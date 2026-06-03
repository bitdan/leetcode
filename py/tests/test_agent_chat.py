import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from agent_chat.service import AgentChatRequest, AgentChatService
from api.main import app


class AgentChatServiceTest(unittest.TestCase):
    def test_routes_to_leetcode(self):
        service = AgentChatService()
        with patch.object(service, "_handle_leetcode",
                          return_value={"understanding": "x", "key_observations": [], "hint": "h",
                                        "complexity_analysis": "c", "review_findings": [], "next_step": "n",
                                        "similar_patterns": []}):
            result = service.chat(
                AgentChatRequest(
                    message="Two Sum\nGiven an array of integers nums...\n帮我分析时间复杂度\n```java\nclass Solution {}\n```"
                )
            )
        self.assertEqual("leetcode_coach", result.route)

    def test_routes_to_stacktrace(self):
        service = AgentChatService()
        with patch.object(service, "_handle_stacktrace",
                          return_value={"root_cause": "NullPointerException", "evidence": [], "likely_fixes": [],
                                        "missing_context": []}):
            result = service.chat(
                AgentChatRequest(
                    message="java.lang.NullPointerException\nCaused by: java.lang.NullPointerException\n    at com.demo.UserService.load(UserService.java:12)"
                )
            )
        self.assertEqual("java_stacktrace", result.route)

    def test_routes_to_langgraph_by_default(self):
        service = AgentChatService()
        with patch.object(service, "_handle_langgraph",
                          return_value={"draft": "general answer", "corrections": [], "trace": []}):
            result = service.chat(AgentChatRequest(message="帮我写一段关于数据太多怎么办的总结"))
        self.assertEqual("langgraph", result.route)

    def test_default_langgraph_workflow_runs_without_patch(self):
        service = AgentChatService()
        result = service.chat(AgentChatRequest(message="帮我写一段关于数据太多怎么办的总结"))

        self.assertEqual("langgraph", result.route)
        self.assertIn("trace", result.structured_content)
        self.assertNotIn("执行轨迹", result.answer)

    def test_agent_architecture_question_gets_actionable_answer(self):
        service = AgentChatService()
        result = service.chat(AgentChatRequest(message="如何实现agent"))

        self.assertEqual("agent_architecture", result.route)
        self.assertEqual("Agent 架构顾问", result.title)
        self.assertIn("Planner", result.answer)
        self.assertIn("Tool Registry", result.answer)
        self.assertIn("Evaluator", result.answer)
        self.assertNotIn("结果\n", result.answer)
        self.assertEqual("agent_architecture", result.structured_content["trace"][0]["output_summary"])
        self.assertTrue(result.run_id.startswith("run_"))
        self.assertTrue(result.trace_id.startswith("trace_"))
        self.assertEqual("route_decided", result.steps[0].node)
        self.assertEqual("agent_architecture_planner", result.tool_calls[0].tool_name)

    def test_weather_question_uses_general_answer_not_missing_context(self):
        service = AgentChatService()
        result = service.chat(AgentChatRequest(message="广州天气如何"))

        self.assertEqual("langgraph", result.route)
        self.assertEqual("success", result.status)
        self.assertNotIn("我还不能稳定判断", result.answer)
        self.assertIn("实时天气工具", result.answer)

    def test_general_question_does_not_require_task_type(self):
        service = AgentChatService()
        result = service.chat(AgentChatRequest(message="广州在哪里"))

        self.assertEqual("langgraph", result.route)
        self.assertEqual("success", result.status)
        self.assertNotIn("我还不能稳定判断", result.answer)

    def test_general_question_can_use_model_answer(self):
        service = AgentChatService(openai_api_key="test-key")
        with patch.object(service, "_call_model_for_general_answer", return_value="广州在中国广东省，是广东省省会。"):
            result = service.chat(AgentChatRequest(message="广州在哪里"))

        self.assertEqual("langgraph", result.route)
        self.assertIn("广东省", result.answer)
        self.assertTrue(result.structured_content["model_used"])


class AgentChatApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_chat_endpoint(self):
        with patch("api.main.agent_chat_service.chat") as mock_chat:
            mock_chat.return_value = api_response(
                {
                    "route": "leetcode_coach",
                    "title": "LeetCode 陪练",
                    "answer": "题意理解\n示例",
                    "structured_content": {"mode": "hint"},
                }
            )
            response = self.client.post("/api/v1/agent/chat",
                                        json={"message": "Two Sum\n```java\nclass Solution {}\n```"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("leetcode_coach", response.json()["route"])

    def test_chat_stream_endpoint_emits_final_response(self):
        with self.client.stream("POST", "/api/v1/agent/chat/stream", json={"message": "如何实现agent"}) as response:
            body = response.read().decode("utf-8")
        self.assertEqual(200, response.status_code)
        self.assertIn("event: route_decided", body)
        self.assertIn("event: answer_delta", body)
        self.assertIn("event: final", body)


def api_response(payload):
    from agent_chat.service import AgentChatResponse

    return AgentChatResponse(**payload)


if __name__ == "__main__":
    unittest.main()
