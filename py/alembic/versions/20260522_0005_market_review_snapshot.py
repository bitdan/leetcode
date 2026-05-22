"""add market review snapshot tables

Revision ID: 20260522_0005
Revises: 20260518_0004
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260522_0005"
down_revision: Union[str, None] = "20260518_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_review_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=32), server_default=sa.text("'akshare'"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'success'"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "source", name="uq_market_review_runs_date_source"),
    )
    op.create_index("idx_market_review_runs_status_date", "market_review_runs", ["status", "trade_date"])

    op.create_table(
        "market_limit_up_pool",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("industry", sa.String(length=64), server_default=sa.text("''"), nullable=False),
        sa.Column("latest_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("change_percent", sa.Numeric(10, 4), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("circulating_market_value", sa.Numeric(20, 2), nullable=True),
        sa.Column("seal_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("first_limit_time", sa.String(length=16), server_default=sa.text("''"), nullable=False),
        sa.Column("last_limit_time", sa.String(length=16), server_default=sa.text("''"), nullable=False),
        sa.Column("open_count", sa.Integer(), nullable=True),
        sa.Column("consecutive_boards", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("limit_up_stat", sa.String(length=32), server_default=sa.text("''"), nullable=False),
        sa.Column("board_quality_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"),
                  nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"),
                  nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "code", name="uq_market_limit_up_pool_date_code"),
    )
    op.create_index("idx_market_limit_up_pool_date_boards", "market_limit_up_pool",
                    ["trade_date", "consecutive_boards"])
    op.create_index("idx_market_limit_up_pool_date_industry", "market_limit_up_pool", ["trade_date", "industry"])

    op.create_table(
        "market_sector_strength",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("industry", sa.String(length=64), nullable=False),
        sa.Column("limit_up_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("advanced_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_consecutive_boards", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("total_seal_amount", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("total_amount", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("open_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("core_stocks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"),
                  nullable=False),
        sa.Column("strength_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("risk_tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"),
                  nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "industry", name="uq_market_sector_strength_date_industry"),
    )
    op.create_index("idx_market_sector_strength_date_score", "market_sector_strength", ["trade_date", "strength_score"])

    op.create_table(
        "market_candidate_pool",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("pool_type", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("industry", sa.String(length=64), server_default=sa.text("''"), nullable=False),
        sa.Column("target_boards", sa.Integer(), server_default=sa.text("2"), nullable=False),
        sa.Column("candidate_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("level", sa.String(length=32), server_default=sa.text("'观察'"), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"),
                  nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"),
                  nullable=False),
        sa.Column("rule_version", sa.String(length=32), server_default=sa.text("'v1'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "pool_type", "code", name="uq_market_candidate_pool_date_type_code"),
    )
    op.create_index("idx_market_candidate_pool_date_type_score", "market_candidate_pool",
                    ["trade_date", "pool_type", "candidate_score"])

    op.create_table(
        "market_review_signal",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("industry", sa.String(length=64), server_default=sa.text("''"), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("signal_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"),
                  nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"),
                  nullable=False),
        sa.Column("rule_version", sa.String(length=32), server_default=sa.text("'v1'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "signal_type", "code", name="uq_market_review_signal_date_type_code"),
    )
    op.create_index("idx_market_review_signal_date_type_score", "market_review_signal",
                    ["trade_date", "signal_type", "signal_score"])


def downgrade() -> None:
    op.drop_index("idx_market_review_signal_date_type_score", table_name="market_review_signal")
    op.drop_table("market_review_signal")
    op.drop_index("idx_market_candidate_pool_date_type_score", table_name="market_candidate_pool")
    op.drop_table("market_candidate_pool")
    op.drop_index("idx_market_sector_strength_date_score", table_name="market_sector_strength")
    op.drop_table("market_sector_strength")
    op.drop_index("idx_market_limit_up_pool_date_industry", table_name="market_limit_up_pool")
    op.drop_index("idx_market_limit_up_pool_date_boards", table_name="market_limit_up_pool")
    op.drop_table("market_limit_up_pool")
    op.drop_index("idx_market_review_runs_status_date", table_name="market_review_runs")
    op.drop_table("market_review_runs")
