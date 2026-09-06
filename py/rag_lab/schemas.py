from typing import List, Optional

from pydantic import BaseModel, Field


class RagDocumentInput(BaseModel):
    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=40000)
    source: str = Field(default="", max_length=500)


class RagIndexRequest(BaseModel):
    collection_id: str = Field(default="default", min_length=1, max_length=80)
    documents: List[RagDocumentInput] = Field(..., min_length=1, max_length=12)


class RagQueryRequest(BaseModel):
    collection_id: str = Field(default="default", min_length=1, max_length=80)
    question: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


class RagIndexSummary(BaseModel):
    collection_id: str
    document_count: int
    chunk_count: int
    graph_edge_count: int
    vocabulary_size: int


class RagEvidence(BaseModel):
    rank: int
    chunk_id: str
    document_id: str
    title: str
    heading: str
    source: str
    content: str
    matched_terms: List[str] = Field(default_factory=list)
    lexical_score: float
    semantic_score: float
    graph_score: float
    diversity_penalty: float
    final_score: float


class RagGraphEdge(BaseModel):
    source_chunk_id: str
    target_chunk_id: str
    weight: float
    reason: str


class RagQueryDiagnostics(BaseModel):
    query_terms: List[str] = Field(default_factory=list)
    expanded_terms: List[str] = Field(default_factory=list)
    retrieval_strategy: str
    confidence: float
    confidence_label: str
    knowledge_gap: str


class RagQueryResult(BaseModel):
    answer: str
    evidence: List[RagEvidence] = Field(default_factory=list)
    graph_edges: List[RagGraphEdge] = Field(default_factory=list)
    diagnostics: RagQueryDiagnostics
