"""support nested post comment replies

Revision ID: 20260509_0002
Revises: 20260509_0001
Create Date: 2026-05-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260509_0002"
down_revision: Union[str, None] = "20260509_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("post_comments", sa.Column("parent_id", sa.String(length=64), nullable=True))
    op.add_column("post_comments", sa.Column("reply_to_author_name", sa.String(length=128), nullable=True))
    op.create_foreign_key(
        "fk_post_comments_parent_id",
        "post_comments",
        "post_comments",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_post_comments_parent", "post_comments", ["parent_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_post_comments_parent", table_name="post_comments")
    op.drop_constraint("fk_post_comments_parent_id", "post_comments", type_="foreignkey")
    op.drop_column("post_comments", "reply_to_author_name")
    op.drop_column("post_comments", "parent_id")
