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
            response = service.chat(ProjectAgentRequest(message="create_app 在哪里", max_results=5))

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


class ProjectAgentApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_project_agent_chat_endpoint(self):
        response = self.client.post("/api/v1/project-agent/chat", json={"message": "项目结构概览"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("answer", payload)
        self.assertEqual("project_overview", payload["tool_calls"][0]["tool_name"])


if __name__ == "__main__":
    unittest.main()
