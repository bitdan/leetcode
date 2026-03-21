# MCP Server Notes

This directory is the MCP adapter layer for local skills. Keep it thin.

## Role Split

- `skills/*/scripts/*.py`
  Own the real capability and expose a stable programmatic entrypoint for each skill.

- `py/mcp_server/*.py`
  Adapt those skill entrypoints to MCP tools and JSON-RPC/SSE transport.

- `py/mcp_server/server.py`
  Own the MCP protocol handling:
  - create SSE sessions
  - receive JSON-RPC requests
  - route `tools/list` and `tools/call`
  - push responses back through SSE

## Current Tool Mapping

- `java_stacktrace.py`
  Loads `skills/java-stacktrace-analyzer/scripts/analyze_stacktrace.py`

- `sql_exporter.py`
  Loads `skills/sql-exporter/scripts/export_sql.py`

- `sql_generator.py`
  Loads `skills/nl-to-sql-generator/scripts/generate_sql.py`

- `leetcode_coach.py`
  Loads `skills/leetcode-coach/scripts/run_coach.py`

## Call Flow

The request path is:

1. Frontend or MCP client opens `GET /mcp/java/sse`
2. Server creates a session and sends back a `/messages?session_id=...` endpoint
3. Client sends JSON-RPC messages to `POST /mcp/java/messages`
4. `server.py` routes the tool call
5. The adapter module calls the matching skill script
6. The skill script calls its local core implementation
7. Result is wrapped as MCP `content` + `structuredContent`
8. Response is pushed back over SSE

## Maintenance Rule

When adding a new MCP tool:

1. Add or confirm a stable entrypoint under `skills/<skill-name>/scripts/`
2. Add a small adapter in `py/mcp_server/`
3. Register the tool schema and dispatch branch in `server.py`
4. Add or update a unit test in `py/tests/test_mcp_server.py`
