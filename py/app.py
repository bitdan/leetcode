from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_chat.routes import create_router as create_agent_chat_router
from agent_eval.routes import create_router as create_agent_eval_router
from auth.routes import create_router as create_auth_router
from bootstrap import build_container
from chat.routes import create_router as create_chat_router
from core.logging import configure_logging, register_request_logging
from core.settings import get_settings
from game.routes import create_router as create_game_router
from market_review.routes import create_router as create_market_review_router
from mcp_server.server import create_router as create_mcp_router
from post.routes import create_router as create_post_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    container = build_container(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await container.chat_service.start()
        try:
            yield
        finally:
            await container.chat_service.stop()
            container.user_service.close()
            container.post_service.close()
            container.agent_eval_service.store.close()

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
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
    app.include_router(create_chat_router(container))
    app.include_router(create_post_router(container))
    app.include_router(create_market_review_router(container))
    app.include_router(create_agent_chat_router(container))
    app.include_router(create_agent_eval_router(container))
    app.include_router(create_mcp_router(container))

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
