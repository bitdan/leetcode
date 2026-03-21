from typing import Any, Callable, Dict, List

from mcp_server.java_stacktrace import analyze_java_stacktrace
from mcp_server.leetcode_coach import run_leetcode_coach
from mcp_server.sql_exporter import run_sql_export
from mcp_server.sql_generator import generate_nl_sql


def create_default_tool_registry() -> Dict[str, Dict[str, Any]]:
    return {
        "analyze_java_stacktrace_tool": {
            "description": "Analyze a Java stack trace, identify the root cause, and suggest fixes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "stacktrace": {"type": "string", "description": "Full Java stack trace text."},
                    "context": {"type": "string", "description": "Optional runtime context.", "default": ""},
                },
                "required": ["stacktrace"],
                "additionalProperties": False,
            },
            "handler": _handle_java_stacktrace,
        },
        "leetcode_coach_tool": {
            "description": "Coach a user through a LeetCode problem using the problem statement and submitted code.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "problem_statement": {"type": "string"},
                    "constraints": {"type": "array", "items": {"type": "string"}, "default": []},
                    "examples": {"type": "array", "items": {"type": "string"}, "default": []},
                    "code": {"type": "string"},
                    "language": {"type": "string", "default": "java"},
                    "user_question": {"type": "string", "default": ""},
                    "mode": {"type": "string", "enum": ["hint", "review", "teach", "mock"], "default": "hint"},
                },
                "required": ["title", "problem_statement", "code"],
                "additionalProperties": False,
            },
            "handler": _handle_leetcode_coach,
        },
        "sql_exporter_tool": {
            "description": "Validate, execute, and export a read-only SQL query using the sql-exporter skill workflow.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "db_kind": {"type": "string", "enum": ["sqlite", "sqlalchemy"]},
                    "db_path": {"type": "string", "default": ""},
                    "dsn": {"type": "string", "default": ""},
                    "sql": {"type": "string", "default": ""},
                    "sql_file": {"type": "string", "default": ""},
                    "params": {"type": "object", "default": {}},
                    "export": {"type": "string", "enum": ["csv", "json", "xlsx"]},
                    "output": {"type": "string"},
                    "max_rows": {"type": "integer", "default": 5000},
                },
                "required": ["db_kind", "export", "output"],
                "additionalProperties": False,
            },
            "handler": _handle_sql_exporter,
        },
        "nl_to_sql_generator_tool": {
            "description": "Generate read-only SQL from a natural-language analytics question.",
            "inputSchema": {
                "type": "object",
                "properties": {"question": {"type": "string"}, "account": {"type": "string", "default": ""}},
                "required": ["question"],
                "additionalProperties": False,
            },
            "handler": _handle_nl_to_sql,
        },
    }


def list_tool_definitions(registry: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"name": name, "description": definition["description"], "inputSchema": definition["inputSchema"]} for
            name, definition in registry.items()]


def call_tool(registry: Dict[str, Dict[str, Any]], tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    definition = registry.get(tool_name)
    if definition is None:
        raise KeyError(tool_name)
    handler: Callable[[Dict[str, Any]], Dict[str, Any]] = definition["handler"]
    return handler(arguments)


def _handle_java_stacktrace(arguments: Dict[str, Any]) -> Dict[str, Any]:
    stacktrace = str(arguments.get("stacktrace") or "").strip()
    if not stacktrace:
        raise ValueError("stacktrace is required")
    return analyze_java_stacktrace(stacktrace=stacktrace, context=str(arguments.get("context") or "").strip())


def _handle_leetcode_coach(arguments: Dict[str, Any]) -> Dict[str, Any]:
    title = str(arguments.get("title") or "").strip()
    problem_statement = str(arguments.get("problem_statement") or "").strip()
    code = str(arguments.get("code") or "")
    if not title:
        raise ValueError("title is required")
    if not problem_statement:
        raise ValueError("problem_statement is required")
    if not code.strip():
        raise ValueError("code is required")
    return run_leetcode_coach(
        title=title,
        problem_statement=problem_statement,
        code=code,
        constraints=[str(item) for item in arguments.get("constraints") or []],
        examples=[str(item) for item in arguments.get("examples") or []],
        language=str(arguments.get("language") or "java").strip() or "java",
        user_question=str(arguments.get("user_question") or "").strip(),
        mode=str(arguments.get("mode") or "hint").strip() or "hint",
    )


def _handle_sql_exporter(arguments: Dict[str, Any]) -> Dict[str, Any]:
    return run_sql_export(
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


def _handle_nl_to_sql(arguments: Dict[str, Any]) -> Dict[str, Any]:
    question = str(arguments.get("question") or "").strip()
    if not question:
        raise ValueError("question is required")
    return generate_nl_sql(question=question, account=str(arguments.get("account") or "").strip())
