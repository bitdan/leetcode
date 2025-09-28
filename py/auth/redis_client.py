import redis
import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta
from config.config import REDIS_CONFIG

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        try:
            # 使用正确的Redis连接参数
            self.redis_client = redis.Redis(
                host=REDIS_CONFIG["host"],
                port=REDIS_CONFIG["port"],
                db=REDIS_CONFIG["database"],  # 使用db而不是database
                password=REDIS_CONFIG["password"],
                decode_responses=REDIS_CONFIG["decode_responses"],
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Redis连接成功: {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            logger.error(f"Redis配置: {REDIS_CONFIG}")
            raise

    def set_token(self, user_id: str, token: str, expiration_hours: int = 6) -> bool:
        """存储用户token"""
        try:
            key = f"token:{user_id}"
            expiration = timedelta(hours=expiration_hours)
            return self.redis_client.setex(key, expiration, token)
        except Exception as e:
            logger.error(f"存储token失败: {e}")
            return False

    def get_token(self, user_id: str) -> Optional[str]:
        """获取用户token"""
        try:
            key = f"token:{user_id}"
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"获取token失败: {e}")
            return None

    def delete_token(self, user_id: str) -> bool:
        """删除用户token"""
        try:
            key = f"token:{user_id}"
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"删除token失败: {e}")
            return False

    def set_user_info(self, user_id: str, user_info: Dict[str, Any], expiration_hours: int = 6) -> bool:
        """存储用户信息"""
        try:
            key = f"user:{user_id}"
            expiration = timedelta(hours=expiration_hours)
            return self.redis_client.setex(key, expiration, json.dumps(user_info, ensure_ascii=False))
        except Exception as e:
            logger.error(f"存储用户信息失败: {e}")
            return False

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            key = f"user:{user_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None

    def delete_user_info(self, user_id: str) -> bool:
        """删除用户信息"""
        try:
            key = f"user:{user_id}"
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"删除用户信息失败: {e}")
            return False

    def extend_user_session(self, user_id: str, expiration_hours: int = 6) -> bool:
        """延长用户会话时间"""
        try:
            expiration = timedelta(hours=expiration_hours)
            
            # 延长token时间
            token_key = f"token:{user_id}"
            if self.redis_client.exists(token_key):
                self.redis_client.expire(token_key, expiration)
            
            # 延长用户信息时间
            user_key = f"user:{user_id}"
            if self.redis_client.exists(user_key):
                self.redis_client.expire(user_key, expiration)
            
            return True
        except Exception as e:
            logger.error(f"延长用户会话失败: {e}")
            return False

    def check_token_valid(self, user_id: str) -> bool:
        """检查token是否有效"""
        try:
            key = f"token:{user_id}"
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"检查token有效性失败: {e}")
            return False


# 全局Redis客户端实例
redis_client = RedisClient()
