import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from rag_lab.routes import create_router
from rag_lab.schemas import RagDocumentInput
from rag_lab.service import RagLabService


class RagLabServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = RagLabService()
        self.service.index("demo", [
            RagDocumentInput(
                id="hybrid",
                title="混合检索",
                content="# 召回\n混合检索同时使用 BM25 关键词召回和向量语义召回。\n\n# 重排\nReranker 对候选证据进行重新排序。",
                source="hybrid.md",
            ),
            RagDocumentInput(
                id="graph",
                title="证据图",
                content="# 图扩散\n证据图连接相邻文本块和共享概念块，让相关上下文获得额外分数。\n\n# 引用\n回答必须附带可追踪引用。",
                source="graph.md",
            ),
        ])

    def test_indexes_chunks_and_graph_edges(self):
        stats = self.service.stats("demo")
        self.assertEqual(2, stats.document_count)
        self.assertGreaterEqual(stats.chunk_count, 2)
        self.assertGreater(stats.graph_edge_count, 0)

    def test_query_returns_explainable_scores_and_citations(self):
        result = self.service.query("demo", "为什么 RAG 要做混合检索和重排？", top_k=3)
        self.assertGreater(len(result.evidence), 0)
        self.assertIn("BM25", result.diagnostics.retrieval_strategy)
        self.assertIn("[1]", result.answer)
        self.assertGreater(result.evidence[0].final_score, 0)
        self.assertTrue(result.evidence[0].matched_terms)

    def test_missing_collection_is_actionable(self):
        with self.assertRaisesRegex(ValueError, "先索引文档"):
            self.service.query("missing", "什么是 RAG")

    def test_api_indexes_and_queries_collection(self):
        container = type("Container", (), {"rag_lab_service": RagLabService()})()
        app = FastAPI()
        app.include_router(create_router(container))
        client = TestClient(app)

        index_response = client.post("/api/v1/rag/index", json={
            "collection_id": "api-demo",
            "documents": [{
                "title": "可靠 RAG",
                "content": "# 引用\n可靠回答应附带引用证据，并在证据不足时说明知识缺口。",
                "source": "reliable.md",
            }],
        })
        self.assertEqual(200, index_response.status_code)
        self.assertGreater(index_response.json()["data"]["chunk_count"], 0)

        query_response = client.post("/api/v1/rag/query", json={
            "collection_id": "api-demo",
            "question": "可靠回答为什么需要引用？",
            "top_k": 3,
        })
        self.assertEqual(200, query_response.status_code)
        self.assertTrue(query_response.json()["data"]["evidence"])


if __name__ == "__main__":
    unittest.main()
