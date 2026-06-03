from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentRuntimeRequest(BaseModel):
    message: str = Field(..., description="User request for the project agent runtime")
    session_id: Optional[str] = None
    history: List[Dict[str, str]] = Field(default_factory=list)
    max_results: int = Field(8, ge=1, le=20)
    use_rag: bool = True


class AgentRuntimeToolCall(BaseModel):
    tool_name: str
    input_payload: Dict[str, Any]
    output_summary: str
    status: str
    latency_ms: int


class AgentRuntimeResponse(BaseModel):
    answer: str
    route: str = "project_agent"
    title: str = "项目 Agent"
    session_id: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    tool_calls: List[AgentRuntimeToolCall] = Field(default_factory=list)
    structured_content: Dict[str, Any] = Field(default_factory=dict)


class AgentRuntimeConfirmationResponse(BaseModel):
    confirmation_id: str
    status: str
    answer: str
    tool_call: Optional[AgentRuntimeToolCall] = None
