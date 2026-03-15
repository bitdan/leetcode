import asyncio
import sqlite3
import shutil
import sys
from pathlib import Path
import unittest
from unittest.mock import patch


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

    def test_sql_exporter_tool(self):
        async def scenario():
            tmp_dir = project_root / "tests" / "tmp_mcp_sql_exporter"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            try:
                db_path = tmp_dir / "demo.sqlite"
                output_path = tmp_dir / "result.json"
                conn = sqlite3.connect(str(db_path))
                try:
                    conn.execute("create table users(id integer primary key, name text)")
                    conn.execute("insert into users(id, name) values(1, 'Alice')")
                    conn.commit()
                finally:
                    conn.close()

                session = McpSession(session_id="sql-session", initialized=True)
                payload = await _process_jsonrpc(
                    session,
                    {
                        "jsonrpc": "2.0",
                        "id": 9,
                        "method": "tools/call",
                        "params": {
                            "name": "sql_exporter_tool",
                            "arguments": {
                                "db_kind": "sqlite",
                                "db_path": str(db_path),
                                "sql": "SELECT id, name FROM users ORDER BY id",
                                "export": "json",
                                "output": str(output_path),
                            },
                        },
                    },
                )
                self.assertFalse(payload["result"]["isError"])
                structured = payload["result"]["structuredContent"]
                self.assertEqual(1, structured["rows"])
                self.assertEqual("json", structured["export"])
                self.assertTrue(output_path.exists())
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        asyncio.run(scenario())

    def test_nl_to_sql_generator_tool(self):
        async def scenario():
            session = McpSession(session_id="sql-gen-session", initialized=True)
            with patch("mcp_server.server.generate_nl_sql") as mock_generate:
                mock_generate.return_value = {
                    "sql": "SELECT seller_sku, SUM(quantity_ordered) AS qty_ordered FROM sale_amazon_order_item GROUP BY seller_sku LIMIT 10",
                    "preview_sql": "SELECT seller_sku, SUM(quantity_ordered) AS qty_ordered FROM sale_amazon_order_item GROUP BY seller_sku LIMIT 10",
                    "params": [],
                    "result_columns": ["seller_sku", "qty_ordered"],
                    "explanation": "统计近30天SKU维度的下单量",
                    "tables": ["sale_amazon_order_item"],
                }
                payload = await _process_jsonrpc(
                    session,
                    {
                        "jsonrpc": "2.0",
                        "id": 12,
                        "method": "tools/call",
                        "params": {
                            "name": "nl_to_sql_generator_tool",
                            "arguments": {
                                "question": "近30天销量最高的10个SKU",
                                "account": "QD-US",
                            },
                        },
                    },
                )
            self.assertFalse(payload["result"]["isError"])
            structured = payload["result"]["structuredContent"]
            self.assertIn("SELECT seller_sku", structured["sql"])
            self.assertEqual(["seller_sku", "qty_ordered"], structured["result_columns"])

        asyncio.run(scenario())

    def test_sse_format(self):
        payload = _format_sse("message", "{\"jsonrpc\":\"2.0\"}")
        self.assertIn("event: message", payload)
        self.assertIn("data: {\"jsonrpc\":\"2.0\"}", payload)


if __name__ == "__main__":
    unittest.main()
