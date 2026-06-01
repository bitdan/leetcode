import logging

from fastapi import APIRouter, HTTPException

from project_agent.schemas import ProjectAgentRequest, ProjectAgentResponse

logger = logging.getLogger(__name__)


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/project-agent", tags=["project-agent"])

    @router.post("/chat", response_model=ProjectAgentResponse)
    async def chat(req: ProjectAgentRequest) -> ProjectAgentResponse:
        try:
            return container.project_agent_service.chat(req)
        except Exception as exc:
            logger.exception("/api/v1/project-agent/chat failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router
