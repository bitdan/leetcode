import logging

from agent_chat.service import AgentChatRequest, AgentChatResponse
from auth.routes import AUTH_COOKIE_NAME
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)


def create_router(container) -> APIRouter:
    router = APIRouter(tags=["agent-chat"])

    def get_optional_user(request: Request):
        authorization = request.headers.get("Authorization", "")
        token = ""
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        token = token or request.cookies.get(AUTH_COOKIE_NAME, "")
        return container.user_service.validate_user_session(token) if token else None

    @router.post("/api/v1/agent/chat", response_model=AgentChatResponse)
    async def agent_chat(req: AgentChatRequest, request: Request) -> AgentChatResponse:
        try:
            return container.agent_eval_service.run_traced_chat(
                req,
                container.agent_chat_service.chat,
                current_user=get_optional_user(request),
            )
        except Exception as exc:
            logger.exception("/api/v1/agent/chat failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router
