from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ProjectAgentRequest(BaseModel):
    message: str = Field(..., description="User question about the current project")
    history: List[Dict[str, str]] = Field(default_factory=list)
    max_results: int = Field(8, ge=1, le=20)


class ProjectAgentToolCall(BaseModel):
    tool_name: str
    input_payload: Dict[str, Any]
    output_summary: str
    status: str
    latency_ms: int


class ProjectAgentResponse(BaseModel):
    answer: str
    citations: List[str] = Field(default_factory=list)
    tool_calls: List[ProjectAgentToolCall] = Field(default_factory=list)
    structured_content: Dict[str, Any] = Field(default_factory=dict)

