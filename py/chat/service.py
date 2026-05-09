import asyncio
import contextlib
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional, Set

import redis
import redis.asyncio as async_redis
from auth.schemas import UserInfo
from chat.schemas import ChatMessage
from fastapi import WebSocket

logger = logging.getLogger(__name__)


def dump_model(model) -> dict:
    return model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()


class ChatService:
    def __init__(self, history_limit: int = 100):
        self.history_limit = history_limit
        maxlen = history_limit if history_limit > 0 else None
        self.messages_by_channel: Dict[str, Deque[ChatMessage]] = defaultdict(lambda: deque(maxlen=maxlen))
        self.connections_by_channel: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def get_history(self, channel: str, limit: int = 50) -> List[ChatMessage]:
        messages = list(self.messages_by_channel[channel])
        safe_limit = max(1, min(limit, self.history_limit)) if self.history_limit > 0 else max(1, limit)
        return messages[-safe_limit:]

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


class RedisChatService(ChatService):
    HISTORY_KEY_PREFIX = "chat:history:"
    PUBSUB_CHANNEL_PREFIX = "chat:pubsub:"

    def __init__(
            self,
            host: str,
            port: int,
            database: int,
            password: str,
            decode_responses: bool,
            history_limit: int = 100,
            history_ttl_seconds: int = 7 * 24 * 60 * 60,
    ):
        super().__init__(history_limit=history_limit)
        self.history_ttl_seconds = history_ttl_seconds
        self.instance_id = str(uuid.uuid4())
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=database,
            password=password,
            decode_responses=decode_responses,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        self.redis_client.ping()
        self.async_redis_client = async_redis.Redis(
            host=host,
            port=port,
            db=database,
            password=password,
            decode_responses=decode_responses,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        self._pubsub = None
        self._listener_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._listener_task and not self._listener_task.done():
            return
        await self.async_redis_client.ping()
        self._pubsub = self.async_redis_client.pubsub()
        await self._pubsub.psubscribe(f"{self.PUBSUB_CHANNEL_PREFIX}*")
        self._listener_task = asyncio.create_task(self._listen_for_messages())

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None
        if self._pubsub:
            with contextlib.suppress(Exception):
                await self._pubsub.punsubscribe(f"{self.PUBSUB_CHANNEL_PREFIX}*")
                await self._pubsub.close()
            self._pubsub = None
        await self.async_redis_client.close()

    def get_history(self, channel: str, limit: int = 50) -> List[ChatMessage]:
        safe_limit = max(1, min(limit, self.history_limit)) if self.history_limit > 0 else max(1, limit)
        payloads = self.redis_client.lrange(self._history_key(channel), -safe_limit, -1)
        messages: List[ChatMessage] = []
        for payload in payloads:
            try:
                data = json.loads(payload)
                messages.append(self._build_message(data))
            except Exception:
                logger.warning("Failed to decode chat history payload", exc_info=True)
        return messages

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
        payload = {"type": "message", "channel": channel, "message": dump_model(message)}
        serialized_message = json.dumps(dump_model(message), ensure_ascii=False)
        serialized_payload = json.dumps(payload, ensure_ascii=False)

        pipe = self.redis_client.pipeline()
        history_key = self._history_key(channel)
        pipe.rpush(history_key, serialized_message)
        if self.history_limit > 0:
            pipe.ltrim(history_key, -self.history_limit, -1)
        if self.history_ttl_seconds > 0:
            pipe.expire(history_key, self.history_ttl_seconds)
        pipe.publish(self._pubsub_channel(channel), serialized_payload)
        pipe.execute()
        return message

    async def _listen_for_messages(self) -> None:
        while True:
            try:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    await asyncio.sleep(0.01)
                    continue
                data = json.loads(message["data"])
                channel = data.get("channel")
                if channel:
                    await self.broadcast(channel, data)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Redis chat pubsub listener failed")
                await asyncio.sleep(1)

    def _history_key(self, channel: str) -> str:
        return f"{self.HISTORY_KEY_PREFIX}{channel}"

    def _pubsub_channel(self, channel: str) -> str:
        return f"{self.PUBSUB_CHANNEL_PREFIX}{channel}"

    def _build_message(self, data: dict) -> ChatMessage:
        return ChatMessage.model_validate(data) if hasattr(ChatMessage, "model_validate") else ChatMessage.parse_obj(
            data)
