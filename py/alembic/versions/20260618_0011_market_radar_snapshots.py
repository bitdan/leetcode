"""market radar snapshots

Revision ID: 20260618_0011
Revises: 20260527_0010
Create Date: 2026-06-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260618_0011"
down_revision = "20260527_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_radar_sector_snapshot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("sector_name", sa.String(length=64), nullable=False),
        sa.Column("sector_type", sa.String(length=32), server_default=sa.text("'industry'"), nullable=False),
        sa.Column("heat_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("momentum_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("liquidity_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("breadth_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("limit_up_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("strong_stock_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("stock_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rise_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("change_percent", sa.Numeric(10, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("total_amount", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("core_stocks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "sector_type", "sector_name", name="uq_market_radar_sector_date_type_name"),
    )
    op.create_index(
        "idx_market_radar_sector_date_score",
        "market_radar_sector_snapshot",
        ["trade_date", "heat_score"],
    )

    op.create_table(
        "market_radar_candidate_snapshot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("industry", sa.String(length=64), server_default=sa.text("''"), nullable=False),
        sa.Column("latest_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("change_percent", sa.Numeric(10, 4), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("candidate_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("sector_heat_score", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("signal_type", sa.String(length=64), server_default=sa.text("'sector_strength'"), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "code", "signal_type", name="uq_market_radar_candidate_date_code_signal"),
    )
    op.create_index(
        "idx_market_radar_candidate_date_score",
        "market_radar_candidate_snapshot",
        ["trade_date", "candidate_score"],
    )
    op.create_index(
        "idx_market_radar_candidate_date_industry",
        "market_radar_candidate_snapshot",
        ["trade_date", "industry"],
    )


def downgrade() -> None:
    op.drop_index("idx_market_radar_candidate_date_industry", table_name="market_radar_candidate_snapshot")
    op.drop_index("idx_market_radar_candidate_date_score", table_name="market_radar_candidate_snapshot")
    op.drop_table("market_radar_candidate_snapshot")
    op.drop_index("idx_market_radar_sector_date_score", table_name="market_radar_sector_snapshot")
    op.drop_table("market_radar_sector_snapshot")
