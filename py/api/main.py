import json
import logging
import os
import sys
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from starlette.responses import Response
from typing import Any, List

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from langgraph.LangGraph import run_workflow
from auth.routes import router as auth_router
from game.routes import router as game_router
from sql_generator.routes import router as sql_generator_router

try:
    from mcp_server.server import router as mcp_java_router
except ImportError:
    mcp_java_router = None


app = FastAPI(title="Tool Hub API", version="1.0.0")

# 基础日志配置（stdout），Docker 会通过 docker logs 捕获
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)
SENSITIVE_KEYS = {"password", "token", "access_token", "authorization", "secret", "jwt"}
MAX_LOG_BODY_LENGTH = 2000


def _sanitize_log_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                sanitized[key] = "***"
            else:
                sanitized[key] = _sanitize_log_value(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_log_value(item) for item in value]
    return value


def _truncate_log_text(value: str) -> str:
    if len(value) <= MAX_LOG_BODY_LENGTH:
        return value
    return value[:MAX_LOG_BODY_LENGTH] + "...<truncated>"


def _format_log_payload(value: Any) -> str:
    try:
        return _truncate_log_text(json.dumps(_sanitize_log_value(value), ensure_ascii=False))
    except Exception:
        return _truncate_log_text(str(value))


def _decode_request_body(body: bytes) -> Any:
    if not body:
        return ""

    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


# 允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8080",
        "http://tool.linger.host",
        "https://tool.linger.host"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    start = time.perf_counter()
    client = request.client.host if request.client else "unknown"
    query_params = dict(request.query_params)
    request_body = await request.body()
    request_payload = _decode_request_body(request_body)

    async def receive():
        return {"type": "http.request", "body": request_body, "more_body": False}

    request = Request(request.scope, receive)

    logger.info(
        "HTTP request client=%s method=%s path=%s query=%s body=%s",
        client,
        request.method,
        request.url.path,
        _format_log_payload(query_params),
        _format_log_payload(request_payload),
    )

    try:
        response = await call_next(request)
    except Exception:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.exception(
            'HTTP request failed client=%s method=%s path=%s latency_ms=%s',
            client,
            request.method,
            request.url.path,
            latency_ms,
        )
        raise

    response_body = b""
    is_streaming = response.headers.get("content-type", "").startswith("text/event-stream")
    if not is_streaming:
        async for chunk in response.body_iterator:
            response_body += chunk
        response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
            background=response.background,
        )

    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "HTTP response client=%s method=%s path=%s status=%s latency_ms=%s body=%s",
        client,
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
        "<streaming-response>" if is_streaming else _format_log_payload(_decode_request_body(response_body)),
    )
    return response

# 注册认证路由
app.include_router(auth_router)

# 注册游戏路由
app.include_router(game_router)

# 注册SQL生成路由
app.include_router(sql_generator_router)

if mcp_java_router is not None:
    app.include_router(mcp_java_router)
else:
    logger.warning("MCP server dependency not available; skipping /mcp/java routes")

class ChatRequest(BaseModel):
    topic: str


class TraceStep(BaseModel):
    node: str
    input_summary: str
    output_summary: str
    decision: str
    latency_ms: int


class ChatResponse(BaseModel):
    topic: str
    draft: str
    corrections: List[str]
    attempts: int
    trace: List[TraceStep]


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        # 运行工作流（内部包含逐步日志输出）
        final_state = run_workflow(req.topic)
        return ChatResponse(
            topic=req.topic,
            draft=final_state.get("draft", ""),
            corrections=final_state.get("corrections", []),
            attempts=final_state.get("attempts", 0),
            trace=final_state.get("trace", []),
        )
    except Exception as e:
        logger.exception("/api/v1/chat 调用失败")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, access_log=False)
