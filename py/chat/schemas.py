from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    id: str
    channel: str
    type: Literal["message", "system"] = "message"
    user_id: Optional[str] = None
    username: Optional[str] = None
    content: str = Field(min_length=1, max_length=500)
    created_at: float


class ChatSendPayload(BaseModel):
    type: Literal["message"] = "message"
    content: str = Field(min_length=1, max_length=500)
