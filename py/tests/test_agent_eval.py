import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from agent_chat.service import AgentChatRequest, AgentChatResponse
from agent_eval.schemas import AgentFeedbackRequest
from agent_eval.service import AgentEvalService


class FakeAgentEvalStore:
    def __init__(self):
        self.runs = []
        self.tool_calls = []
        self.feedback = []

    def create_run(self, record):
        self.runs.append(record)

    def create_tool_call(self, record):
        self.tool_calls.append(record)

    def create_feedback(self, payload, user_id):
        self.feedback.append((payload, user_id))
        return "feedback_1"

    def summarize(self):
        return {
            "total_runs": 2,
            "success_rate": 1,
            "tool_success_rate": 0.5,
            "avg_steps": 2,
            "avg_latency_ms": 120,
            "p95_latency_ms": 200,
            "avg_retry_count": 1,
            "total_tokens": 300,
            "token_cost": 0.03,
            "human_takeover_rate": 0.25,
            "hallucination_rate": 0.1,
            "user_satisfaction": 4.5,
            "resolution_rate": 0.75,
        }


class AgentEvalServiceTest(unittest.TestCase):
    def test_traced_chat_records_run_and_tool_call(self):
        store = FakeAgentEvalStore()
        service = AgentEvalService(store)

        def chat_func(_request):
            return AgentChatResponse(
                route="langgraph",
                title="通用工作流",
                answer="ok",
                structured_content={
                    "trace": [
                        {
                            "node": "draft",
                            "input_summary": "in",
                            "output_summary": "out",
                            "decision": "next",
                            "latency_ms": 12,
                        }
                    ]
                },
            )

        response = service.run_traced_chat(AgentChatRequest(message="hello"), chat_func)

        self.assertEqual("langgraph", response.route)
        self.assertEqual(1, len(store.runs))
        self.assertEqual(1, len(store.tool_calls))
        self.assertEqual("success", store.runs[0].status)
        self.assertEqual(1, store.runs[0].steps_count)
        self.assertTrue(response.structured_content["trace_id"].startswith("trace_"))
        self.assertTrue(response.structured_content["run_id"].startswith("run_"))
        self.assertEqual("draft", store.tool_calls[0].tool_name)

    def test_feedback_delegates_to_store(self):
        store = FakeAgentEvalStore()
        service = AgentEvalService(store)
        feedback_id = service.create_feedback(AgentFeedbackRequest(run_id="run_1", rating=5))
        self.assertEqual("feedback_1", feedback_id)
        self.assertEqual(1, len(store.feedback))

    def test_summary_maps_metric_fields(self):
        service = AgentEvalService(FakeAgentEvalStore())
        summary = service.summarize()
        self.assertEqual(2, summary.total_runs)
        self.assertEqual(0.5, summary.tool_success_rate)
        self.assertEqual(0.1, summary.hallucination_rate)


if __name__ == "__main__":
    unittest.main()
