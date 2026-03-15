import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from mcp_server.java_stacktrace import analyze_java_stacktrace


SERVER_INFO = {
    "name": "tool-hub-mcp",
    "version": "1.0.0",
}

PROTOCOL_VERSION = "2024-11-05"


@dataclass
class McpSession:
    session_id: str
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    initialized: bool = False


SESSIONS: Dict[str, McpSession] = {}


def _tool_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "name": "analyze_java_stacktrace_tool",
            "description": "Analyze a Java stack trace, identify the root cause, and suggest fixes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "stacktrace": {
                        "type": "string",
                        "description": "Full Java stack trace text.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional runtime context such as Spring Boot startup or API request handling.",
                        "default": "",
                    },
                },
                "required": ["stacktrace"],
                "additionalProperties": False,
            },
        }
    ]


def _format_sse(event: str, data: str) -> str:
    payload = data.replace("\r\n", "\n").replace("\r", "\n")
    lines = payload.split("\n")
    return "".join([f"event: {event}\n", *[f"data: {line}\n" for line in lines], "\n"])


def _jsonrpc_result(message_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _jsonrpc_error(message_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _session_endpoint(request: Request, session_id: str) -> str:
    return str(request.url_for("mcp_java_messages")) + f"?session_id={session_id}"


async def _enqueue_message(session: McpSession, payload: Dict[str, Any]) -> None:
    await session.queue.put(_format_sse("message", json.dumps(payload, ensure_ascii=False)))


async def _handle_initialize(session: McpSession, message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    requested_version = str(params.get("protocolVersion") or PROTOCOL_VERSION)
    session.initialized = True
    return _jsonrpc_result(
        message_id,
        {
            "protocolVersion": requested_version,
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": SERVER_INFO,
        },
    )


async def _handle_tools_list(message_id: Any) -> Dict[str, Any]:
    return _jsonrpc_result(message_id, {"tools": _tool_definitions()})


async def _handle_tool_call(message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    tool_name = params.get("name")
    arguments = params.get("arguments") or {}
    if tool_name != "analyze_java_stacktrace_tool":
        return _jsonrpc_error(message_id, -32601, f"Unknown tool: {tool_name}")

    stacktrace = str(arguments.get("stacktrace") or "").strip()
    context = str(arguments.get("context") or "").strip()
    if not stacktrace:
        return _jsonrpc_error(message_id, -32602, "stacktrace is required")

    analysis = analyze_java_stacktrace(stacktrace=stacktrace, context=context)
    return _jsonrpc_result(
        message_id,
        {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(analysis, ensure_ascii=False, indent=2),
                }
            ],
            "structuredContent": analysis,
            "isError": False,
        },
    )


async def _process_jsonrpc(session: McpSession, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = payload.get("method")
    message_id = payload.get("id")
    params = payload.get("params") or {}

    if method == "initialize":
        return await _handle_initialize(session, message_id, params)

    if method == "notifications/initialized":
        return None

    if not session.initialized:
        return _jsonrpc_error(message_id, -32002, "Session not initialized")

    if method == "tools/list":
        return await _handle_tools_list(message_id)

    if method == "tools/call":
        return await _handle_tool_call(message_id, params)

    if method == "ping":
        return _jsonrpc_result(message_id, {})

    return _jsonrpc_error(message_id, -32601, f"Unknown method: {method}")


router = APIRouter(tags=["mcp-java"])


@router.get("/mcp/java", include_in_schema=False)
async def mcp_java_root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/mcp/java/sse", status_code=307)


@router.get("/mcp/java/", include_in_schema=False)
async def mcp_java_root_redirect_slash() -> RedirectResponse:
    return RedirectResponse(url="/mcp/java/sse", status_code=307)


@router.get("/mcp/java/sse", name="mcp_java_sse", include_in_schema=False)
async def mcp_java_sse(request: Request) -> StreamingResponse:
    session = McpSession(session_id=str(uuid.uuid4()))
    SESSIONS[session.session_id] = session

    async def event_stream():
        try:
            endpoint_event = _format_sse("endpoint", _session_endpoint(request, session.session_id))
            yield endpoint_event
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(session.queue.get(), timeout=15)
                    yield message
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            SESSIONS.pop(session.session_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/mcp/java/messages", name="mcp_java_messages", include_in_schema=False)
async def mcp_java_messages(
    request: Request,
    session_id: str = Query(..., description="MCP SSE session id"),
) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Unknown or expired MCP session")

    payload = await request.json()
    response = await _process_jsonrpc(session, payload)
    if response is not None:
        await _enqueue_message(session, response)
    return {"ok": True}
