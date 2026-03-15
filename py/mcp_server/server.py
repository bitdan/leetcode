import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from mcp_server.java_stacktrace import analyze_java_stacktrace
from mcp_server.sql_exporter import run_sql_export
from mcp_server.sql_generator import generate_nl_sql


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
        },
        {
            "name": "sql_exporter_tool",
            "description": "Validate, execute, and export a read-only SQL query using the sql-exporter skill workflow.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "db_kind": {
                        "type": "string",
                        "enum": ["sqlite", "sqlalchemy"],
                        "description": "Database connection mode. Use sqlalchemy for MySQL/PostgreSQL and sqlite for local files.",
                    },
                    "db_path": {
                        "type": "string",
                        "description": "SQLite database path when db_kind=sqlite.",
                        "default": "",
                    },
                    "dsn": {
                        "type": "string",
                        "description": "SQLAlchemy DSN when db_kind=sqlalchemy.",
                        "default": "",
                    },
                    "sql": {
                        "type": "string",
                        "description": "Inline read-only SQL text. Provide sql or sql_file.",
                        "default": "",
                    },
                    "sql_file": {
                        "type": "string",
                        "description": "Path to a .sql file. Provide sql or sql_file.",
                        "default": "",
                    },
                    "params": {
                        "type": "object",
                        "description": "Named query parameters as a JSON object.",
                        "default": {},
                    },
                    "export": {
                        "type": "string",
                        "enum": ["csv", "json", "xlsx"],
                        "description": "Export file format.",
                    },
                    "output": {
                        "type": "string",
                        "description": "Output file path for the exported result.",
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Maximum rows to fetch and export.",
                        "default": 5000,
                    },
                },
                "required": ["db_kind", "export", "output"],
                "additionalProperties": False,
            },
        },
        {
            "name": "nl_to_sql_generator_tool",
            "description": "Generate read-only SQL from a natural-language analytics question using the repository's Amazon order SQL generator workflow.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural-language question such as 近30天销量最高的10个SKU.",
                    },
                    "account": {
                        "type": "string",
                        "description": "Optional account-site token such as QD-US.",
                        "default": "",
                    },
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
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
    try:
        if tool_name == "analyze_java_stacktrace_tool":
            stacktrace = str(arguments.get("stacktrace") or "").strip()
            context = str(arguments.get("context") or "").strip()
            if not stacktrace:
                return _jsonrpc_error(message_id, -32602, "stacktrace is required")
            result = analyze_java_stacktrace(stacktrace=stacktrace, context=context)
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
            account = str(arguments.get("account") or "").strip()
            if not question:
                return _jsonrpc_error(message_id, -32602, "question is required")
            result = generate_nl_sql(question=question, account=account)
        else:
            return _jsonrpc_error(message_id, -32601, f"Unknown tool: {tool_name}")
    except Exception as exc:
        return _jsonrpc_error(message_id, -32001, str(exc))

    return _jsonrpc_result(
        message_id,
        {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2),
                }
            ],
            "structuredContent": result,
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
