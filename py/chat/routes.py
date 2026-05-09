import logging

from auth.routes import AUTH_COOKIE_NAME
from auth.schemas import ApiResponse, UserInfo
from chat.schemas import ChatSendPayload
from chat.service import dump_model
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/chat", tags=["实时聊天"])
    chat_service = container.chat_service
    auth_router = getattr(container, "_auth_router", None)

    async def get_current_user_proxy() -> UserInfo:
        raise RuntimeError("Auth dependency not attached")

    get_current_user = getattr(auth_router, "get_current_user", get_current_user_proxy)

    @router.get("/history", response_model=ApiResponse)
    async def get_history(
            channel: str = Query(default="general", min_length=1, max_length=64),
            limit: int = Query(default=50, ge=1, le=100),
            current_user: UserInfo = Depends(get_current_user),
    ):
        messages = [dump_model(message) for message in chat_service.get_history(channel, limit)]
        return ApiResponse(code=200, msg="获取聊天记录成功", data=messages)

    @router.websocket("/ws")
    async def chat_ws(
            websocket: WebSocket,
            channel: str = Query(default="general", min_length=1, max_length=64),
            access_token: str = Query(default=""),
    ):
        token = access_token or websocket.cookies.get(AUTH_COOKIE_NAME, "")
        current_user = container.user_service.validate_user_session(token)
        if not token or not current_user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        chat_service.add_connection(channel, websocket)
        await websocket.send_json({
            "type": "connected",
            "channel": channel,
            "user": dump_model(current_user),
        })

        try:
            while True:
                payload = await websocket.receive_json()
                try:
                    message = ChatSendPayload.model_validate(payload) if hasattr(ChatSendPayload,
                                                                                 "model_validate") else ChatSendPayload.parse_obj(
                        payload)
                except Exception:
                    await websocket.send_json({"type": "error", "message": "消息格式错误"})
                    continue

                content = message.content.strip()
                if not content:
                    await websocket.send_json({"type": "error", "message": "消息不能为空"})
                    continue

                await chat_service.publish_user_message(channel, current_user, content[:500])
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("Chat websocket failed")
        finally:
            chat_service.remove_connection(channel, websocket)

    return router
