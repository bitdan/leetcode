"""initial tool hub auth and post tables

Revision ID: 20260509_0001
Revises:
Create Date: 2026-05-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260509_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_PASSWORD_HASH = "$2b$12$EU5Lp5TvjeohpxP6WbLJoOOGuLMF0IcIzABzEq9wAbb2DW64Bcq9G"


def upgrade() -> None:
    op.create_table(
        "sys_users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("avatar", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("roles", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[\"user\"]'::jsonb"),
                  nullable=False),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"),
                  nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("idx_sys_users_status_created", "sys_users", ["status", "created_at"])
    op.create_index("idx_sys_users_email", "sys_users", ["email"], postgresql_where=sa.text("email IS NOT NULL"))

    op.create_table(
        "post_posts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_id", sa.String(length=128), nullable=False),
        sa.Column("author_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'published'"), nullable=False),
        sa.Column("view_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("like_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("comment_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_post_posts_status_created", "post_posts", ["status", "created_at"])
    op.create_index("idx_post_posts_author", "post_posts", ["author_id", "created_at"])
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_post_posts_search
        ON post_posts
        USING GIN (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, '')))
        """
    )

    op.create_table(
        "post_comments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("post_id", sa.String(length=64), nullable=False),
        sa.Column("author_id", sa.String(length=128), nullable=False),
        sa.Column("author_name", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'published'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_post_comments_post", "post_comments", ["post_id", "created_at"])

    op.create_table(
        "post_likes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_post_likes_post_user"),
    )
    op.create_index("idx_post_likes_user", "post_likes", ["user_id", "created_at"])

    op.execute(
        f"""
        INSERT INTO sys_users (
            user_id, username, password_hash, email, avatar, status, roles, permissions, created_at, updated_at
        )
        VALUES (
            'admin_001', 'admin', '{ADMIN_PASSWORD_HASH}', 'admin@example.com', NULL, 'active',
            '["admin"]'::jsonb, '["*"]'::jsonb, NOW(), NOW()
        )
        ON CONFLICT (username) DO UPDATE
        SET user_id = EXCLUDED.user_id,
            password_hash = EXCLUDED.password_hash,
            email = EXCLUDED.email,
            status = 'active',
            roles = EXCLUDED.roles,
            permissions = EXCLUDED.permissions,
            updated_at = NOW()
        """
    )


def downgrade() -> None:
    op.drop_index("idx_post_likes_user", table_name="post_likes")
    op.drop_table("post_likes")
    op.drop_index("idx_post_comments_post", table_name="post_comments")
    op.drop_table("post_comments")
    op.drop_index("idx_post_posts_search", table_name="post_posts")
    op.drop_index("idx_post_posts_author", table_name="post_posts")
    op.drop_index("idx_post_posts_status_created", table_name="post_posts")
    op.drop_table("post_posts")
    op.drop_index("idx_sys_users_email", table_name="sys_users")
    op.drop_index("idx_sys_users_status_created", table_name="sys_users")
    op.drop_table("sys_users")
