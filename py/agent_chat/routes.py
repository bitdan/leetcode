import logging

from agent_chat.service import AgentChatRequest, AgentChatResponse
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)


def create_router(container) -> APIRouter:
    router = APIRouter(tags=["agent-chat"])

    @router.post("/api/v1/agent/chat", response_model=AgentChatResponse)
    async def agent_chat(req: AgentChatRequest) -> AgentChatResponse:
        try:
            return container.agent_chat_service.chat(req)
        except Exception as exc:
            logger.exception("/api/v1/agent/chat failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router
