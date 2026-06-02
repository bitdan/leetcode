import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from api.main import app
from project_agent.schemas import ProjectAgentRequest
from project_agent.service import ProjectAgentService


class ProjectAgentServiceTest(unittest.TestCase):
    def test_search_project_returns_trace_and_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("def create_app():\n    return 'ok'\n", encoding="utf-8")

            service = ProjectAgentService(root)
            response = service.chat(ProjectAgentRequest(message="create_app 在哪里", max_results=5, use_rag=False))

        self.assertIn("src/main.py:1", response.citations)
        self.assertEqual("search_project", response.tool_calls[0].tool_name)
        self.assertEqual("success", response.tool_calls[0].status)
        self.assertIn("create_app", response.answer)

    def test_read_project_file_stays_inside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")

            service = ProjectAgentService(root)
            response = service.chat(ProjectAgentRequest(message="读取 README.md"))

        self.assertEqual(["README.md"], response.citations)
        self.assertIn("# Demo", response.answer)

    def test_rag_index_retrieves_document_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "agent.md").write_text("Project agent supports streaming output and eval cases.\n",
                                                     encoding="utf-8")

            service = ProjectAgentService(root)
            index = service.build_index(force=True)
            response = service.chat(ProjectAgentRequest(message="streaming eval cases", max_results=5))

        self.assertEqual(1, index.indexed_files)
        self.assertIn("docs/agent.md:1", response.citations)
        self.assertIn("rag_retrieve", [call.tool_name for call in response.tool_calls])

    def test_session_memory_reuses_previous_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "memory.py").write_text("def remember_session():\n    return True\n", encoding="utf-8")

            service = ProjectAgentService(root)
            first = service.chat(ProjectAgentRequest(message="remember_session 在哪里", session_id="s1"))
            second = service.chat(ProjectAgentRequest(message="继续看刚才的问题", session_id="s1"))

        self.assertEqual("s1", first.session_id)
        self.assertIn("src/memory.py:1", second.citations)
        self.assertGreater(second.structured_content["memory_turns"], 0)

    def test_command_requires_confirmation_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = ProjectAgentService(Path(tmp))
            response = service.chat(ProjectAgentRequest(message="运行 python -m py_compile missing.py"))
            confirmation = response.structured_content["confirmation"]

            rejected = service.confirm(confirmation["id"], approved=False)

        self.assertTrue(response.structured_content["requires_confirmation"])
        self.assertEqual("rejected", rejected.status)

    def test_eval_cases_score_answer_and_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("def create_app():\n    return 'ok'\n", encoding="utf-8")
            service = ProjectAgentService(root)

            from project_agent.schemas import ProjectAgentEvalCase, ProjectAgentEvalRequest

            result = service.run_eval_cases(
                ProjectAgentEvalRequest(
                    cases=[
                        ProjectAgentEvalCase(
                            name="find create_app",
                            message="create_app 在哪里",
                            must_include=["src/main.py"],
                            tool_must_include=["search_project"],
                        )
                    ]
                )
            )

        self.assertEqual(1, result.total)
        self.assertEqual(1, result.passed)


class ProjectAgentApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_project_agent_chat_endpoint(self):
        response = self.client.post("/api/v1/project-agent/chat", json={"message": "项目结构概览"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("answer", payload)
        self.assertEqual("project_overview", payload["tool_calls"][0]["tool_name"])

    def test_project_agent_stream_endpoint(self):
        response = self.client.post("/api/v1/project-agent/chat/stream", json={"message": "项目结构概览"})

        self.assertEqual(200, response.status_code)
        self.assertIn("event: step", response.text)
        self.assertIn("event: final", response.text)


if __name__ == "__main__":
    unittest.main()
