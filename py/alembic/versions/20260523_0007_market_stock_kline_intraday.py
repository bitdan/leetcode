"""add market stock intraday kline table

Revision ID: 20260523_0007
Revises: 20260523_0006
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260523_0007"
down_revision: Union[str, None] = "20260523_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_stock_kline_intraday",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("bar_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("period", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=64), server_default=sa.text("''"), nullable=False),
        sa.Column("open_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("high_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("low_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("amplitude", sa.Numeric(10, 4), nullable=True),
        sa.Column("change_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("change_percent", sa.Numeric(10, 4), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"),
                  nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bar_time", "code", "period", name="uq_market_stock_kline_intraday_time_code_period"),
    )
    op.create_index(
        "idx_market_stock_kline_intraday_code_period_time",
        "market_stock_kline_intraday",
        ["code", "period", "bar_time"],
    )
    op.create_index(
        "idx_market_stock_kline_intraday_trade_date",
        "market_stock_kline_intraday",
        ["trade_date", "period"],
    )


def downgrade() -> None:
    op.drop_index("idx_market_stock_kline_intraday_trade_date", table_name="market_stock_kline_intraday")
    op.drop_index("idx_market_stock_kline_intraday_code_period_time", table_name="market_stock_kline_intraday")
    op.drop_table("market_stock_kline_intraday")
