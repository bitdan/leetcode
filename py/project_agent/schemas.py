from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectAgentRequest(BaseModel):
    message: str = Field(..., description="User question about the current project")
    session_id: Optional[str] = Field(None, description="Conversation session id for short-term memory")
    history: List[Dict[str, str]] = Field(default_factory=list)
    max_results: int = Field(8, ge=1, le=20)
    use_rag: bool = True


class ProjectAgentToolCall(BaseModel):
    tool_name: str
    input_payload: Dict[str, Any]
    output_summary: str
    status: str
    latency_ms: int


class ProjectAgentResponse(BaseModel):
    answer: str
    session_id: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    tool_calls: List[ProjectAgentToolCall] = Field(default_factory=list)
    structured_content: Dict[str, Any] = Field(default_factory=dict)


class ProjectAgentIndexRequest(BaseModel):
    max_files: int = Field(300, ge=1, le=2000)
    force: bool = False


class ProjectAgentIndexResponse(BaseModel):
    indexed_files: int
    chunks: int
    rebuilt: bool


class ProjectAgentEvalCase(BaseModel):
    name: str
    message: str
    must_include: List[str] = Field(default_factory=list)
    tool_must_include: List[str] = Field(default_factory=list)


class ProjectAgentEvalRequest(BaseModel):
    cases: List[ProjectAgentEvalCase]


class ProjectAgentEvalCaseResult(BaseModel):
    name: str
    passed: bool
    answer_score: float
    tool_score: float
    reason: str


class ProjectAgentEvalResponse(BaseModel):
    total: int
    passed: int
    failed: int
    results: List[ProjectAgentEvalCaseResult]


class ProjectAgentConfirmationRequest(BaseModel):
    confirmation_id: str
    approved: bool


class ProjectAgentConfirmationResponse(BaseModel):
    confirmation_id: str
    status: str
    answer: str
    tool_call: Optional[ProjectAgentToolCall] = None
