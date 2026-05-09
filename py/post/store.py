import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from db.session import create_session_factory, session_scope
from post.db_models import Post, PostComment
from sqlalchemy import func, or_, select

logger = logging.getLogger(__name__)


@dataclass
class PostRecord:
    id: str
    title: str
    content: str
    author_id: str
    author_name: str
    view_count: int
    like_count: int
    comment_count: int
    created_at: datetime
    updated_at: datetime


@dataclass
class PostCommentRecord:
    id: str
    post_id: str
    parent_id: Optional[str]
    author_id: str
    author_name: str
    reply_to_author_name: Optional[str]
    content: str
    created_at: datetime
    updated_at: datetime


class PostStoreUnavailable(RuntimeError):
    pass


class PostStore:
    def __init__(self, postgres_dsn: str):
        self.unavailable_reason = ""
        self.session_factory = None
        try:
            self.session_factory = create_session_factory(postgres_dsn)
        except ModuleNotFoundError:
            self.unavailable_reason = "缺少 PostgreSQL 驱动，请先安装 py/requirements.txt 中的依赖"
        except Exception:
            logger.exception("PostgreSQL post store initialization failed")
            self.unavailable_reason = "PostgreSQL 连接初始化失败，请检查 POSTGRES_DSN 和数据库状态"

    def close(self) -> None:
        if not self.session_factory:
            return
        self.session_factory.kw["bind"].dispose()

    def list_posts(self, keyword: str, page: int, page_size: int) -> Tuple[List[PostRecord], int]:
        self._ensure_available()
        offset = (page - 1) * page_size
        filters = [Post.status == "published"]
        if keyword:
            pattern = f"%{keyword}%"
            filters.append(or_(Post.title.ilike(pattern), Post.content.ilike(pattern)))

        with session_scope(self.session_factory) as session:
            total = session.scalar(select(func.count()).select_from(Post).where(*filters)) or 0
            posts = session.scalars(
                select(Post)
                .where(*filters)
                .order_by(Post.created_at.desc())
                .limit(page_size)
                .offset(offset)
            ).all()
            return [self._build_record(post) for post in posts], int(total)

    def get_post(self, post_id: str, increment_view: bool = False) -> Optional[PostRecord]:
        self._ensure_available()
        with session_scope(self.session_factory) as session:
            post = session.scalar(select(Post).where(Post.id == post_id, Post.status == "published"))
            if not post:
                return None
            if increment_view:
                post.view_count += 1
                session.flush()
            return self._build_record(post)

    def create_post(self, title: str, content: str, author_id: str, author_name: str) -> PostRecord:
        self._ensure_available()
        post = Post(
            id=f"post_{uuid.uuid4().hex}",
            title=title,
            content=content,
            author_id=author_id,
            author_name=author_name,
        )
        with session_scope(self.session_factory) as session:
            session.add(post)
            session.flush()
            session.refresh(post)
            return self._build_record(post)

    def update_post(self, post_id: str, title: str, content: str, author_id: str) -> Optional[PostRecord]:
        self._ensure_available()
        with session_scope(self.session_factory) as session:
            post = session.scalar(
                select(Post).where(Post.id == post_id, Post.author_id == author_id, Post.status == "published")
            )
            if not post:
                return None
            post.title = title
            post.content = content
            post.updated_at = datetime.now(post.updated_at.tzinfo) if post.updated_at else datetime.now()
            session.flush()
            session.refresh(post)
            return self._build_record(post)

    def delete_post(self, post_id: str, author_id: str) -> bool:
        self._ensure_available()
        with session_scope(self.session_factory) as session:
            post = session.scalar(
                select(Post).where(Post.id == post_id, Post.author_id == author_id, Post.status == "published")
            )
            if not post:
                return False
            post.status = "deleted"
            post.updated_at = datetime.now(post.updated_at.tzinfo) if post.updated_at else datetime.now()
            return True

    def list_comments(self, post_id: str) -> List[PostCommentRecord]:
        self._ensure_available()
        with session_scope(self.session_factory) as session:
            comments = session.scalars(
                select(PostComment)
                .where(PostComment.post_id == post_id, PostComment.status == "published")
                .order_by(PostComment.created_at.asc())
            ).all()
            return [self._build_comment_record(comment) for comment in comments]

    def create_comment(
            self,
            post_id: str,
            content: str,
            author_id: str,
            author_name: str,
            parent_id: Optional[str] = None,
    ) -> Optional[PostCommentRecord]:
        self._ensure_available()
        with session_scope(self.session_factory) as session:
            post = session.scalar(select(Post).where(Post.id == post_id, Post.status == "published"))
            if not post:
                return None
            parent_comment = None
            if parent_id:
                parent_comment = session.scalar(
                    select(PostComment).where(
                        PostComment.id == parent_id,
                        PostComment.post_id == post_id,
                        PostComment.status == "published",
                    )
                )
                if not parent_comment:
                    return None
            comment = PostComment(
                id=f"comment_{uuid.uuid4().hex}",
                post_id=post_id,
                parent_id=parent_id,
                author_id=author_id,
                author_name=author_name,
                reply_to_author_name=parent_comment.author_name if parent_comment else None,
                content=content,
            )
            post.comment_count += 1
            session.add(comment)
            session.flush()
            session.refresh(comment)
            return self._build_comment_record(comment)

    def _ensure_available(self) -> None:
        if not self.session_factory:
            raise PostStoreUnavailable(self.unavailable_reason or "POSTGRES_DSN 未配置，发帖功能暂不可用")

    def _build_record(self, post: Post) -> PostRecord:
        return PostRecord(
            id=post.id,
            title=post.title,
            content=post.content,
            author_id=post.author_id,
            author_name=post.author_name,
            view_count=int(post.view_count or 0),
            like_count=int(post.like_count or 0),
            comment_count=int(post.comment_count or 0),
            created_at=post.created_at,
            updated_at=post.updated_at,
        )

    def _build_comment_record(self, comment: PostComment) -> PostCommentRecord:
        return PostCommentRecord(
            id=comment.id,
            post_id=comment.post_id,
            parent_id=comment.parent_id,
            author_id=comment.author_id,
            author_name=comment.author_name,
            reply_to_author_name=comment.reply_to_author_name,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
