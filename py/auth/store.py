import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import redis
from auth.schemas import User, UserInfo


@dataclass
class UserRecord:
    user_id: str
    username: str
    password_hash: str
    email: Optional[str]
    avatar: Optional[str]
    roles: list
    permissions: list
    created_at: str
    updated_at: str


class UserRepository(ABC):
    @abstractmethod
    def exists(self, username: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UserRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[UserRecord]:
        raise NotImplementedError

    @abstractmethod
    def save(self, record: UserRecord) -> UserRecord:
        raise NotImplementedError

    @abstractmethod
    def update(self, record: UserRecord) -> UserRecord:
        raise NotImplementedError


class SessionStore(ABC):
    @abstractmethod
    def set_token(self, user_id: str, token: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_token(self, user_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def set_user_info(self, user_id: str, user_info: Dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def delete_user_info(self, user_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extend_user_session(self, user_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def check_token_valid(self, user_id: str) -> bool:
        raise NotImplementedError


class MemorySessionStore(SessionStore):
    def __init__(self):
        self.tokens: Dict[str, str] = {}
        self.user_info: Dict[str, Dict[str, Any]] = {}

    def set_token(self, user_id: str, token: str) -> bool:
        self.tokens[user_id] = token
        return True

    def delete_token(self, user_id: str) -> bool:
        self.tokens.pop(user_id, None)
        return True

    def set_user_info(self, user_id: str, user_info: Dict[str, Any]) -> bool:
        self.user_info[user_id] = user_info
        return True

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.user_info.get(user_id)

    def delete_user_info(self, user_id: str) -> bool:
        self.user_info.pop(user_id, None)
        return True

    def extend_user_session(self, user_id: str) -> bool:
        return True

    def check_token_valid(self, user_id: str) -> bool:
        return user_id in self.tokens


class RedisSessionStore(SessionStore):
    def __init__(self, host: str, port: int, database: int, password: str, decode_responses: bool,
                 expiration_hours: int):
        self.expiration = timedelta(hours=expiration_hours)
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

    def set_token(self, user_id: str, token: str) -> bool:
        return bool(self.redis_client.setex(f"token:{user_id}", self.expiration, token))

    def delete_token(self, user_id: str) -> bool:
        return bool(self.redis_client.delete(f"token:{user_id}"))

    def set_user_info(self, user_id: str, user_info: Dict[str, Any]) -> bool:
        return bool(
            self.redis_client.setex(f"user:{user_id}", self.expiration, json.dumps(user_info, ensure_ascii=False)))

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        data = self.redis_client.get(f"user:{user_id}")
        return json.loads(data) if data else None

    def delete_user_info(self, user_id: str) -> bool:
        return bool(self.redis_client.delete(f"user:{user_id}"))

    def extend_user_session(self, user_id: str) -> bool:
        for key in (f"token:{user_id}", f"user:{user_id}"):
            if self.redis_client.exists(key):
                self.redis_client.expire(key, self.expiration)
        return True

    def check_token_valid(self, user_id: str) -> bool:
        return bool(self.redis_client.exists(f"token:{user_id}"))


class InMemoryUserRepository(UserRepository):
    def __init__(self, jwt_handler):
        now = datetime.now().isoformat()
        self.users = {
            "admin": UserRecord(
                user_id="admin_001",
                username="admin",
                password_hash=jwt_handler.get_password_hash("123456"),
                email="admin@example.com",
                avatar=None,
                roles=["admin"],
                permissions=["*"],
                created_at=now,
                updated_at=now,
            )
        }

    def exists(self, username: str) -> bool:
        return username in self.users

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        return self.users.get(username)

    def get_by_user_id(self, user_id: str) -> Optional[UserRecord]:
        for record in self.users.values():
            if record.user_id == user_id:
                return record
        return None

    def save(self, record: UserRecord) -> UserRecord:
        self.users[record.username] = record
        return record

    def update(self, record: UserRecord) -> UserRecord:
        self.users[record.username] = record
        return record


class RedisUserRepository(UserRepository):
    USERNAME_KEY_PREFIX = "auth:user:username:"
    USER_ID_KEY_PREFIX = "auth:user:id:"

    def __init__(self, host: str, port: int, database: int, password: str, decode_responses: bool, jwt_handler):
        self.jwt_handler = jwt_handler
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
        self._ensure_default_admin()

    def exists(self, username: str) -> bool:
        return bool(self.redis_client.exists(self._username_key(username)))

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        user_id = self.redis_client.get(self._username_key(username))
        if not user_id:
            return None
        return self.get_by_user_id(user_id)

    def get_by_user_id(self, user_id: str) -> Optional[UserRecord]:
        payload = self.redis_client.get(self._user_id_key(user_id))
        if not payload:
            return None
        return self._deserialize(payload)

    def save(self, record: UserRecord) -> UserRecord:
        self._persist(record)
        return record

    def update(self, record: UserRecord) -> UserRecord:
        self._persist(record)
        return record

    def _persist(self, record: UserRecord) -> None:
        payload = json.dumps(record.__dict__, ensure_ascii=False)
        pipe = self.redis_client.pipeline()
        pipe.set(self._user_id_key(record.user_id), payload)
        pipe.set(self._username_key(record.username), record.user_id)
        pipe.execute()

    def _serialize_default_admin(self) -> UserRecord:
        now = datetime.now().isoformat()
        return UserRecord(
            user_id="admin_001",
            username="admin",
            password_hash=self.jwt_handler.get_password_hash("123456"),
            email="admin@example.com",
            avatar=None,
            roles=["admin"],
            permissions=["*"],
            created_at=now,
            updated_at=now,
        )

    def _ensure_default_admin(self) -> None:
        if self.exists("admin"):
            return
        self.save(self._serialize_default_admin())

    def _username_key(self, username: str) -> str:
        return f"{self.USERNAME_KEY_PREFIX}{username}"

    def _user_id_key(self, user_id: str) -> str:
        return f"{self.USER_ID_KEY_PREFIX}{user_id}"

    def _deserialize(self, payload: str) -> UserRecord:
        data = json.loads(payload)
        return UserRecord(
            user_id=data["user_id"],
            username=data["username"],
            password_hash=data["password_hash"],
            email=data.get("email"),
            avatar=data.get("avatar"),
            roles=list(data.get("roles", [])),
            permissions=list(data.get("permissions", [])),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


def create_user_repository(settings, jwt_handler) -> UserRepository:
    if settings.use_redis_sessions:
        try:
            return RedisUserRepository(
                host=settings.redis.host,
                port=settings.redis.port,
                database=settings.redis.database,
                password=settings.redis.password,
                decode_responses=settings.redis.decode_responses,
                jwt_handler=jwt_handler,
            )
        except Exception:
            pass
    return InMemoryUserRepository(jwt_handler=jwt_handler)


def build_user(record: UserRecord) -> User:
    return User(
        user_id=record.user_id,
        username=record.username,
        email=record.email,
        avatar=record.avatar,
        created_at=datetime.fromisoformat(record.created_at),
        updated_at=datetime.fromisoformat(record.updated_at),
    )


def build_user_info(record: UserRecord) -> UserInfo:
    return UserInfo(user=build_user(record), roles=list(record.roles), permissions=list(record.permissions))
