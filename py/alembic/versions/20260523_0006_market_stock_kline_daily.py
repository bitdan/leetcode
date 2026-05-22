"""add market stock kline daily table

Revision ID: 20260523_0006
Revises: 20260522_0005
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260523_0006"
down_revision: Union[str, None] = "20260522_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_stock_kline_daily",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
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
        sa.UniqueConstraint("trade_date", "code", name="uq_market_stock_kline_daily_date_code"),
    )
    op.create_index("idx_market_stock_kline_daily_code_date", "market_stock_kline_daily", ["code", "trade_date"])


def downgrade() -> None:
    op.drop_index("idx_market_stock_kline_daily_code_date", table_name="market_stock_kline_daily")
    op.drop_table("market_stock_kline_daily")
