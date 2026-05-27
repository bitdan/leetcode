import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

import redis
from auth.db_models import SysUser
from auth.schemas import User, UserInfo
from db.session import create_session_factory, session_scope
from sqlalchemy import func, select

logger = logging.getLogger(__name__)


@dataclass
class UserRecord:
    user_id: str
    username: str
    password_hash: str
    email: Optional[str]
    avatar: Optional[str]
    status: str
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

    @abstractmethod
    def list_users(self, keyword: Optional[str] = None, limit: int = 100, offset: int = 0) -> list[UserRecord]:
        raise NotImplementedError

    @abstractmethod
    def count_users(self, keyword: Optional[str] = None) -> int:
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

    def record_login_day(self, user_id: str, login_date: Optional[date] = None) -> bool:
        return False

    def get_login_stats(self, user_id: str, today: Optional[date] = None, recent_days: int = 30) -> Dict[str, Any]:
        return build_empty_login_stats(today or date.today(), recent_days)


def build_empty_login_stats(today: date, recent_days: int = 30) -> Dict[str, Any]:
    return {
        "today": today.isoformat(),
        "logged_today": False,
        "current_year_active_days": 0,
        "current_month_active_days": 0,
        "recent_30_days_active_days": 0,
        "consecutive_days": 0,
        "recent_days": [
            {"date": (today - timedelta(days=offset)).isoformat(), "logged": False}
            for offset in range(recent_days - 1, -1, -1)
        ],
    }


