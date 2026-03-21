import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from auth.schemas import TokenData

logger = logging.getLogger(__name__)


class JWTHandler:
    def __init__(self, secret_key: str, algorithm: str, expiration_hours: int):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(self._normalize_password(plain_password), hashed_password.encode("utf-8"))
        except Exception as exc:
            logger.error("Password verification failed: %s", exc)
            return False

    def get_password_hash(self, password: str) -> str:
        return bcrypt.hashpw(self._normalize_password(password), bcrypt.gensalt()).decode("utf-8")

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(hours=self.expiration_hours))
        payload = data.copy()
        payload.update({"exp": expire, "iat": now, "jti": str(uuid.uuid4())})
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[TokenData]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            username = payload.get("username")
            if user_id is None or username is None:
                return None
            return TokenData(user_id=user_id, username=username)
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except Exception as exc:
            logger.error("Token verification failed: %s", exc)
            return None

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
        except Exception as exc:
            logger.error("Token decode failed: %s", exc)
            return None

    def _normalize_password(self, password: str) -> bytes:
        encoded = password.encode("utf-8")
        return encoded[:72] if len(encoded) > 72 else encoded
