import logging
import json

from agent_chat.service import AgentChatError, AgentChatRequest, AgentChatResponse
from agent_eval.store import AgentEvalStoreUnavailable
from auth.routes import AUTH_COOKIE_NAME
from auth.schemas import ApiResponse
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentToolInvokeRequest(BaseModel):
    arguments: dict = Field(default_factory=dict)
    run_id: str | None = None
    session_id: str | None = None
    confirmed: bool = False


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
        except AgentChatError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": exc.error_code,
                    "message": str(exc),
                    "retryable": exc.retryable,
                },
            ) from exc
        except Exception as exc:
            logger.exception("/api/v1/agent/chat failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error_code": "agent_internal_error", "message": "Agent 执行失败", "retryable": True},
            ) from exc

    @router.post("/api/v1/agent/chat/stream")
    async def agent_chat_stream(req: AgentChatRequest, request: Request) -> StreamingResponse:
        current_user = get_optional_user(request)

        def event_generator():
            try:
                for item in container.agent_chat_service.stream(req):
                    if item.get("event") == "final":
                        response = AgentChatResponse(**item["data"])
                        response = container.agent_eval_service.record_chat_response(
                            req,
                            response,
                            current_user=current_user,
                        )
                        item = {"event": "final", "data": _dump_model(response)}
                    yield _sse(item["event"], item["data"])
            except Exception:
                logger.exception("/api/v1/agent/chat/stream failed")
                yield _sse(
                    "error",
                    {
                        "error_code": "agent_stream_error",
                        "message": "Agent 流式执行失败",
                        "retryable": True,
                    },
                )

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @router.get("/api/v1/agent/runs/{run_id}", response_model=ApiResponse)
    async def get_run(run_id: str) -> ApiResponse:
        try:
            return ApiResponse(code=200, msg="获取 Agent run 成功", data=container.agent_eval_service.get_run_detail(run_id))
        except AgentEvalStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Get agent run failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取 Agent run 失败") from exc

    @router.get("/api/v1/agent/sessions/{session_id}/runs", response_model=ApiResponse)
    async def list_session_runs(session_id: str, limit: int = Query(default=50, ge=1, le=200)) -> ApiResponse:
        try:
            return ApiResponse(
                code=200,
                msg="获取 Agent session runs 成功",
                data=container.agent_eval_service.list_session_runs(session_id, limit),
            )
        except AgentEvalStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("List agent session runs failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取会话任务失败") from exc

    @router.post("/api/v1/agent/runs/{run_id}/retry", response_model=ApiResponse)
    async def retry_run(run_id: str, request: Request) -> ApiResponse:
        try:
            detail = container.agent_eval_service.get_run_detail(run_id)
            retry_req = AgentChatRequest(
                message=detail["input_text"],
                session_id=detail.get("session_id"),
                history=[],
                route="auto",
            )
            response = container.agent_eval_service.run_traced_chat(
                retry_req,
                container.agent_chat_service.chat,
                current_user=get_optional_user(request),
            )
            return ApiResponse(code=200, msg="Agent run 已重试", data=_dump_model(response))
        except AgentEvalStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Retry agent run failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="重试 Agent run 失败") from exc

    @router.post("/api/v1/agent/runs/{run_id}/cancel", response_model=ApiResponse)
    async def cancel_run(run_id: str) -> ApiResponse:
        try:
            return ApiResponse(code=200, msg="Agent run 取消状态已更新", data=container.agent_eval_service.cancel_run(run_id))
        except AgentEvalStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Cancel agent run failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="取消 Agent run 失败") from exc

    @router.get("/api/v1/agent/tools", response_model=ApiResponse)
    async def list_tools() -> ApiResponse:
        return ApiResponse(code=200, msg="获取 Agent tools 成功", data=container.agent_chat_service.list_tools())

    @router.get("/api/v1/agent/skills", response_model=ApiResponse)
    async def list_skills() -> ApiResponse:
        return ApiResponse(code=200, msg="获取 Agent skills 成功", data=container.agent_chat_service.list_skills())

    @router.post("/api/v1/agent/tools/{tool_name}/invoke", response_model=ApiResponse)
    async def invoke_tool(tool_name: str, payload: AgentToolInvokeRequest) -> ApiResponse:
        try:
            result = container.agent_chat_service.invoke_tool(
                tool_name,
                payload.arguments,
                run_id=payload.run_id,
                session_id=payload.session_id,
                confirmed=payload.confirmed,
            )
            return ApiResponse(code=200, msg="Agent tool 调用完成", data=result)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"工具不存在: {tool_name}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Invoke agent tool failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent tool 调用失败") from exc

    @router.get("/api/v1/agent/confirmations", response_model=ApiResponse)
    async def list_confirmations(session_id: str | None = None) -> ApiResponse:
        return ApiResponse(
            code=200,
            msg="获取待确认操作成功",
            data=container.agent_chat_service.list_confirmations(session_id),
        )

    @router.get("/api/v1/agent/confirmations/{confirmation_id}", response_model=ApiResponse)
    async def get_confirmation(confirmation_id: str) -> ApiResponse:
        try:
            return ApiResponse(
                code=200,
                msg="获取待确认操作成功",
                data=container.agent_chat_service.get_confirmation(confirmation_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/api/v1/agent/confirmations/{confirmation_id}/approve", response_model=ApiResponse)
    async def approve_confirmation(confirmation_id: str) -> ApiResponse:
        try:
            return ApiResponse(
                code=200,
                msg="操作已确认并执行",
                data=container.agent_chat_service.approve_confirmation(confirmation_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Approve agent confirmation failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="确认操作执行失败") from exc

    @router.post("/api/v1/agent/confirmations/{confirmation_id}/reject", response_model=ApiResponse)
    async def reject_confirmation(confirmation_id: str) -> ApiResponse:
        try:
            return ApiResponse(
                code=200,
                msg="操作已拒绝",
                data=container.agent_chat_service.reject_confirmation(confirmation_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return router


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _dump_model(model):
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()
