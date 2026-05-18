import logging
import uuid
from typing import Optional

from agent_eval.db_models import AgentFeedback, AgentRun, AgentToolCall
from agent_eval.schemas import AgentFeedbackRequest, AgentRunRecord, AgentToolCallRecord
from db.session import create_session_factory, session_scope
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class AgentEvalStoreUnavailable(RuntimeError):
    pass


class AgentEvalStore:
    def __init__(self, postgres_dsn: str):
        self.unavailable_reason = ""
        self.session_factory = None
        try:
            self.session_factory = create_session_factory(postgres_dsn)
        except ModuleNotFoundError:
            self.unavailable_reason = "缺少 PostgreSQL 驱动，请先安装 py/requirements.txt 中的依赖"
        except Exception:
            logger.exception("PostgreSQL agent eval store initialization failed")
            self.unavailable_reason = "PostgreSQL 连接初始化失败，请检查 POSTGRES_DSN 和数据库状态"

    def close(self) -> None:
        if not self.session_factory:
            return
        self.session_factory.kw["bind"].dispose()

    def is_available(self) -> bool:
        return bool(self.session_factory)

    def create_run(self, record: AgentRunRecord) -> None:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                session.add(AgentRun(**self._dump_model(record)))
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def create_tool_call(self, record: AgentToolCallRecord) -> None:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                session.add(AgentToolCall(**self._dump_model(record)))
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def create_feedback(self, payload: AgentFeedbackRequest, user_id: Optional[str]) -> str:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                run_id = payload.run_id
                if not run_id and payload.trace_id:
                    run_id = session.scalar(select(AgentRun.id).where(AgentRun.trace_id == payload.trace_id))
                if not run_id:
                    raise ValueError("run_id or trace_id is required")
                exists = session.scalar(select(AgentRun.id).where(AgentRun.id == run_id))
                if not exists:
                    raise ValueError("Agent run not found")
                feedback_id = f"feedback_{uuid.uuid4().hex}"
                session.add(
                    AgentFeedback(
                        id=feedback_id,
                        run_id=run_id,
                        user_id=user_id,
                        rating=payload.rating,
                        is_helpful=payload.is_helpful,
                        is_resolved=payload.is_resolved,
                        needs_human_takeover=payload.needs_human_takeover,
                        hallucination_reported=payload.hallucination_reported,
                        feedback_text=payload.feedback_text,
                    )
                )
                return feedback_id
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def summarize(self) -> dict:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                return self._summarize_session(session)
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def _summarize_session(self, session) -> dict:
        total_runs = int(session.scalar(select(func.count()).select_from(AgentRun)) or 0)
        if total_runs == 0:
            return {}

        success_runs = int(
            session.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.status == "success")) or 0
        )
        avg_steps = float(session.scalar(select(func.avg(AgentRun.steps_count))) or 0)
        avg_latency_ms = float(session.scalar(select(func.avg(AgentRun.latency_ms))) or 0)
        avg_retry_count = float(session.scalar(select(func.avg(AgentRun.retry_count))) or 0)
        total_tokens = int(session.scalar(select(func.coalesce(func.sum(AgentRun.total_tokens), 0))) or 0)
        token_cost = float(session.scalar(select(func.coalesce(func.sum(AgentRun.estimated_cost), 0))) or 0)

        latencies = [
            int(value)
            for value in session.scalars(select(AgentRun.latency_ms).order_by(AgentRun.latency_ms.asc())).all()
        ]
        p95_latency_ms = self._percentile(latencies, 0.95)

        total_tool_calls = int(session.scalar(select(func.count()).select_from(AgentToolCall)) or 0)
        successful_tool_calls = int(
            session.scalar(
                select(func.count()).select_from(AgentToolCall).where(AgentToolCall.status == "success")
            ) or 0
        )

        feedback_count = int(session.scalar(select(func.count()).select_from(AgentFeedback)) or 0)
        human_takeovers = int(
            session.scalar(
                select(func.count()).select_from(AgentFeedback).where(AgentFeedback.needs_human_takeover.is_(True))
            ) or 0
        )
        hallucinations = int(
            session.scalar(
                select(func.count()).select_from(AgentFeedback).where(AgentFeedback.hallucination_reported.is_(True))
            ) or 0
        )
        rating_avg = float(session.scalar(select(func.avg(AgentFeedback.rating))) or 0)
        resolved_count = int(
            session.scalar(
                select(func.count()).select_from(AgentFeedback).where(AgentFeedback.is_resolved.is_(True))
            ) or 0
        )
        resolution_base = int(
            session.scalar(
                select(func.count()).select_from(AgentFeedback).where(AgentFeedback.is_resolved.is_not(None))
            ) or 0
        )

        return {
            "total_runs": total_runs,
            "success_rate": self._ratio(success_runs, total_runs),
            "tool_success_rate": self._ratio(successful_tool_calls, total_tool_calls),
            "avg_steps": avg_steps,
            "avg_latency_ms": avg_latency_ms,
            "p95_latency_ms": p95_latency_ms,
            "avg_retry_count": avg_retry_count,
            "total_tokens": total_tokens,
            "token_cost": token_cost,
            "human_takeover_rate": self._ratio(human_takeovers, feedback_count),
            "hallucination_rate": self._ratio(hallucinations, feedback_count),
            "user_satisfaction": rating_avg,
            "resolution_rate": self._ratio(resolved_count, resolution_base),
        }

    def _ensure_available(self) -> None:
        if not self.session_factory:
            raise AgentEvalStoreUnavailable(self.unavailable_reason or "POSTGRES_DSN 未配置，Agent 评测暂不可用")

    def _ratio(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0
        return round(numerator / denominator, 4)

    def _percentile(self, values: list[int], percentile: float) -> float:
        if not values:
            return 0
        index = max(0, min(len(values) - 1, int(round((len(values) - 1) * percentile))))
        return float(values[index])

    def _dump_model(self, model) -> dict:
        return model.model_dump() if hasattr(model, "model_dump") else model.dict()

    def _mark_unavailable(self, exc: SQLAlchemyError):
        logger.warning("Agent eval store unavailable after database error: %s", exc.__class__.__name__)
        self.unavailable_reason = "Agent 评测表不可用，请先运行 Alembic 迁移"
        self.session_factory = None
        raise AgentEvalStoreUnavailable(self.unavailable_reason) from exc
