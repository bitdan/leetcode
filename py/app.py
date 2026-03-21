from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_chat.routes import create_router as create_agent_chat_router
from auth.routes import create_router as create_auth_router
from bootstrap import build_container
from core.logging import configure_logging, register_request_logging
from core.settings import get_settings
from game.routes import create_router as create_game_router
from mcp_server.server import create_router as create_mcp_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    container = build_container(settings)

    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_request_logging(app)

    auth_router = create_auth_router(container)
    container._auth_router = auth_router
    app.include_router(auth_router)
    app.include_router(create_game_router(container))
    app.include_router(create_agent_chat_router(container))
    app.include_router(create_mcp_router(container))

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
