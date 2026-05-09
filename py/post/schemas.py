from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PostCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=20000)


class PostUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=20000)


class PostItem(BaseModel):
    id: str
    title: str
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
