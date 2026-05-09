import logging
from dataclasses import dataclass

from agent_chat.service import AgentChatService
from auth.security import JWTHandler
from auth.service import UserService
from auth.store import MemorySessionStore, RedisSessionStore, create_user_repository
from auth.totp_service import TotpService
from auth.totp_store import create_totp_store
from chat.service import ChatService, RedisChatService
from core.settings import Settings
from game.service import GameService
from mcp_server.registry import create_default_tool_registry

logger = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    jwt_handler: JWTHandler
    user_service: UserService
    totp_service: TotpService
    game_service: GameService
    chat_service: ChatService
    agent_chat_service: AgentChatService
    mcp_tool_registry: dict


def build_container(settings: Settings) -> Container:
    jwt_handler = JWTHandler(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expiration_hours=settings.jwt_expiration_hours,
    )

    session_store = MemorySessionStore()
    if settings.use_redis_sessions:
        try:
            session_store = RedisSessionStore(
                host=settings.redis.host,
                port=settings.redis.port,
                database=settings.redis.database,
                password=settings.redis.password,
                decode_responses=settings.redis.decode_responses,
                expiration_hours=settings.jwt_expiration_hours,
            )
        except Exception:
            logger.warning("Redis unavailable. Falling back to in-memory session store.", exc_info=True)

    user_repository = create_user_repository(settings, jwt_handler)
    user_service = UserService(
        user_repository=user_repository,
        session_store=session_store,
        jwt_handler=jwt_handler,
        session_ttl_hours=settings.jwt_expiration_hours,
    )
    totp_service = TotpService(
        totp_store=create_totp_store(settings),
        issuer_name=settings.app_name,
    )
    return Container(
        settings=settings,
        jwt_handler=jwt_handler,
        user_service=user_service,
        totp_service=totp_service,
        game_service=GameService(),
        chat_service=create_chat_service(settings),
        agent_chat_service=AgentChatService(),
        mcp_tool_registry=create_default_tool_registry(),
    )


def create_chat_service(settings: Settings) -> ChatService:
    if settings.use_redis_chat:
        try:
            return RedisChatService(
                host=settings.redis.host,
                port=settings.redis.port,
                database=settings.redis.database,
                password=settings.redis.password,
                decode_responses=settings.redis.decode_responses,
                history_limit=settings.chat_history_limit,
                history_ttl_seconds=settings.chat_history_ttl_seconds,
            )
        except Exception:
            logger.warning("Redis unavailable. Falling back to in-memory chat service.", exc_info=True)
    return ChatService(history_limit=settings.chat_history_limit)
