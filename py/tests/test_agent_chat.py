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


def api_response(payload):
    from agent_chat.service import AgentChatResponse

    return AgentChatResponse(**payload)


if __name__ == "__main__":
    unittest.main()
