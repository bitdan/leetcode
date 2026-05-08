import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class RedisSettings:
    host: str
    port: int
    database: int
    password: str
    decode_responses: bool = True


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    log_level: str
    cors_origins: List[str]
    openai_api_key: str
    openai_api_base: str
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expiration_hours: int
    auth_cookie_secure: bool
    redis: RedisSettings
    use_redis_sessions: bool
    use_redis_user_store: bool


def _split_csv(value: str, default: List[str]) -> List[str]:
    if not value.strip():
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    cors_default = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://tool.linger.host",
        "https://tool.linger.host",
    ]
    return Settings(
        app_name=os.getenv("APP_NAME", "Tool Hub API"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS", ""), cors_default),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_api_base=os.getenv("OPENAI_API_BASE", ""),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-env"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", "6")),
        auth_cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        redis=RedisSettings(
            host=os.getenv("REDIS_HOST", "43.156.83.246"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            database=int(os.getenv("REDIS_DATABASE", "14")),
            password=os.getenv("REDIS_PASSWORD", "dudu0.0@"),
            decode_responses=os.getenv("REDIS_DECODE_RESPONSES", "true").lower() == "true",
        ),
        use_redis_sessions=os.getenv("USE_REDIS_SESSIONS", "true").lower() == "true",
        use_redis_user_store=os.getenv("USE_REDIS_USER_STORE", "true").lower() == "true",
    )


def legacy_redis_config() -> Dict[str, object]:
    settings = get_settings()
    return {
        "host": settings.redis.host,
        "port": settings.redis.port,
        "database": settings.redis.database,
        "password": settings.redis.password,
        "decode_responses": settings.redis.decode_responses,
    }
