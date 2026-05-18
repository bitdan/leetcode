import logging

from agent_eval.schemas import AgentEvalSummary, AgentFeedbackRequest
from agent_eval.store import AgentEvalStoreUnavailable
from auth.routes import AUTH_COOKIE_NAME
from auth.schemas import ApiResponse
from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/agent/evaluations", tags=["agent-evaluations"])
    eval_service = container.agent_eval_service

    def get_optional_user(request: Request):
        authorization = request.headers.get("Authorization", "")
        token = ""
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        token = token or request.cookies.get(AUTH_COOKIE_NAME, "")
        return container.user_service.validate_user_session(token) if token else None

    @router.post("/feedback", response_model=ApiResponse)
    async def create_feedback(payload: AgentFeedbackRequest, request: Request) -> ApiResponse:
        try:
            feedback_id = eval_service.create_feedback(payload, get_optional_user(request))
            return ApiResponse(code=200, msg="反馈已记录", data={"id": feedback_id})
        except AgentEvalStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except Exception as exc:
            logger.exception("Create agent feedback failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="反馈记录失败") from exc

    @router.get("/summary", response_model=ApiResponse)
    async def summary() -> ApiResponse:
        data: AgentEvalSummary = eval_service.summarize()
        return ApiResponse(
            code=200,
            msg="获取 Agent 评测指标成功",
            data=data.model_dump() if hasattr(data, "model_dump") else data.dict(),
        )

    return router
