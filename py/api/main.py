import sys
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from typing import List

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from langgraph.LangGraph import run_workflow
from auth.routes import router as auth_router


app = FastAPI(title="Tool Hub API", version="1.0.0")

# 基础日志配置（stdout），Docker 会通过 docker logs 捕获
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册认证路由
app.include_router(auth_router)

class ChatRequest(BaseModel):
    topic: str


class ChatResponse(BaseModel):
    topic: str
    draft: str
    corrections: List[str]
    attempts: int


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
        )
    except Exception as e:
        logger.exception("/api/v1/chat 调用失败")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
