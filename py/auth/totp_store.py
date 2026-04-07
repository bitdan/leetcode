import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import redis


class TotpStore(ABC):
    @abstractmethod
    def list_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save_accounts(self, user_id: str, accounts: List[Dict[str, Any]]) -> bool:
        raise NotImplementedError


class MemoryTotpStore(TotpStore):
    def __init__(self):
        self._data: Dict[str, List[Dict[str, Any]]] = {}

    def list_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self._data.get(user_id, []))

    def save_accounts(self, user_id: str, accounts: List[Dict[str, Any]]) -> bool:
        self._data[user_id] = list(accounts)
        return True


class RedisTotpStore(TotpStore):
    def __init__(self, host: str, port: int, database: int, password: str, decode_responses: bool):
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

    def _key(self, user_id: str) -> str:
        return f"totp:accounts:{user_id}"

    def list_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        value = self.redis_client.get(self._key(user_id))
        if not value:
            return []
        return json.loads(value)

    def save_accounts(self, user_id: str, accounts: List[Dict[str, Any]]) -> bool:
        return bool(self.redis_client.set(self._key(user_id), json.dumps(accounts, ensure_ascii=False)))


def create_totp_store(settings) -> TotpStore:
    if settings.use_redis_sessions:
        try:
            return RedisTotpStore(
                host=settings.redis.host,
                port=settings.redis.port,
                database=settings.redis.database,
                password=settings.redis.password,
                decode_responses=settings.redis.decode_responses,
            )
        except Exception:
            pass
    return MemoryTotpStore()
