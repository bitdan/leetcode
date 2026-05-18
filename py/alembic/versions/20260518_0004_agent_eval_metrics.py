"""add agent evaluation metrics

Revision ID: 20260518_0004
Revises: 20260510_0003
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260518_0004"
down_revision: Union[str, None] = "20260510_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("route", sa.String(length=64), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_text", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("structured_content", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("steps_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_cost", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), server_default=sa.text("'default'"), nullable=False),
        sa.Column("model_name", sa.String(length=128), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trace_id"),
    )
    op.create_index("idx_agent_runs_route_created", "agent_runs", ["route", "created_at"])
    op.create_index("idx_agent_runs_status_created", "agent_runs", ["status", "created_at"])
    op.create_index("idx_agent_runs_prompt_version", "agent_runs", ["prompt_version", "created_at"])
    op.create_index("idx_agent_runs_user", "agent_runs", ["user_id", "created_at"])

    op.create_table(
        "agent_tool_calls",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=True),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_agent_tool_calls_run", "agent_tool_calls", ["run_id"])
    op.create_index("idx_agent_tool_calls_tool_created", "agent_tool_calls", ["tool_name", "created_at"])
    op.create_index("idx_agent_tool_calls_status_created", "agent_tool_calls", ["status", "created_at"])

    op.create_table(
        "agent_feedback",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("is_helpful", sa.Boolean(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=True),
        sa.Column("needs_human_takeover", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("hallucination_reported", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_agent_feedback_run", "agent_feedback", ["run_id"])
    op.create_index("idx_agent_feedback_created", "agent_feedback", ["created_at"])
    op.create_index("idx_agent_feedback_user", "agent_feedback", ["user_id", "created_at"])

    op.create_table(
        "agent_eval_cases",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("route", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("expected_payload", sa.JSON(), nullable=True),
        sa.Column("source_run_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["source_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_agent_eval_cases_route_status", "agent_eval_cases", ["route", "status"])
    op.create_index("idx_agent_eval_cases_created", "agent_eval_cases", ["created_at"])

    op.create_table(
        "agent_eval_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), server_default=sa.text("'default'"), nullable=False),
        sa.Column("route_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("answer_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("safety_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("hallucination_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("passed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("judge_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["agent_eval_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_agent_eval_results_case", "agent_eval_results", ["case_id", "created_at"])
    op.create_index("idx_agent_eval_results_prompt_version", "agent_eval_results", ["prompt_version", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_agent_eval_results_prompt_version", table_name="agent_eval_results")
    op.drop_index("idx_agent_eval_results_case", table_name="agent_eval_results")
    op.drop_table("agent_eval_results")

    op.drop_index("idx_agent_eval_cases_created", table_name="agent_eval_cases")
    op.drop_index("idx_agent_eval_cases_route_status", table_name="agent_eval_cases")
    op.drop_table("agent_eval_cases")

    op.drop_index("idx_agent_feedback_user", table_name="agent_feedback")
    op.drop_index("idx_agent_feedback_created", table_name="agent_feedback")
    op.drop_index("idx_agent_feedback_run", table_name="agent_feedback")
    op.drop_table("agent_feedback")

    op.drop_index("idx_agent_tool_calls_status_created", table_name="agent_tool_calls")
    op.drop_index("idx_agent_tool_calls_tool_created", table_name="agent_tool_calls")
    op.drop_index("idx_agent_tool_calls_run", table_name="agent_tool_calls")
    op.drop_table("agent_tool_calls")

    op.drop_index("idx_agent_runs_user", table_name="agent_runs")
    op.drop_index("idx_agent_runs_prompt_version", table_name="agent_runs")
    op.drop_index("idx_agent_runs_status_created", table_name="agent_runs")
    op.drop_index("idx_agent_runs_route_created", table_name="agent_runs")
    op.drop_table("agent_runs")
