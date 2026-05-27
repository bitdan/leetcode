import logging
import uuid
from datetime import datetime
from typing import Optional

from auth.jwt_handler import jwt_handler
from auth.redis_client import redis_client
from auth.schemas import (
    AdminPasswordReset,
    AdminUser,
    AdminUserUpdate,
    ChangePasswordRequest,
    User,
    UserCreate,
    UserInfo,
    UserLogin,
    UserProfileUpdate,
)
from auth.store import SessionStore, UserRecord, UserRepository, build_user, build_user_info, create_user_repository
from core.settings import get_settings

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repository: UserRepository, session_store: SessionStore, jwt_handler,
                 session_ttl_hours: int):
        self.user_repository = user_repository
        self.session_store = session_store
        self.jwt_handler = jwt_handler
        self.session_ttl_hours = session_ttl_hours

    def validate_captcha(self, code: str, uuid_value: str) -> bool:
        return len(code.strip()) > 0 and len(uuid_value.strip()) > 0

    def close(self) -> None:
        close = getattr(self.user_repository, "close", None)
        if callable(close):
            close()

    def register_user(self, user_data: UserCreate) -> Optional[User]:
        if not self.validate_captcha(user_data.code, user_data.uuid):
            raise ValueError("验证码错误")
        if self.user_repository.exists(user_data.username):
            raise ValueError("用户名已存在")
        if user_data.password != user_data.confirmPassword:
            raise ValueError("两次输入的密码不一致")
        if len(user_data.password) < 6:
            raise ValueError("密码长度至少6位")

        now = datetime.now().isoformat()
        record = UserRecord(
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            username=user_data.username,
            password_hash=self.jwt_handler.get_password_hash(user_data.password),
            email=user_data.email,
            avatar=None,
            status="active",
            roles=["user"],
            permissions=[],
            created_at=now,
            updated_at=now,
        )
        self.user_repository.save(record)
        logger.info("User registered: %s", user_data.username)
        return build_user(record)

    def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        if not self.validate_captcha(login_data.code, login_data.uuid):
            raise ValueError("验证码错误")
        record = self.user_repository.get_by_username(login_data.username)
        if not record or not self.jwt_handler.verify_password(login_data.password, record.password_hash):
            raise ValueError("用户名或密码错误")
        if record.status != "active":
            raise ValueError("账号已被禁用")
        logger.info("User authenticated: %s", login_data.username)
        return build_user(record)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        record = self.user_repository.get_by_user_id(user_id)
        return build_user(record) if record else None

    def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        record = self.user_repository.get_by_user_id(user_id)
        return build_user_info(record) if record else None

    def update_profile(self, user_id: str, payload: UserProfileUpdate) -> UserInfo:
        record = self.user_repository.get_by_user_id(user_id)
        if not record:
            raise ValueError("用户不存在")

        record.email = payload.email
        record.avatar = payload.avatar
        record.updated_at = datetime.now().isoformat()
        self.user_repository.update(record)
        return self._refresh_session_user_info(user_id)

    def change_password(self, user_id: str, payload: ChangePasswordRequest) -> bool:
        record = self.user_repository.get_by_user_id(user_id)
        if not record:
            raise ValueError("用户不存在")
        if not self.jwt_handler.verify_password(payload.oldPassword, record.password_hash):
            raise ValueError("原密码错误")
        if payload.newPassword != payload.confirmPassword:
            raise ValueError("两次输入的新密码不一致")
        if len(payload.newPassword) < 6:
            raise ValueError("密码长度至少6位")
        if payload.oldPassword == payload.newPassword:
            raise ValueError("新密码不能与原密码相同")

        record.password_hash = self.jwt_handler.get_password_hash(payload.newPassword)
        record.updated_at = datetime.now().isoformat()
        self.user_repository.update(record)
        self._refresh_session_user_info(user_id)
        return True

    def list_admin_users(self, keyword: Optional[str] = None, limit: int = 100, offset: int = 0) -> list[AdminUser]:
        safe_limit = max(1, min(limit, 200))
        safe_offset = max(0, offset)
        return [
            self._build_admin_user(record)
            for record in self.user_repository.list_users(keyword, safe_limit, safe_offset)
        ]

    def update_admin_user(self, target_user_id: str, payload: AdminUserUpdate) -> AdminUser:
        record = self.user_repository.get_by_user_id(target_user_id)
        if not record:
            raise ValueError("用户不存在")
        if payload.status is not None:
            if payload.status not in {"active", "disabled"}:
                raise ValueError("用户状态只能是 active 或 disabled")
            record.status = payload.status
        if payload.roles is not None:
            record.roles = self._normalize_string_list(payload.roles, "角色")
        if payload.permissions is not None:
            record.permissions = self._normalize_string_list(payload.permissions, "权限")
        if payload.email is not None:
            record.email = payload.email or None
        if payload.avatar is not None:
            record.avatar = payload.avatar or None

        record.updated_at = datetime.now().isoformat()
        self.user_repository.update(record)
        if record.status != "active":
            self.session_store.delete_token(target_user_id)
            self.session_store.delete_user_info(target_user_id)
            return self._build_admin_user(record)
        self._refresh_session_user_info(target_user_id)
        return self._build_admin_user(record)

    def reset_admin_user_password(self, target_user_id: str, payload: AdminPasswordReset) -> bool:
        record = self.user_repository.get_by_user_id(target_user_id)
        if not record:
            raise ValueError("用户不存在")
        if payload.newPassword != payload.confirmPassword:
            raise ValueError("两次输入的新密码不一致")
        if len(payload.newPassword) < 6:
            raise ValueError("密码长度至少6位")

        record.password_hash = self.jwt_handler.get_password_hash(payload.newPassword)
        record.updated_at = datetime.now().isoformat()
        self.user_repository.update(record)
        self.session_store.delete_token(target_user_id)
        self.session_store.delete_user_info(target_user_id)
        return True

    def create_user_session(self, user: User) -> str:
        token = self.jwt_handler.create_access_token({"sub": user.user_id, "username": user.username})
        self.session_store.set_token(user.user_id, token)
        self.session_store.record_login_day(user.user_id)
        self._refresh_session_user_info(user.user_id)
        return token

    def get_login_stats(self, user_id: str) -> dict:
        return self.session_store.get_login_stats(user_id)

    def _refresh_session_user_info(self, user_id: str) -> UserInfo:
        user_info = self.get_user_info(user_id)
        if user_info is None:
            raise ValueError("用户不存在")
        user_info_dict = user_info.model_dump(mode="json") if hasattr(user_info, "model_dump") else user_info.dict()
        self.session_store.set_user_info(user_id, user_info_dict)
        return user_info

    def logout_user(self, user_id: str) -> bool:
        self.session_store.delete_token(user_id)
        self.session_store.delete_user_info(user_id)
        return True

    def validate_user_session(self, token: str) -> Optional[UserInfo]:
        token_data = self.jwt_handler.verify_token(token)
        if not token_data or not token_data.user_id:
            return None

        try:
            if not self.session_store.check_token_valid(token_data.user_id):
                return None

            record = self.user_repository.get_by_user_id(token_data.user_id)
            if not record or record.status != "active":
                return None

            user_info_dict = self.session_store.get_user_info(token_data.user_id)
            if user_info_dict:
                self.session_store.extend_user_session(token_data.user_id)
                if hasattr(UserInfo, "model_validate"):
                    return UserInfo.model_validate(user_info_dict)
                return UserInfo.parse_obj(user_info_dict)
        except Exception as exc:
            logger.warning("Session store lookup failed, falling back to JWT-only auth: %s", exc)

        # Fallback for degraded session storage when token presence already passed
        # or the store itself errored during lookup.
        record = self.user_repository.get_by_user_id(token_data.user_id)
        if not record or record.status != "active":
            return None
        return build_user_info(record)

    def _normalize_string_list(self, values: list[str], label: str) -> list[str]:
        normalized = []
        for value in values:
            item = value.strip()
            if item and item not in normalized:
                normalized.append(item)
        if label == "角色" and not normalized:
            raise ValueError("角色不能为空")
        return normalized

    def _build_admin_user(self, record: UserRecord) -> AdminUser:
        return AdminUser(
            user_id=record.user_id,
            username=record.username,
            email=record.email,
            avatar=record.avatar,
            status=record.status,
            roles=list(record.roles),
            permissions=list(record.permissions),
            created_at=datetime.fromisoformat(record.created_at),
            updated_at=datetime.fromisoformat(record.updated_at),
        )


_settings = get_settings()
user_service = UserService(
    user_repository=create_user_repository(_settings, jwt_handler),
    session_store=redis_client,
    jwt_handler=jwt_handler,
    session_ttl_hours=_settings.jwt_expiration_hours,
)

__all__ = ["UserService", "user_service"]
