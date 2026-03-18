import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from mcp_server.java_stacktrace import analyze_java_stacktrace
from mcp_server.leetcode_coach import run_leetcode_coach
from mcp_server.registry import create_default_tool_registry, list_tool_definitions
from mcp_server.sql_exporter import run_sql_export
from mcp_server.sql_generator import generate_nl_sql

SERVER_INFO = {"name": "tool-hub-mcp", "version": "1.0.0"}
PROTOCOL_VERSION = "2024-11-05"


@dataclass
class McpSession:
    session_id: str
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    initialized: bool = False


def _format_sse(event: str, data: str) -> str:
    payload = data.replace("\r\n", "\n").replace("\r", "\n")
    return "".join([f"event: {event}\n", *[f"data: {line}\n" for line in payload.split("\n")], "\n"])


def _jsonrpc_result(message_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _jsonrpc_error(message_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


async def _enqueue_message(session: McpSession, payload: Dict[str, Any]) -> None:
    await session.queue.put(_format_sse("message", json.dumps(payload, ensure_ascii=False)))


async def _process_jsonrpc(session: McpSession, payload: Dict[str, Any],
                           registry: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    registry = registry or create_default_tool_registry()
    method = payload.get("method")
    message_id = payload.get("id")
    params = payload.get("params") or {}

    if method == "initialize":
        session.initialized = True
        requested_version = str(params.get("protocolVersion") or PROTOCOL_VERSION)
        return _jsonrpc_result(message_id,
                               {"protocolVersion": requested_version, "capabilities": {"tools": {"listChanged": False}},
                                "serverInfo": SERVER_INFO})

    if method == "notifications/initialized":
        return None

    if not session.initialized:
        return _jsonrpc_error(message_id, -32002, "Session not initialized")

    if method == "tools/list":
        return _jsonrpc_result(message_id, {"tools": list_tool_definitions(registry)})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            if tool_name == "analyze_java_stacktrace_tool":
                stacktrace = str(arguments.get("stacktrace") or "").strip()
                if not stacktrace:
                    return _jsonrpc_error(message_id, -32602, "stacktrace is required")
                result = analyze_java_stacktrace(stacktrace=stacktrace,
                                                 context=str(arguments.get("context") or "").strip())
            elif tool_name == "leetcode_coach_tool":
                title = str(arguments.get("title") or "").strip()
                problem_statement = str(arguments.get("problem_statement") or "").strip()
                code = str(arguments.get("code") or "")
                if not title:
                    return _jsonrpc_error(message_id, -32602, "title is required")
                if not problem_statement:
                    return _jsonrpc_error(message_id, -32602, "problem_statement is required")
                if not code.strip():
                    return _jsonrpc_error(message_id, -32602, "code is required")
                result = run_leetcode_coach(
                    title=title,
                    problem_statement=problem_statement,
                    code=code,
                    constraints=[str(item) for item in arguments.get("constraints") or []],
                    examples=[str(item) for item in arguments.get("examples") or []],
                    language=str(arguments.get("language") or "java").strip() or "java",
                    user_question=str(arguments.get("user_question") or "").strip(),
                    mode=str(arguments.get("mode") or "hint").strip() or "hint",
                )
            elif tool_name == "sql_exporter_tool":
                result = run_sql_export(
                    db_kind=str(arguments.get("db_kind") or "").strip(),
                    db_path=str(arguments.get("db_path") or "").strip(),
                    dsn=str(arguments.get("dsn") or "").strip(),
                    sql=str(arguments.get("sql") or ""),
                    sql_file=str(arguments.get("sql_file") or "").strip(),
                    params=arguments.get("params") if isinstance(arguments.get("params"), dict) else {},
                    export=str(arguments.get("export") or "").strip(),
                    output=str(arguments.get("output") or "").strip(),
                    max_rows=int(arguments.get("max_rows") or 5000),
                )
            elif tool_name == "nl_to_sql_generator_tool":
                question = str(arguments.get("question") or "").strip()
                if not question:
                    return _jsonrpc_error(message_id, -32602, "question is required")
                result = generate_nl_sql(question=question, account=str(arguments.get("account") or "").strip())
            else:
                return _jsonrpc_error(message_id, -32601, f"Unknown tool: {tool_name}")
        except ValueError as exc:
            return _jsonrpc_error(message_id, -32602, str(exc))
        except Exception as exc:
            return _jsonrpc_error(message_id, -32001, str(exc))
        return _jsonrpc_result(message_id,
                               {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
                                "structuredContent": result, "isError": False})

    if method == "ping":
        return _jsonrpc_result(message_id, {})

    return _jsonrpc_error(message_id, -32601, f"Unknown method: {method}")


def create_router(container) -> APIRouter:
    router = APIRouter(tags=["mcp-java"])
    sessions: Dict[str, McpSession] = {}
    registry = container.mcp_tool_registry

    def session_endpoint(request: Request, session_id: str) -> str:
        return str(request.url_for("mcp_java_messages")) + f"?session_id={session_id}"

    @router.get("/mcp/java", include_in_schema=False)
    async def mcp_java_root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/mcp/java/sse", status_code=307)

    @router.get("/mcp/java/", include_in_schema=False)
    async def mcp_java_root_redirect_slash() -> RedirectResponse:
        return RedirectResponse(url="/mcp/java/sse", status_code=307)

    @router.get("/mcp/java/sse", name="mcp_java_sse", include_in_schema=False)
    async def mcp_java_sse(request: Request) -> StreamingResponse:
        session = McpSession(session_id=str(uuid.uuid4()))
        sessions[session.session_id] = session

        async def event_stream():
            try:
                yield _format_sse("endpoint", session_endpoint(request, session.session_id))
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        yield await asyncio.wait_for(session.queue.get(), timeout=15)
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
                sessions.pop(session.session_id, None)

        return StreamingResponse(event_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                                          "X-Accel-Buffering": "no"})

    @router.post("/mcp/java/messages", name="mcp_java_messages", include_in_schema=False)
    async def mcp_java_messages(request: Request, session_id: str = Query(..., description="MCP SSE session id")) -> \
    Dict[str, Any]:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Unknown or expired MCP session")
        payload = await request.json()
        response = await _process_jsonrpc(session, payload, registry)
        if response is not None:
            await _enqueue_message(session, response)
        return {"ok": True}

    return router


__all__ = [
    "McpSession",
    "_format_sse",
    "_jsonrpc_error",
    "_jsonrpc_result",
    "_process_jsonrpc",
    "create_router",
    "analyze_java_stacktrace",
    "run_leetcode_coach",
    "run_sql_export",
    "generate_nl_sql",
]
