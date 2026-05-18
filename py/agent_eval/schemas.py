from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - pydantic v1 fallback
    ConfigDict = None


class AgentRunRecord(BaseModel):
    if ConfigDict:
        model_config = ConfigDict(protected_namespaces=())

    id: str
    trace_id: str
    user_id: Optional[str] = None
    route: str
    input_text: str
    output_text: str = ""
    structured_content: Optional[Dict[str, Any]] = None
    status: str
    latency_ms: int = 0
    steps_count: int = 0
    retry_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0
    prompt_version: str = "default"
    model_name: str = "unknown"
    error_message: Optional[str] = None


class AgentToolCallRecord(BaseModel):
    id: str
    run_id: str
    tool_name: str
    status: str
    latency_ms: int = 0
    input_payload: Optional[Dict[str, Any]] = None
    output_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class AgentFeedbackRequest(BaseModel):
    run_id: Optional[str] = None
    trace_id: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    is_helpful: Optional[bool] = None
    is_resolved: Optional[bool] = None
    needs_human_takeover: bool = False
    hallucination_reported: bool = False
    feedback_text: Optional[str] = Field(default=None, max_length=2000)


class AgentEvalCaseFromRunRequest(BaseModel):
    run_id: Optional[str] = None
    trace_id: Optional[str] = None
    name: Optional[str] = Field(default=None, max_length=200)
    expected_payload: Optional[Dict[str, Any]] = None


class AgentEvalRunRequest(BaseModel):
    route: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=200)
    prompt_version: Optional[str] = None


class AgentEvalCaseRecord(BaseModel):
    id: str
    route: str
    name: str
    input_payload: Dict[str, Any]
    expected_payload: Optional[Dict[str, Any]] = None
    source_run_id: Optional[str] = None
    status: str = "active"


class AgentEvalResultRecord(BaseModel):
    id: str
    case_id: str
    run_id: Optional[str] = None
    prompt_version: str = "default"
    route_score: float = 0
    answer_score: float = 0
    safety_score: float = 0
    hallucination_score: float = 0
    passed: bool = False
    judge_reason: Optional[str] = None


class AgentEvalBatchResult(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: List[Dict[str, Any]] = Field(default_factory=list)


class AgentEvalSummary(BaseModel):
    total_runs: int = 0
    success_rate: float = 0
    tool_success_rate: float = 0
    avg_steps: float = 0
    avg_latency_ms: float = 0
    p95_latency_ms: float = 0
    avg_retry_count: float = 0
    total_tokens: int = 0
    token_cost: float = 0
    human_takeover_rate: float = 0
    hallucination_rate: float = 0
    user_satisfaction: float = 0
    resolution_rate: float = 0
