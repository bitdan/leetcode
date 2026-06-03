import json
from pathlib import Path
from typing import Iterable

from agent_runtime.schemas import AgentRuntimeRequest
from agent_runtime.service import AgentRuntimeService
from project_agent.schemas import (
    ProjectAgentConfirmationResponse,
    ProjectAgentEvalCaseResult,
    ProjectAgentEvalRequest,
    ProjectAgentEvalResponse,
    ProjectAgentIndexResponse,
    ProjectAgentRequest,
    ProjectAgentResponse,
)


class ProjectAgentService:
    """Compatibility facade for the consolidated agent runtime."""

    def __init__(self, project_root: Path):
        self.runtime = AgentRuntimeService(project_root)

    def chat(self, request: ProjectAgentRequest) -> ProjectAgentResponse:
        response = self.runtime.run(self._to_runtime_request(request))
        return ProjectAgentResponse(
            answer=response.answer,
            session_id=response.session_id,
            citations=response.citations,
            tool_calls=[call.model_dump() for call in response.tool_calls],
            structured_content=response.structured_content,
        )

    def build_index(self, max_files: int = 300, force: bool = False) -> ProjectAgentIndexResponse:
        return ProjectAgentIndexResponse(**self.runtime.build_index(max_files=max_files, force=force))

    def stream_chat(self, request: ProjectAgentRequest) -> Iterable[str]:
        yield self._sse("step", {"node": "start", "status": "running"})
        response = self.chat(request)
        for call in response.tool_calls:
            yield self._sse(
                "tool_result",
                {
                    "tool_name": call.tool_name,
                    "status": call.status,
                    "summary": call.output_summary,
                    "latency_ms": call.latency_ms,
                },
            )
        yield self._sse("final", response.model_dump())

    def confirm(self, confirmation_id: str, approved: bool) -> ProjectAgentConfirmationResponse:
        response = self.runtime.confirm(confirmation_id, approved)
        return ProjectAgentConfirmationResponse(
            confirmation_id=response.confirmation_id,
            status=response.status,
            answer=response.answer,
            tool_call=response.tool_call.model_dump() if response.tool_call else None,
        )

    def run_eval_cases(self, payload: ProjectAgentEvalRequest) -> ProjectAgentEvalResponse:
        results = []
        passed_count = 0
        for case in payload.cases:
            response = self.chat(
                ProjectAgentRequest(
                    message=case.message,
                    session_id=None,
                    max_results=10,
                    use_rag=True,
                )
            )
            answer_blob = (response.answer + "\n" + "\n".join(response.citations)).lower()
            matched_terms = [item for item in case.must_include if item.lower() in answer_blob]
            used_tools = {call.tool_name for call in response.tool_calls}
            matched_tools = [item for item in case.tool_must_include if item in used_tools]
            answer_score = 1.0 if not case.must_include else len(matched_terms) / len(case.must_include)
            tool_score = 1.0 if not case.tool_must_include else len(matched_tools) / len(case.tool_must_include)
            passed = answer_score >= 0.8 and tool_score >= 1.0
            if passed:
                passed_count += 1
            results.append(
                ProjectAgentEvalCaseResult(
                    name=case.name,
                    passed=passed,
                    answer_score=round(answer_score, 4),
                    tool_score=round(tool_score, 4),
                    reason=f"matched_terms={matched_terms}; matched_tools={matched_tools}",
                )
            )
        total = len(payload.cases)
        return ProjectAgentEvalResponse(total=total, passed=passed_count, failed=total - passed_count, results=results)

    def _to_runtime_request(self, request: ProjectAgentRequest) -> AgentRuntimeRequest:
        return AgentRuntimeRequest(
            message=request.message,
            session_id=request.session_id,
            history=request.history,
            max_results=request.max_results,
            use_rag=request.use_rag,
        )

    def _sse(self, event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
