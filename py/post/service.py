from typing import List, Tuple

from auth.schemas import UserInfo
from post.schemas import PostCommentItem, PostItem
from post.store import PostCommentRecord, PostRecord, PostStore


class PostService:
    def __init__(self, store: PostStore):
        self.store = store

    def close(self) -> None:
        self.store.close()

    def list_posts(
            self,
            keyword: str,
            page: int,
            page_size: int,
            current_user: UserInfo = None,
            category: str = "",
            tag: str = "",
    ) -> Tuple[List[PostItem], int]:
        records, total = self.store.list_posts(
            keyword=keyword.strip(),
            category=category.strip(),
            tag=tag.strip(),
            page=page,
            page_size=page_size,
        )
        return [self._to_item(record, current_user=current_user, include_content=False) for record in records], total

    def list_posts_filtered(
            self,
            keyword: str,
            category: str,
            tag: str,
            page: int,
            page_size: int,
            current_user: UserInfo = None,
    ) -> Tuple[List[PostItem], int]:
        return self.list_posts(
            keyword=keyword,
            page=page,
            page_size=page_size,
            current_user=current_user,
            category=category,
            tag=tag,
        )

    def get_post(self, post_id: str, current_user: UserInfo = None) -> PostItem:
        record = self.store.get_post(post_id, increment_view=True)
        if not record:
            raise ValueError("帖子不存在")
        return self._to_item(record, current_user=current_user, include_content=True)

    def create_post(self, title: str, category: str, tags: List[str], content: str, current_user: UserInfo) -> PostItem:
        title = title.strip()
        category = category.strip()
        content = content.strip()
        normalized_tags = self._normalize_tags(tags)
        if not title or not category or not content:
            raise ValueError("标题、分类和正文不能为空")
        record = self.store.create_post(
            title=title,
            category=category,
            tags=normalized_tags,
            content=content,
            author_id=current_user.user.user_id,
            author_name=current_user.user.username,
        )
        return self._to_item(record, current_user=current_user, include_content=True)

    def update_post(self, post_id: str, title: str, category: str, tags: List[str], content: str,
                    current_user: UserInfo) -> PostItem:
        title = title.strip()
        category = category.strip()
        content = content.strip()
        normalized_tags = self._normalize_tags(tags)
        if not title or not category or not content:
            raise ValueError("标题、分类和正文不能为空")
        record = self.store.update_post(
            post_id=post_id,
            title=title,
            category=category,
            tags=normalized_tags,
            content=content,
            author_id=current_user.user.user_id,
        )
        if not record:
            raise PermissionError("帖子不存在或无权修改")
        return self._to_item(record, current_user=current_user, include_content=True)

    def delete_post(self, post_id: str, current_user: UserInfo) -> None:
        if not self.store.delete_post(post_id=post_id, author_id=current_user.user.user_id):
            raise PermissionError("帖子不存在或无权删除")

    def list_comments(self, post_id: str, current_user: UserInfo = None) -> List[PostCommentItem]:
        if not self.store.get_post(post_id, increment_view=False):
            raise ValueError("帖子不存在")
        return [
            self._to_comment_item(comment, current_user=current_user)
            for comment in self.store.list_comments(post_id)
        ]

    def create_comment(self, post_id: str, content: str, current_user: UserInfo,
                       parent_id: str = None) -> PostCommentItem:
        content = content.strip()
        if not content:
            raise ValueError("回复内容不能为空")
        record = self.store.create_comment(
            post_id=post_id,
            content=content,
            author_id=current_user.user.user_id,
            author_name=current_user.user.username,
            parent_id=parent_id,
        )
        if not record:
            raise ValueError("帖子或回复不存在")
        return self._to_comment_item(record, current_user=current_user)

    def _to_item(self, record: PostRecord, current_user: UserInfo = None, include_content: bool = True) -> PostItem:
        return PostItem(
            id=record.id,
            title=record.title,
            category=record.category,
            tags=record.tags,
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

    def _normalize_tags(self, tags: List[str]) -> List[str]:
        normalized = []
        seen = set()
        for raw in tags or []:
            tag = str(raw or "").strip()
            if not tag:
                continue
            if len(tag) > 64:
                raise ValueError("标签长度不能超过 64 个字符")
            if tag in seen:
                continue
            seen.add(tag)
            normalized.append(tag)
        if len(normalized) > 8:
            raise ValueError("标签最多 8 个")
        return normalized

    def _excerpt(self, content: str) -> str:
        compact = " ".join(content.split())
        return compact[:180] + ("..." if len(compact) > 180 else "")

    def _to_comment_item(self, record: PostCommentRecord, current_user: UserInfo = None) -> PostCommentItem:
        return PostCommentItem(
            id=record.id,
            post_id=record.post_id,
            parent_id=record.parent_id,
            author_id=record.author_id,
            author_name=record.author_name,
            reply_to_author_name=record.reply_to_author_name,
            content=record.content,
            created_at=record.created_at,
            updated_at=record.updated_at,
            can_edit=bool(current_user and current_user.user.user_id == record.author_id),
        )
