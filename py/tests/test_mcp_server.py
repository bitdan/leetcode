import asyncio
import sys
from pathlib import Path
import unittest


project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from mcp_server.server import McpSession, _format_sse, _process_jsonrpc


class McpServerTest(unittest.TestCase):
    def test_initialize_tools_list_and_call(self):
        async def scenario():
            session = McpSession(session_id="test-session")

            init_payload = await _process_jsonrpc(
                session,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                },
            )
            self.assertEqual("tool-hub-mcp", init_payload["result"]["serverInfo"]["name"])

            tools_payload = await _process_jsonrpc(
                session,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                },
            )
            self.assertEqual("analyze_java_stacktrace_tool", tools_payload["result"]["tools"][0]["name"])

            call_payload = await _process_jsonrpc(
                session,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "analyze_java_stacktrace_tool",
                        "arguments": {
                            "stacktrace": "java.lang.NullPointerException: x\n    at com.example.demo.UserController.getUser(UserController.java:32)",
                            "context": "Spring MVC request",
                        },
                    },
                },
            )
            self.assertFalse(call_payload["result"]["isError"])
            self.assertIn("root_cause", call_payload["result"]["structuredContent"])

        asyncio.run(scenario())

    def test_sse_format(self):
        payload = _format_sse("message", "{\"jsonrpc\":\"2.0\"}")
        self.assertIn("event: message", payload)
        self.assertIn("data: {\"jsonrpc\":\"2.0\"}", payload)


if __name__ == "__main__":
    unittest.main()
