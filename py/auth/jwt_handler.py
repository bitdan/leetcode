import jwt
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from config.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from auth.models import TokenData

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTHandler:
    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        self.expiration_hours = JWT_EXPIRATION_HOURS

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False

    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        try:
            # 限制密码长度，避免bcrypt错误
            if len(password) > 72:
                password = password[:72]
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"密码哈希生成失败: {e}")
            raise

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问token"""
        try:
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(hours=self.expiration_hours)
            
            to_encode.update({
                "exp": expire,
                "iat": datetime.utcnow(),
                "jti": str(uuid.uuid4())  # JWT ID
            })
            
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"创建token失败: {e}")
            raise

    def verify_token(self, token: str) -> Optional[TokenData]:
        """验证token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            
            if user_id is None or username is None:
                return None
                
            return TokenData(user_id=user_id, username=username)
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.JWTError as e:
            logger.error(f"Token验证失败: {e}")
            return None

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码token（不验证过期时间，用于获取token信息）"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            return payload
        except jwt.JWTError as e:
            logger.error(f"Token解码失败: {e}")
            return None


# 全局JWT处理器实例
jwt_handler = JWTHandler()
