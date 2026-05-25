"""set market review snapshot status default

Revision ID: 20260525_0009
Revises: 20260523_0008
Create Date: 2026-05-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260525_0009"
down_revision: Union[str, None] = "20260523_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "market_review_runs",
        "status",
        server_default=sa.text("'final'"),
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "market_review_runs",
        "status",
        server_default=sa.text("'success'"),
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )
