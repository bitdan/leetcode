from typing import List, Tuple

from auth.schemas import UserInfo
from post.schemas import PostItem
from post.store import PostRecord, PostStore


class PostService:
    def __init__(self, store: PostStore):
        self.store = store

    def close(self) -> None:
        self.store.close()

    def list_posts(self, keyword: str, page: int, page_size: int, current_user: UserInfo = None) -> Tuple[
        List[PostItem], int]:
        records, total = self.store.list_posts(keyword=keyword.strip(), page=page, page_size=page_size)
        return [self._to_item(record, current_user=current_user, include_content=False) for record in records], total

    def get_post(self, post_id: str, current_user: UserInfo = None) -> PostItem:
        record = self.store.get_post(post_id, increment_view=True)
        if not record:
            raise ValueError("帖子不存在")
        return self._to_item(record, current_user=current_user, include_content=True)

    def create_post(self, title: str, content: str, current_user: UserInfo) -> PostItem:
        title = title.strip()
        content = content.strip()
        if not title or not content:
            raise ValueError("标题和正文不能为空")
        record = self.store.create_post(
            title=title,
            content=content,
            author_id=current_user.user.user_id,
            author_name=current_user.user.username,
        )
        return self._to_item(record, current_user=current_user, include_content=True)

    def update_post(self, post_id: str, title: str, content: str, current_user: UserInfo) -> PostItem:
        title = title.strip()
        content = content.strip()
        if not title or not content:
            raise ValueError("标题和正文不能为空")
        record = self.store.update_post(
            post_id=post_id,
            title=title,
            content=content,
            author_id=current_user.user.user_id,
        )
        if not record:
            raise PermissionError("帖子不存在或无权修改")
        return self._to_item(record, current_user=current_user, include_content=True)

    def delete_post(self, post_id: str, current_user: UserInfo) -> None:
        if not self.store.delete_post(post_id=post_id, author_id=current_user.user.user_id):
            raise PermissionError("帖子不存在或无权删除")

    def _to_item(self, record: PostRecord, current_user: UserInfo = None, include_content: bool = True) -> PostItem:
        return PostItem(
            id=record.id,
            title=record.title,
            content=record.content if include_content else self._excerpt(record.content),
            author_id=record.author_id,
            author_name=record.author_name,
            view_count=record.view_count,
            like_count=record.like_count,
            comment_count=record.comment_count,
            created_at=record.created_at,
            updated_at=record.updated_at,
            can_edit=bool(current_user and current_user.user.user_id == record.author_id),
        )

    def _excerpt(self, content: str) -> str:
        compact = " ".join(content.split())
        return compact[:180] + ("..." if len(compact) > 180 else "")
