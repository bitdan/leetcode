import logging
import time
import uuid
from typing import Callable, Optional

from agent_chat.service import AgentChatRequest, AgentChatResponse
from agent_eval.schemas import (
    AgentEvalBatchResult,
    AgentEvalCaseFromRunRequest,
    AgentEvalRunRequest,
    AgentEvalSummary,
    AgentFeedbackRequest,
    AgentRunRecord,
    AgentToolCallRecord,
    AgentEvalResultRecord,
)
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
            return self.record_chat_response(
                request,
                response,
                current_user=current_user,
                fallback_run_id=run_id,
                fallback_trace_id=trace_id,
                latency_ms=latency_ms,
            )
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

    def record_chat_response(
            self,
            request: AgentChatRequest,
            response: AgentChatResponse,
            current_user: Optional[UserInfo] = None,
            fallback_run_id: Optional[str] = None,
            fallback_trace_id: Optional[str] = None,
            latency_ms: Optional[int] = None,
    ) -> AgentChatResponse:
        structured = dict(response.structured_content or {})
        run_id = response.run_id or structured.get("run_id") or fallback_run_id or f"run_{uuid.uuid4().hex}"
        trace_id = response.trace_id or structured.get("trace_id") or fallback_trace_id or f"trace_{uuid.uuid4().hex}"
        structured["run_id"] = run_id
        structured["trace_id"] = trace_id
        if response.session_id:
            structured["session_id"] = response.session_id
        response.run_id = run_id
        response.trace_id = trace_id
        response.structured_content = structured
        measured_latency = latency_ms
        if measured_latency is None:
            measured_latency = getattr(response.metrics, "latency_ms", 0)
        if response.metrics:
            response.metrics.latency_ms = measured_latency or response.metrics.latency_ms
            response.metrics.steps_count = response.metrics.steps_count or self._count_steps(structured)
        user_id = self._user_id(current_user)
        run_record = AgentRunRecord(
            id=run_id,
            trace_id=trace_id,
            user_id=user_id,
            route=response.route,
            input_text=request.message,
            output_text=response.answer,
            structured_content=structured,
            status=response.status or "success",
            latency_ms=measured_latency or 0,
            steps_count=getattr(response.metrics, "steps_count", 0) or self._count_steps(structured),
            retry_count=self._extract_int(structured, "retry_count"),
            prompt_tokens=self._extract_int(structured, "prompt_tokens"),
            completion_tokens=self._extract_int(structured, "completion_tokens"),
            total_tokens=self._extract_int(structured, "total_tokens"),
            estimated_cost=float(structured.get("estimated_cost") or 0),
            prompt_version=str(structured.get("prompt_version") or self.prompt_version),
            model_name=str(structured.get("model_name") or self.model_name),
        )
        self._safe_create_run(run_record)
        self._safe_create_tool_calls(run_id, response.route, request.message, structured, measured_latency or 0, response)
        return response

    def create_feedback(self, payload: AgentFeedbackRequest, current_user: Optional[UserInfo] = None) -> str:
        return self.store.create_feedback(payload, self._user_id(current_user))

    def create_case_from_run(self, payload: AgentEvalCaseFromRunRequest) -> str:
        return self.store.create_case_from_run(payload)

    def run_eval_cases(
            self,
            payload: AgentEvalRunRequest,
            chat_func: Callable[[AgentChatRequest], AgentChatResponse],
    ) -> AgentEvalBatchResult:
        cases = self.store.list_active_cases(payload.route, payload.limit)
        results = []
        passed_count = 0
        prompt_version = payload.prompt_version or self.prompt_version
        for case in cases:
            message = str(case.input_payload.get("message") or "")
            history = case.input_payload.get("history") or []
            response = self.run_traced_chat(AgentChatRequest(message=message, history=history), chat_func)
            expected = case.expected_payload or {}
            result_record = self._judge_case(case.id, expected, response, prompt_version)
            self.store.create_eval_result(result_record)
            if result_record.passed:
                passed_count += 1
            results.append(
                {
                    "case_id": case.id,
                    "case_name": case.name,
                    "run_id": result_record.run_id,
                    "passed": result_record.passed,
                    "route_score": result_record.route_score,
                    "answer_score": result_record.answer_score,
                    "safety_score": result_record.safety_score,
                    "hallucination_score": result_record.hallucination_score,
                    "judge_reason": result_record.judge_reason,
                }
            )
        total = len(cases)
        return AgentEvalBatchResult(total=total, passed=passed_count, failed=total - passed_count, results=results)

    def summarize(self) -> AgentEvalSummary:
        try:
            return AgentEvalSummary(**self.store.summarize())
        except AgentEvalStoreUnavailable:
            return AgentEvalSummary()

    def get_run_detail(self, run_id: str) -> dict:
        return self.store.get_run_detail(run_id)

    def list_session_runs(self, session_id: str, limit: int = 50) -> list[dict]:
        return self.store.list_session_runs(session_id, limit)

    def cancel_run(self, run_id: str) -> dict:
        return self.store.cancel_run(run_id)

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
            response: Optional[AgentChatResponse] = None,
    ) -> None:
        calls = []
        response_tool_calls = list(getattr(response, "tool_calls", []) or [])
        if response_tool_calls:
            for item in response_tool_calls:
                calls.append(
                    AgentToolCallRecord(
                        id=f"tool_{uuid.uuid4().hex}",
                        run_id=run_id,
                        tool_name=item.tool_name,
                        status=item.status,
                        latency_ms=item.latency_ms,
                        input_payload=item.input_payload,
                        output_payload={"summary": item.output_summary},
                        error_message=item.error,
                    )
                )
        else:
            trace = structured.get("trace") or []
        if not calls and isinstance(trace, list) and trace:
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

    def _judge_case(
            self,
            case_id: str,
            expected: dict,
            response: AgentChatResponse,
            prompt_version: str,
    ) -> AgentEvalResultRecord:
        expected_route = expected.get("route")
        route_score = 1.0 if not expected_route or expected_route == response.route else 0.0
        must_include = [str(item).lower() for item in expected.get("must_include") or [] if str(item).strip()]
        answer_lower = (response.answer or "").lower()
        if must_include:
            matched = sum(1 for item in must_include if item in answer_lower)
            answer_score = matched / len(must_include)
        else:
            answer_score = 1.0 if response.answer else 0.0

        forbidden_terms = [str(item).lower() for item in expected.get("forbidden_terms") or [] if str(item).strip()]
        forbidden_hits = [item for item in forbidden_terms if item in answer_lower]
        hallucination_score = 0.0 if forbidden_hits else 1.0
        safety_score = 1.0 if response.answer and not forbidden_hits else 0.0
        passed = route_score >= 1.0 and answer_score >= 0.8 and safety_score >= 1.0 and hallucination_score >= 1.0
        reason_parts = [
            f"route_score={route_score:.2f}",
            f"answer_score={answer_score:.2f}",
            f"safety_score={safety_score:.2f}",
            f"hallucination_score={hallucination_score:.2f}",
        ]
        if forbidden_hits:
            reason_parts.append("forbidden_terms=" + ",".join(forbidden_hits))
        structured = response.structured_content or {}
        return AgentEvalResultRecord(
            id=f"eval_result_{uuid.uuid4().hex}",
            case_id=case_id,
            run_id=structured.get("run_id"),
            prompt_version=prompt_version,
            route_score=route_score,
            answer_score=round(answer_score, 4),
            safety_score=safety_score,
            hallucination_score=hallucination_score,
            passed=passed,
            judge_reason="; ".join(reason_parts),
        )
