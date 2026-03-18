import asyncio
import json
import logging

from auth.schemas import ApiResponse, UserInfo
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from game.schemas import JoinRoomRequest, MakeMoveRequest, Player, PlayerColor

logger = logging.getLogger(__name__)


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/game", tags=["五子棋游戏"])
    game_service = container.game_service
    auth_router = getattr(container, "_auth_router", None)

    async def get_current_user_proxy() -> UserInfo:
        raise RuntimeError("Auth dependency not attached")

    get_current_user = getattr(auth_router, "get_current_user", get_current_user_proxy)

    @router.post("/create-room", response_model=ApiResponse)
    async def create_room(current_user: UserInfo = Depends(get_current_user)):
        if game_service.get_player_room(current_user.user.user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="您已在其他房间中，请先离开")
        room_id = game_service.create_room(
            Player(user_id=current_user.user.user_id, username=current_user.user.username, color=PlayerColor.BLACK,
                   is_ready=True, is_online=True)
        )
        return ApiResponse(code=200, msg="房间创建成功", data=room_id)

    @router.post("/join-room", response_model=ApiResponse)
    async def join_room(request: JoinRoomRequest, current_user: UserInfo = Depends(get_current_user)):
        if game_service.get_player_room(current_user.user.user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="您已在其他房间中，请先离开")
        player = Player(user_id=current_user.user.user_id, username=current_user.user.username, is_ready=True,
                        is_online=True)
        if not game_service.join_room(request.room_id, player):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="加入房间失败，房间不存在或已满")
        return ApiResponse(code=200, msg="加入房间成功")

    @router.post("/leave-room", response_model=ApiResponse)
    async def leave_room(current_user: UserInfo = Depends(get_current_user)):
        if not game_service.leave_room(current_user.user.user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="您不在任何房间中")
        return ApiResponse(code=200, msg="离开房间成功")

    @router.post("/make-move", response_model=ApiResponse)
    async def make_move(request: MakeMoveRequest, current_user: UserInfo = Depends(get_current_user)):
        if game_service.get_player_room(current_user.user.user_id) != request.room_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="您不在该房间中")
        if not game_service.make_move(request.room_id, current_user.user.user_id, request.x, request.y):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="下棋失败，请检查位置和游戏状态")
        return ApiResponse(code=200, msg="下棋成功")

    @router.post("/start-game", response_model=ApiResponse)
    async def start_game(room_id: str, current_user: UserInfo = Depends(get_current_user)):
        if not game_service.start_game(room_id, current_user.user.user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始游戏失败，请检查权限和房间状态")
        return ApiResponse(code=200, msg="游戏开始")

    @router.post("/restart-game", response_model=ApiResponse)
    async def restart_game(room_id: str, current_user: UserInfo = Depends(get_current_user)):
        if not game_service.restart_game(room_id, current_user.user.user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="重新开始游戏失败，请检查权限")
        return ApiResponse(code=200, msg="游戏重新开始")

    @router.get("/room/{room_id}", response_model=ApiResponse)
    async def get_room_info(room_id: str, current_user: UserInfo = Depends(get_current_user)):
        room_info = game_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")
        data = room_info.model_dump(mode="json") if hasattr(room_info, "model_dump") else room_info.dict()
        return ApiResponse(code=200, msg="获取房间信息成功", data=data)

    @router.get("/events/{room_id}")
    async def stream_events(room_id: str, access_token: str = ""):
        current_user = container.user_service.validate_user_session(access_token)
        if not access_token or not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证失败，请重新登录")

        async def event_generator():
            queue = asyncio.Queue()
            if game_service.get_player_room(current_user.user.user_id) != room_id:
                yield f"data: {json.dumps({'type': 'error', 'message': '您不在该房间中'})}\n\n"
                return
            try:
                game_service.add_event_subscriber(room_id, queue)
                yield f"data: {json.dumps({'type': 'connected', 'room_id': room_id})}\n\n"
                room_info = game_service.get_room_info(room_id)
                if room_info:
                    payload = room_info.model_dump(mode="json") if hasattr(room_info,
                                                                           "model_dump") else room_info.dict()
                    yield f"data: {json.dumps({'type': 'room_state', 'data': payload})}\n\n"
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else event.dict()
                        yield f"data: {json.dumps(payload)}\n\n"
                    except asyncio.TimeoutError:
                        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            finally:
                game_service.remove_event_subscriber(room_id, queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "Access-Control-Allow-Origin": "*",
                     "Access-Control-Allow-Headers": "*"},
        )

    return router
