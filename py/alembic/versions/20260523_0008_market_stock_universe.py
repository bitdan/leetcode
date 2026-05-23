"""add market stock universe table

Revision ID: 20260523_0008
Revises: 20260523_0007
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260523_0008"
down_revision: Union[str, None] = "20260523_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_stock_universe",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=64), server_default=sa.text("''"), nullable=False),
        sa.Column("market", sa.String(length=16), server_default=sa.text("''"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"),
                  nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_index(
        "idx_market_stock_universe_status_code",
        "market_stock_universe",
        ["status", "code"],
    )


def downgrade() -> None:
    op.drop_index("idx_market_stock_universe_status_code", table_name="market_stock_universe")
    op.drop_table("market_stock_universe")