class MemorySessionStore(SessionStore):
    def __init__(self):
        self.tokens: Dict[str, str] = {}
        self.user_info: Dict[str, Dict[str, Any]] = {}
        self.login_days: Dict[str, set] = {}

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

    def record_login_day(self, user_id: str, login_date: Optional[date] = None) -> bool:
        day = login_date or date.today()
        self.login_days.setdefault(user_id, set()).add(day)
        return True

    def get_login_stats(self, user_id: str, today: Optional[date] = None, recent_days: int = 30) -> Dict[str, Any]:
        day = today or date.today()
        days = self.login_days.get(user_id, set())
        recent = [day - timedelta(days=offset) for offset in range(recent_days - 1, -1, -1)]
        month_days = {item for item in days if item.year == day.year and item.month == day.month}
        consecutive = 0
        cursor = day
        while cursor in days:
            consecutive += 1
            cursor -= timedelta(days=1)
        return {
            "today": day.isoformat(),
            "logged_today": day in days,
            "current_year_active_days": len({item for item in days if item.year == day.year}),
            "current_month_active_days": len(month_days),
            "recent_30_days_active_days": len([item for item in recent if item in days]),
            "consecutive_days": consecutive,
            "recent_days": [{"date": item.isoformat(), "logged": item in days} for item in recent],
        }


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

    def record_login_day(self, user_id: str, login_date: Optional[date] = None) -> bool:
        day = login_date or date.today()
        return bool(self.redis_client.setbit(self._login_bitmap_key(user_id, day.year), day.timetuple().tm_yday - 1, 1))

    def get_login_stats(self, user_id: str, today: Optional[date] = None, recent_days: int = 30) -> Dict[str, Any]:
        day = today or date.today()
        recent = [day - timedelta(days=offset) for offset in range(recent_days - 1, -1, -1)]
        recent_flags = [self._is_login_day(user_id, item) for item in recent]
        month_active_days = sum(
            1
            for month_day in range(1, day.day + 1)
            if self._is_login_day(user_id, date(day.year, day.month, month_day))
        )

        consecutive = 0
        cursor = day
        for _ in range(366):
            if not self._is_login_day(user_id, cursor):
                break
            consecutive += 1
            cursor -= timedelta(days=1)

        return {
            "today": day.isoformat(),
            "logged_today": self._is_login_day(user_id, day),
            "current_year_active_days": int(self.redis_client.bitcount(self._login_bitmap_key(user_id, day.year))),
            "current_month_active_days": month_active_days,
            "recent_30_days_active_days": sum(1 for flag in recent_flags if flag),
            "consecutive_days": consecutive,
            "recent_days": [
                {"date": item.isoformat(), "logged": logged}
                for item, logged in zip(recent, recent_flags)
            ],
        }

    def _login_bitmap_key(self, user_id: str, year: int) -> str:
        return f"auth:login:bitmap:{user_id}:{year}"

    def _is_login_day(self, user_id: str, day: date) -> bool:
        return bool(self.redis_client.getbit(self._login_bitmap_key(user_id, day.year), day.timetuple().tm_yday - 1))


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
                status="active",
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

    def list_users(self, keyword: Optional[str] = None, limit: int = 100, offset: int = 0) -> list[UserRecord]:
        records = self._filter_users(keyword)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records[offset:offset + limit]

    def count_users(self, keyword: Optional[str] = None) -> int:
        return len(self._filter_users(keyword))

    def _filter_users(self, keyword: Optional[str] = None) -> list[UserRecord]:
        records = [item for item in self.users.values() if item.status != "deleted"]
        if keyword:
            q = keyword.lower()
            records = [
                item for item in records
                if q in item.username.lower() or q in item.user_id.lower() or q in (item.email or "").lower()
            ]
        return records


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

    def list_users(self, keyword: Optional[str] = None, limit: int = 100, offset: int = 0) -> list[UserRecord]:
        records = self._filter_users(keyword)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records[offset:offset + limit]

    def count_users(self, keyword: Optional[str] = None) -> int:
        return len(self._filter_users(keyword))

    def _filter_users(self, keyword: Optional[str] = None) -> list[UserRecord]:
        records = []
        for key in self.redis_client.scan_iter(f"{self.USER_ID_KEY_PREFIX}*"):
            payload = self.redis_client.get(key)
            if payload:
                record = self._deserialize(payload)
                if record.status != "deleted":
                    records.append(record)
        if keyword:
            q = keyword.lower()
            records = [
                item for item in records
                if q in item.username.lower() or q in item.user_id.lower() or q in (item.email or "").lower()
            ]
        return records

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
            status="active",
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
            status=data.get("status", "active"),
            roles=list(data.get("roles", [])),
            permissions=list(data.get("permissions", [])),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, postgres_dsn: str, jwt_handler):
        self.jwt_handler = jwt_handler
        self.session_factory = create_session_factory(postgres_dsn)
        self._ensure_default_admin()

    def exists(self, username: str) -> bool:
        with session_scope(self.session_factory) as session:
            return session.scalar(
                select(SysUser.id).where(SysUser.username == username, SysUser.status != "deleted").limit(1)
            ) is not None

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        with session_scope(self.session_factory) as session:
            user = session.scalar(select(SysUser).where(SysUser.username == username, SysUser.status == "active"))
            return self._deserialize(user) if user else None

    def get_by_user_id(self, user_id: str) -> Optional[UserRecord]:
        with session_scope(self.session_factory) as session:
            user = session.scalar(select(SysUser).where(SysUser.user_id == user_id, SysUser.status != "deleted"))
            return self._deserialize(user) if user else None

    def save(self, record: UserRecord) -> UserRecord:
        with session_scope(self.session_factory) as session:
            session.add(
                SysUser(
                    user_id=record.user_id,
                    username=record.username,
                    password_hash=record.password_hash,
                    email=record.email,
                    avatar=record.avatar,
                    status=record.status,
                    roles=list(record.roles),
                    permissions=list(record.permissions),
                    created_at=datetime.fromisoformat(record.created_at),
                    updated_at=datetime.fromisoformat(record.updated_at),
                )
            )
        return record

    def update(self, record: UserRecord) -> UserRecord:
        with session_scope(self.session_factory) as session:
            user = session.scalar(select(SysUser).where(SysUser.user_id == record.user_id, SysUser.status != "deleted"))
            if user:
                user.username = record.username
                user.password_hash = record.password_hash
                user.email = record.email
                user.avatar = record.avatar
                user.status = record.status
                user.roles = list(record.roles)
                user.permissions = list(record.permissions)
                user.updated_at = datetime.fromisoformat(record.updated_at)
        return record

    def list_users(self, keyword: Optional[str] = None, limit: int = 100, offset: int = 0) -> list[UserRecord]:
        with session_scope(self.session_factory) as session:
            stmt = self._user_filter_stmt(select(SysUser), keyword)
            stmt = stmt.order_by(SysUser.created_at.desc()).offset(offset).limit(limit)
            return [self._deserialize(user) for user in session.scalars(stmt).all()]

    def count_users(self, keyword: Optional[str] = None) -> int:
        with session_scope(self.session_factory) as session:
            stmt = self._user_filter_stmt(select(func.count()).select_from(SysUser), keyword)
            return int(session.scalar(stmt) or 0)

    def _user_filter_stmt(self, stmt, keyword: Optional[str] = None):
        stmt = stmt.where(SysUser.status != "deleted")
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                SysUser.username.ilike(pattern)
                | SysUser.user_id.ilike(pattern)
                | SysUser.email.ilike(pattern)
            )
        return stmt

    def close(self) -> None:
        self.session_factory.kw["bind"].dispose()

    def _ensure_default_admin(self) -> None:
        if self.exists("admin"):
            return
        now = datetime.now().isoformat()
        self.save(
            UserRecord(
                user_id="admin_001",
                username="admin",
                password_hash=self.jwt_handler.get_password_hash("123456"),
                email="admin@example.com",
                avatar=None,
                status="active",
                roles=["admin"],
                permissions=["*"],
                created_at=now,
                updated_at=now,
            )
        )

    def _deserialize(self, user: SysUser) -> UserRecord:
        return UserRecord(
            user_id=user.user_id,
            username=user.username,
            password_hash=user.password_hash,
            email=user.email,
            avatar=user.avatar,
            status=user.status,
            roles=list(user.roles or []),
            permissions=list(user.permissions or []),
            created_at=self._datetime_to_iso(user.created_at),
            updated_at=self._datetime_to_iso(user.updated_at),
        )

    def _datetime_to_iso(self, value: Any) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)


def create_user_repository(settings, jwt_handler) -> UserRepository:
    if getattr(settings, "use_postgres_user_store", True) and getattr(settings, "postgres_dsn", ""):
        try:
            return SqlAlchemyUserRepository(
                postgres_dsn=settings.postgres_dsn,
                jwt_handler=jwt_handler,
            )
        except Exception:
            logger.warning("PostgreSQL user store unavailable. Falling back to Redis or in-memory user store.",
                           exc_info=True)

    if getattr(settings, "use_redis_user_store", settings.use_redis_sessions):
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
            logger.warning("Redis user store unavailable. Falling back to in-memory user store.", exc_info=True)
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
