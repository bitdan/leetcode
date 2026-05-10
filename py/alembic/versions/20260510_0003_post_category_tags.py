"""add post category and tags

Revision ID: 20260510_0003
Revises: 20260509_0002
Create Date: 2026-05-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260510_0003"
down_revision: Union[str, None] = "20260509_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "post_posts",
        sa.Column("category", sa.String(length=64), server_default=sa.text("'经验分享'"), nullable=False),
    )
    op.create_index("idx_post_posts_category_created", "post_posts", ["category", "created_at"])

    op.create_table(
        "post_post_tags",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.String(length=64), nullable=False),
        sa.Column("tag_name", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "tag_name", name="uq_post_post_tags_post_tag"),
    )
    op.create_index("idx_post_post_tags_post", "post_post_tags", ["post_id"])
    op.create_index("idx_post_post_tags_tag", "post_post_tags", ["tag_name"])


def downgrade() -> None:
    op.drop_index("idx_post_post_tags_tag", table_name="post_post_tags")
    op.drop_index("idx_post_post_tags_post", table_name="post_post_tags")
    op.drop_table("post_post_tags")
    op.drop_index("idx_post_posts_category_created", table_name="post_posts")
    op.drop_column("post_posts", "category")
