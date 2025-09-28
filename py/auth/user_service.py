import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from auth.models import User, UserCreate, UserLogin, UserInfo
from auth.jwt_handler import jwt_handler
from auth.redis_client import redis_client

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self):
        # 模拟用户数据库，实际项目中应该使用真实的数据库
        self.users_db: Dict[str, Dict[str, Any]] = {
            # 默认管理员用户
            "admin": {
                "user_id": "admin_001",
                "username": "admin",
                "password_hash": "$2b$12$UVY9PuqA1J3ygIMZaJ4mUuC.W3HdYLCuhEeNKlcSFVARy9uqulkPG",  # admin123
                "email": "admin@example.com",
                "avatar": None,
                "roles": ["admin"],
                "permissions": ["*"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        }

    def validate_captcha(self, code: str, uuid: str) -> bool:
        """验证验证码（简化实现）"""
        # 实际项目中应该验证真实的验证码
        # 这里为了演示，只做简单的非空验证
        return len(code.strip()) > 0 and len(uuid.strip()) > 0

    def register_user(self, user_data: UserCreate) -> Optional[User]:
        """用户注册"""
        try:
            # 验证验证码
            if not self.validate_captcha(user_data.code, user_data.uuid):
                raise ValueError("验证码错误")

            # 检查用户名是否已存在
            if user_data.username in self.users_db:
                raise ValueError("用户名已存在")

            # 验证密码
            if user_data.password != user_data.confirm_password:
                raise ValueError("两次输入的密码不一致")

            if len(user_data.password) < 6:
                raise ValueError("密码长度至少6位")

            # 创建用户
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            password_hash = jwt_handler.get_password_hash(user_data.password)
            
            user_dict = {
                "user_id": user_id,
                "username": user_data.username,
                "password_hash": password_hash,
                "email": user_data.email,
                "avatar": None,
                "roles": ["user"],
                "permissions": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self.users_db[user_data.username] = user_dict
            
            # 构建User对象
            user = User(
                user_id=user_id,
                username=user_data.username,
                email=user_data.email,
                avatar=None,
                created_at=datetime.fromisoformat(user_dict["created_at"]),
                updated_at=datetime.fromisoformat(user_dict["updated_at"])
            )
            
            logger.info(f"用户注册成功: {user_data.username}")
            return user
            
        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            raise

    def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """用户认证"""
        try:
            # 验证验证码
            if not self.validate_captcha(login_data.code, login_data.uuid):
                raise ValueError("验证码错误")

            # 查找用户
            user_dict = self.users_db.get(login_data.username)
            if not user_dict:
                raise ValueError("用户名或密码错误")

            # 验证密码
            if not jwt_handler.verify_password(login_data.password, user_dict["password_hash"]):
                raise ValueError("用户名或密码错误")

            # 构建User对象
            user = User(
                user_id=user_dict["user_id"],
                username=user_dict["username"],
                email=user_dict["email"],
                avatar=user_dict["avatar"],
                created_at=datetime.fromisoformat(user_dict["created_at"]),
                updated_at=datetime.fromisoformat(user_dict["updated_at"])
            )
            
            logger.info(f"用户认证成功: {login_data.username}")
            return user
            
        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            raise

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据用户ID获取用户"""
        for user_dict in self.users_db.values():
            if user_dict["user_id"] == user_id:
                return User(
                    user_id=user_dict["user_id"],
                    username=user_dict["username"],
                    email=user_dict["email"],
                    avatar=user_dict["avatar"],
                    created_at=datetime.fromisoformat(user_dict["created_at"]),
                    updated_at=datetime.fromisoformat(user_dict["updated_at"])
                )
        return None

    def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """获取用户信息（包括角色和权限）"""
        user_dict = None
        for u in self.users_db.values():
            if u["user_id"] == user_id:
                user_dict = u
                break
        
        if not user_dict:
            return None

        user = User(
            user_id=user_dict["user_id"],
            username=user_dict["username"],
            email=user_dict["email"],
            avatar=user_dict["avatar"],
            created_at=datetime.fromisoformat(user_dict["created_at"]),
            updated_at=datetime.fromisoformat(user_dict["updated_at"])
        )

        return UserInfo(
            user=user,
            roles=user_dict["roles"],
            permissions=user_dict["permissions"]
        )

    def create_user_session(self, user: User) -> str:
        """创建用户会话"""
        try:
            # 生成token
            token_data = {
                "sub": user.user_id,
                "username": user.username
            }
            token = jwt_handler.create_access_token(token_data)
            
            # 存储token到Redis
            redis_client.set_token(user.user_id, token)
            
            # 存储用户信息到Redis
            user_info = self.get_user_info(user.user_id)
            if user_info:
                user_info_dict = {
                    "user": {
                        "user_id": user_info.user.user_id,
                        "username": user_info.user.username,
                        "email": user_info.user.email,
                        "avatar": user_info.user.avatar
                    },
                    "roles": user_info.roles,
                    "permissions": user_info.permissions
                }
                redis_client.set_user_info(user.user_id, user_info_dict)
            
            logger.info(f"用户会话创建成功: {user.username}")
            return token
            
        except Exception as e:
            logger.error(f"创建用户会话失败: {e}")
            raise

    def logout_user(self, user_id: str) -> bool:
        """用户登出"""
        try:
            # 从Redis删除token和用户信息
            redis_client.delete_token(user_id)
            redis_client.delete_user_info(user_id)
            
            logger.info(f"用户登出成功: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            return False

    def validate_user_session(self, token: str) -> Optional[UserInfo]:
        """验证用户会话"""
        try:
            # 验证token
            token_data = jwt_handler.verify_token(token)
            if not token_data:
                return None

            # 检查Redis中的token
            if not redis_client.check_token_valid(token_data.user_id):
                return None

            # 获取用户信息
            user_info_dict = redis_client.get_user_info(token_data.user_id)
            if not user_info_dict:
                return None

            # 延长会话时间
            redis_client.extend_user_session(token_data.user_id)

            # 构建UserInfo对象
            user_info = UserInfo(
                user=User(
                    user_id=user_info_dict["user"]["user_id"],
                    username=user_info_dict["user"]["username"],
                    email=user_info_dict["user"]["email"],
                    avatar=user_info_dict["user"]["avatar"],
                    created_at=datetime.fromisoformat(user_info_dict["user"].get("created_at", datetime.now().isoformat())),
                    updated_at=datetime.fromisoformat(user_info_dict["user"].get("updated_at", datetime.now().isoformat()))
                ),
                roles=user_info_dict["roles"],
                permissions=user_info_dict["permissions"]
            )

            return user_info
            
        except Exception as e:
            logger.error(f"验证用户会话失败: {e}")
            return None


# 全局用户服务实例
user_service = UserService()
