import logging
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Tuple

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


class PostStoreUnavailable(RuntimeError):
    pass


class PostStore:
    def __init__(self, postgres_dsn: str):
        self.postgres_dsn = postgres_dsn
        self.pool: Optional[Any] = None
        self.unavailable_reason = ""
        if postgres_dsn:
            try:
                from psycopg2.extras import RealDictCursor
                from psycopg2.pool import SimpleConnectionPool

                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=5,
                    dsn=postgres_dsn,
                    cursor_factory=RealDictCursor,
                )
            except ModuleNotFoundError:
                self.unavailable_reason = "缺少 psycopg2-binary，请先安装 py/requirements.txt 中的依赖"
            except Exception:
                logger.exception("PostgreSQL post store initialization failed")
                self.unavailable_reason = "PostgreSQL 连接初始化失败，请检查 POSTGRES_DSN 和数据库状态"

    @contextmanager
    def _connection(self):
        if not self.pool:
            raise PostStoreUnavailable(self.unavailable_reason or "POSTGRES_DSN 未配置，发帖功能暂不可用")
        connection = self.pool.getconn()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self.pool.putconn(connection)

    def close(self) -> None:
        if self.pool:
            self.pool.closeall()

    def list_posts(self, keyword: str, page: int, page_size: int) -> Tuple[List[PostRecord], int]:
        offset = (page - 1) * page_size
        params = {"limit": page_size, "offset": offset}
        where = ["status = 'published'"]
        if keyword:
            params["keyword"] = f"%{keyword}%"
            where.append("(title ILIKE %(keyword)s OR content ILIKE %(keyword)s)")
        where_sql = " AND ".join(where)

        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) AS total FROM post_posts WHERE {where_sql}", params)
                total = int(cursor.fetchone()["total"])
                cursor.execute(
                    f"""
                    SELECT id, title, content, author_id, author_name, view_count, like_count,
                           comment_count, created_at, updated_at
                    FROM post_posts
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                return [self._build_record(row) for row in cursor.fetchall()], total

    def get_post(self, post_id: str, increment_view: bool = False) -> Optional[PostRecord]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                if increment_view:
                    cursor.execute(
                        """
                        UPDATE post_posts
                        SET view_count = view_count + 1
                        WHERE id = %s AND status = 'published'
                        """,
                        (post_id,),
                    )
                cursor.execute(
                    """
                    SELECT id, title, content, author_id, author_name, view_count, like_count,
                           comment_count, created_at, updated_at
                    FROM post_posts
                    WHERE id = %s AND status = 'published'
                    """,
                    (post_id,),
                )
                row = cursor.fetchone()
                return self._build_record(row) if row else None

    def create_post(self, title: str, content: str, author_id: str, author_name: str) -> PostRecord:
        post_id = f"post_{uuid.uuid4().hex}"
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO post_posts (id, title, content, author_id, author_name)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, title, content, author_id, author_name, view_count, like_count,
                              comment_count, created_at, updated_at
                    """,
                    (post_id, title, content, author_id, author_name),
                )
                return self._build_record(cursor.fetchone())

    def update_post(self, post_id: str, title: str, content: str, author_id: str) -> Optional[PostRecord]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE post_posts
                    SET title = %s, content = %s, updated_at = NOW()
                    WHERE id = %s AND author_id = %s AND status = 'published'
                    RETURNING id, title, content, author_id, author_name, view_count, like_count,
                              comment_count, created_at, updated_at
                    """,
                    (title, content, post_id, author_id),
                )
                row = cursor.fetchone()
                return self._build_record(row) if row else None

    def delete_post(self, post_id: str, author_id: str) -> bool:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE post_posts
                    SET status = 'deleted', updated_at = NOW()
                    WHERE id = %s AND author_id = %s AND status = 'published'
                    """,
                    (post_id, author_id),
                )
                return cursor.rowcount > 0

    def _build_record(self, row) -> PostRecord:
        return PostRecord(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            author_id=row["author_id"],
            author_name=row["author_name"],
            view_count=int(row["view_count"]),
            like_count=int(row["like_count"]),
            comment_count=int(row["comment_count"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
