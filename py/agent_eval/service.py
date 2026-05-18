import logging
import time
import uuid
from typing import Callable, Optional

from agent_chat.service import AgentChatRequest, AgentChatResponse
from agent_eval.schemas import AgentEvalSummary, AgentFeedbackRequest, AgentRunRecord, AgentToolCallRecord
from agent_eval.store import AgentEvalStore, AgentEvalStoreUnavailable
from auth.schemas import UserInfo

logger = logging.getLogger(__name__)


class AgentEvalService:
    def __init__(self, store: AgentEvalStore, prompt_version: str = "default", model_name: str = "unknown"):
        self.store = store
        self.prompt_version = prompt_version
        self.model_name = model_name

    def run_traced_chat(
            self,
            request: AgentChatRequest,
            chat_func: Callable[[AgentChatRequest], AgentChatResponse],
            current_user: Optional[UserInfo] = None,
    ) -> AgentChatResponse:
        started = time.perf_counter()
        trace_id = f"trace_{uuid.uuid4().hex}"
        run_id = f"run_{uuid.uuid4().hex}"
        user_id = self._user_id(current_user)
        try:
            response = chat_func(request)
            latency_ms = int((time.perf_counter() - started) * 1000)
            structured = dict(response.structured_content or {})
            structured["trace_id"] = trace_id
            structured["run_id"] = run_id
            response.structured_content = structured
            run_record = AgentRunRecord(
                id=run_id,
                trace_id=trace_id,
                user_id=user_id,
                route=response.route,
                input_text=request.message,
                output_text=response.answer,
                structured_content=structured,
                status="success",
                latency_ms=latency_ms,
                steps_count=self._count_steps(structured),
                retry_count=self._extract_int(structured, "retry_count"),
                prompt_tokens=self._extract_int(structured, "prompt_tokens"),
                completion_tokens=self._extract_int(structured, "completion_tokens"),
                total_tokens=self._extract_int(structured, "total_tokens"),
                estimated_cost=float(structured.get("estimated_cost") or 0),
                prompt_version=str(structured.get("prompt_version") or self.prompt_version),
                model_name=str(structured.get("model_name") or self.model_name),
            )
            self._safe_create_run(run_record)
            self._safe_create_tool_calls(run_id, response.route, request.message, structured, latency_ms)
            return response
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self._safe_create_run(
                AgentRunRecord(
                    id=run_id,
                    trace_id=trace_id,
                    user_id=user_id,
                    route="unknown",
                    input_text=request.message,
                    output_text="",
                    status="failed",
                    latency_ms=latency_ms,
                    steps_count=0,
                    retry_count=0,
                    prompt_version=self.prompt_version,
                    model_name=self.model_name,
                    error_message=str(exc),
                )
            )
            raise

    def create_feedback(self, payload: AgentFeedbackRequest, current_user: Optional[UserInfo] = None) -> str:
        return self.store.create_feedback(payload, self._user_id(current_user))

    def summarize(self) -> AgentEvalSummary:
        try:
            return AgentEvalSummary(**self.store.summarize())
        except AgentEvalStoreUnavailable:
            return AgentEvalSummary()

    def _safe_create_run(self, record: AgentRunRecord) -> None:
        try:
            self.store.create_run(record)
        except AgentEvalStoreUnavailable:
            logger.debug("Agent eval store unavailable; skip run trace")
        except Exception:
            logger.exception("Failed to store agent run")

    def _safe_create_tool_calls(
            self,
            run_id: str,
            route: str,
            input_text: str,
            structured: dict,
            latency_ms: int,
    ) -> None:
        trace = structured.get("trace") or []
        calls = []
        if isinstance(trace, list) and trace:
            for item in trace:
                if not isinstance(item, dict):
                    continue
                calls.append(
                    AgentToolCallRecord(
                        id=f"tool_{uuid.uuid4().hex}",
                        run_id=run_id,
                        tool_name=str(item.get("node") or route),
                        status="success" if not item.get("error") else "failed",
                        latency_ms=self._extract_int(item, "latency_ms"),
                        input_payload={"summary": item.get("input_summary")},
                        output_payload={"summary": item.get("output_summary"), "decision": item.get("decision")},
                        error_message=item.get("error"),
                    )
                )
        else:
            calls.append(
                AgentToolCallRecord(
                    id=f"tool_{uuid.uuid4().hex}",
                    run_id=run_id,
                    tool_name=route,
                    status="success",
                    latency_ms=latency_ms,
                    input_payload={"message": input_text[:1000]},
                    output_payload={"route_reason": structured.get("route_reason")},
                )
            )
        for call in calls:
            try:
                self.store.create_tool_call(call)
            except AgentEvalStoreUnavailable:
                logger.debug("Agent eval store unavailable; skip tool trace")
                return
            except Exception:
                logger.exception("Failed to store agent tool call")

    def _count_steps(self, structured: dict) -> int:
        trace = structured.get("trace")
        if isinstance(trace, list) and trace:
            return len(trace)
        return 1

    def _extract_int(self, payload: dict, key: str) -> int:
        try:
            return int(payload.get(key) or 0)
        except (TypeError, ValueError):
            return 0

    def _user_id(self, current_user: Optional[UserInfo]) -> Optional[str]:
        if not current_user:
            return None
        return getattr(getattr(current_user, "user", None), "user_id", None)
