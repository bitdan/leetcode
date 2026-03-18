import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from mcp_server.java_stacktrace import analyze_java_stacktrace
from mcp_server.leetcode_coach import run_leetcode_coach
from mcp_server.sql_exporter import run_sql_export
from mcp_server.sql_generator import generate_nl_sql

SERVER_INFO = {
    "name": "tool-hub-mcp",
    "version": "1.0.0",
}

PROTOCOL_VERSION = "2024-11-05"


@dataclass
class McpSession:
    # 每个 SSE 连接都会对应一个会话；客户端后续通过 session_id 往 /messages 发 JSON-RPC 请求。
    session_id: str
    # queue 用来把服务端响应异步推回到 SSE 长连接。
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    initialized: bool = False


SESSIONS: Dict[str, McpSession] = {}


def _tool_definitions() -> List[Dict[str, Any]]:
    # 这里定义“这个 MCP server 暴露哪些工具，以及每个工具的输入 schema”。
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
            "name": "leetcode_coach_tool",
            "description": "Coach a user through a LeetCode problem using the problem statement and submitted code, returning hints, complexity analysis, review findings, and next-step advice.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "LeetCode problem title.",
                    },
                    "problem_statement": {
                        "type": "string",
                        "description": "Full problem statement or the essential problem description.",
                    },
                    "constraints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of constraints.",
                        "default": [],
                    },
                    "examples": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of examples.",
                        "default": [],
                    },
                    "code": {
                        "type": "string",
                        "description": "User submitted code to review.",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language of the submitted code.",
                        "default": "java",
                    },
                    "user_question": {
                        "type": "string",
                        "description": "Optional user question or difficulty point.",
                        "default": "",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["hint", "review", "teach", "mock"],
                        "description": "Coaching mode.",
                        "default": "hint",
                    },
                },
                "required": ["title", "problem_statement", "code"],
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
    # SSE 协议是纯文本格式：event: xxx / data: xxx
    # 多行 data 需要逐行写入 data: 前缀。
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
    # 所有 JSON-RPC 响应最终都会进入 session.queue，再由 SSE 长连接发回前端。
    await session.queue.put(_format_sse("message", json.dumps(payload, ensure_ascii=False)))


async def _handle_initialize(session: McpSession, message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    # MCP 客户端建立连接后，第一步通常就是 initialize 握手。
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
        # 这里就是 MCP server 的“路由层”：根据 tool_name 分发到对应实现。
        if tool_name == "analyze_java_stacktrace_tool":
            stacktrace = str(arguments.get("stacktrace") or "").strip()
            context = str(arguments.get("context") or "").strip()
            if not stacktrace:
                return _jsonrpc_error(message_id, -32602, "stacktrace is required")
            result = analyze_java_stacktrace(stacktrace=stacktrace, context=context)
        elif tool_name == "leetcode_coach_tool":
            title = str(arguments.get("title") or "").strip()
            problem_statement = str(arguments.get("problem_statement") or "").strip()
            code = str(arguments.get("code") or "")
            constraints = arguments.get("constraints") if isinstance(arguments.get("constraints"), list) else []
            examples = arguments.get("examples") if isinstance(arguments.get("examples"), list) else []
            language = str(arguments.get("language") or "java").strip() or "java"
            user_question = str(arguments.get("user_question") or "").strip()
            mode = str(arguments.get("mode") or "hint").strip() or "hint"
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
                constraints=[str(item) for item in constraints],
                examples=[str(item) for item in examples],
                language=language,
                user_question=user_question,
                mode=mode,
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
            account = str(arguments.get("account") or "").strip()
            if not question:
                return _jsonrpc_error(message_id, -32602, "question is required")
            result = generate_nl_sql(question=question, account=account)
        else:
            return _jsonrpc_error(message_id, -32601, f"Unknown tool: {tool_name}")
    except Exception as exc:
        # 工具内部异常统一包装成 JSON-RPC error，避免前端只能看到 500。
        return _jsonrpc_error(message_id, -32001, str(exc))

    return _jsonrpc_result(
        message_id,
        {
            "content": [
                {
                    # content 是 MCP 常见的文本输出形式，方便通用客户端直接显示。
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2),
                }
            ],
            # structuredContent 给程序化调用方使用，前端页面也优先显示这一块。
            "structuredContent": result,
            "isError": False,
        },
    )


async def _process_jsonrpc(session: McpSession, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # 这个函数专门负责“解释客户端发来的 JSON-RPC 请求”。
    # 它本身不关心 HTTP/SSE，只关心 method / params / id。
    method = payload.get("method")
    message_id = payload.get("id")
    params = payload.get("params") or {}

    if method == "initialize":
        return await _handle_initialize(session, message_id, params)

    if method == "notifications/initialized":
        return None

    # 除了 initialize 以外，其他请求都要求会话已经初始化。
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
    # 新建一个会话，并把它挂到内存字典里。
    session = McpSession(session_id=str(uuid.uuid4()))
    SESSIONS[session.session_id] = session

    async def event_stream():
        try:
            # 连接建立后先告诉客户端：后续 JSON-RPC 要往哪个 /messages 端点发。
            endpoint_event = _format_sse("endpoint", _session_endpoint(request, session.session_id))
            yield endpoint_event
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(session.queue.get(), timeout=15)
                    yield message
                except asyncio.TimeoutError:
                    # keep-alive 避免某些代理或浏览器把空闲 SSE 连接断掉。
                    yield ": keep-alive\n\n"
        finally:
            # SSE 断开时清理会话，避免内存泄漏。
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
    # 客户端通过 session_id 告诉服务端：这条 JSON-RPC 消息属于哪个 SSE 会话。
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Unknown or expired MCP session")

    payload = await request.json()
    response = await _process_jsonrpc(session, payload)
    if response is not None:
        await _enqueue_message(session, response)
    return {"ok": True}
