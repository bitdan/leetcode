import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from project_agent.schemas import (
    ProjectAgentConfirmationRequest,
    ProjectAgentConfirmationResponse,
    ProjectAgentEvalRequest,
    ProjectAgentEvalResponse,
    ProjectAgentIndexRequest,
    ProjectAgentIndexResponse,
    ProjectAgentRequest,
    ProjectAgentResponse,
)

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

    @router.post("/chat/stream")
    async def chat_stream(req: ProjectAgentRequest) -> StreamingResponse:
        try:
            return StreamingResponse(container.project_agent_service.stream_chat(req), media_type="text/event-stream")
        except Exception as exc:
            logger.exception("/api/v1/project-agent/chat/stream failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/index", response_model=ProjectAgentIndexResponse)
    async def index(req: ProjectAgentIndexRequest) -> ProjectAgentIndexResponse:
        try:
            return container.project_agent_service.build_index(max_files=req.max_files, force=req.force)
        except Exception as exc:
            logger.exception("/api/v1/project-agent/index failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/confirm", response_model=ProjectAgentConfirmationResponse)
    async def confirm(req: ProjectAgentConfirmationRequest) -> ProjectAgentConfirmationResponse:
        try:
            return container.project_agent_service.confirm(req.confirmation_id, req.approved)
        except Exception as exc:
            logger.exception("/api/v1/project-agent/confirm failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/eval", response_model=ProjectAgentEvalResponse)
    async def eval_cases(req: ProjectAgentEvalRequest) -> ProjectAgentEvalResponse:
        try:
            return container.project_agent_service.run_eval_cases(req)
        except Exception as exc:
            logger.exception("/api/v1/project-agent/eval failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router
