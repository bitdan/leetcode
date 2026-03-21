from auth.store import MemorySessionStore, RedisSessionStore
from core.settings import get_settings

_settings = get_settings()

try:
    redis_client = RedisSessionStore(
        host=_settings.redis.host,
        port=_settings.redis.port,
        database=_settings.redis.database,
        password=_settings.redis.password,
        decode_responses=_settings.redis.decode_responses,
        expiration_hours=_settings.jwt_expiration_hours,
    )
except Exception:
    redis_client = MemorySessionStore()

__all__ = ["redis_client", "RedisSessionStore", "MemorySessionStore"]
