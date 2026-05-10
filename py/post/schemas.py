from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PostCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    category: str = Field(default="经验分享", min_length=1, max_length=64)
    tags: List[str] = Field(default_factory=list)
    content: str = Field(..., min_length=1, max_length=20000)


class PostUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    category: str = Field(default="经验分享", min_length=1, max_length=64)
    tags: List[str] = Field(default_factory=list)
    content: str = Field(..., min_length=1, max_length=20000)


class PostCommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[str] = None


class PostItem(BaseModel):
    id: str
    title: str
    category: str
    tags: List[str] = Field(default_factory=list)
    content: Optional[str] = None
    author_id: str
    author_name: str
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime
    can_edit: bool = False


class PostListData(BaseModel):
    items: List[PostItem]
    total: int
    page: int
    page_size: int


class PostCommentItem(BaseModel):
    id: str
    post_id: str
    parent_id: Optional[str] = None
    author_id: str
    author_name: str
    reply_to_author_name: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime
    can_edit: bool = False
