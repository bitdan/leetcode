import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Dict, List, Set

from auth.schemas import UserInfo
from chat.schemas import ChatMessage
from fastapi import WebSocket


def dump_model(model) -> dict:
    return model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()


class ChatService:
    def __init__(self, history_limit: int = 100):
        self.history_limit = history_limit
        self.messages_by_channel: Dict[str, Deque[ChatMessage]] = defaultdict(lambda: deque(maxlen=history_limit))
        self.connections_by_channel: Dict[str, Set[WebSocket]] = defaultdict(set)

    def get_history(self, channel: str, limit: int = 50) -> List[ChatMessage]:
        messages = list(self.messages_by_channel[channel])
        return messages[-max(1, min(limit, self.history_limit)):]

    def add_connection(self, channel: str, websocket: WebSocket) -> None:
        self.connections_by_channel[channel].add(websocket)

    def remove_connection(self, channel: str, websocket: WebSocket) -> None:
        connections = self.connections_by_channel.get(channel)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self.connections_by_channel.pop(channel, None)

    async def publish_user_message(self, channel: str, user_info: UserInfo, content: str) -> ChatMessage:
        message = ChatMessage(
            id=str(uuid.uuid4()),
            channel=channel,
            type="message",
            user_id=user_info.user.user_id,
            username=user_info.user.username,
            content=content,
            created_at=time.time(),
        )
        self.messages_by_channel[channel].append(message)
        await self.broadcast(channel, {"type": "message", "channel": channel, "message": dump_model(message)})
        return message

    async def broadcast(self, channel: str, payload: dict) -> None:
        stale_connections = []
        for websocket in list(self.connections_by_channel.get(channel, set())):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale_connections.append(websocket)
        for websocket in stale_connections:
            self.remove_connection(channel, websocket)
