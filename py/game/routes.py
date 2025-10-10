import asyncio
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.routes import get_current_user
from auth.models import UserInfo, ApiResponse
from game.models import (
    CreateRoomRequest, JoinRoomRequest, MakeMoveRequest, 
    Player, PlayerColor, GameEvent
)
from game.service import game_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/game", tags=["五子棋游戏"])
security = HTTPBearer()


@router.post("/create-room", response_model=ApiResponse)
async def create_room(
    current_user: UserInfo = Depends(get_current_user)
):
    """创建游戏房间"""
    try:
        # 检查用户是否已在其他房间
        existing_room = game_service.get_player_room(current_user.user.user_id)
        if existing_room:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已在其他房间中，请先离开"
            )
        
        # 创建房主玩家
        host = Player(
            user_id=current_user.user.user_id,
            username=current_user.user.username,
            color=PlayerColor.BLACK,  # 房主默认为黑棋
            is_ready=True,
            is_online=True
        )
        
        # 创建房间
        room_id = game_service.create_room(host)
        
        return ApiResponse(
            code=200,
            msg="房间创建成功",
            data=room_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建房间失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建房间失败，请稍后重试"
        )


@router.post("/join-room", response_model=ApiResponse)
async def join_room(
    request: JoinRoomRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """加入游戏房间"""
    try:
        # 检查用户是否已在其他房间
        existing_room = game_service.get_player_room(current_user.user.user_id)
        if existing_room:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已在其他房间中，请先离开"
            )
        
        # 创建玩家
        player = Player(
            user_id=current_user.user.user_id,
            username=current_user.user.username,
            is_ready=True,
            is_online=True
        )
        
        # 加入房间
        success = game_service.join_room(request.room_id, player)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="加入房间失败，房间不存在或已满"
            )
        
        return ApiResponse(
            code=200,
            msg="加入房间成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"加入房间失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="加入房间失败，请稍后重试"
        )


@router.post("/leave-room", response_model=ApiResponse)
async def leave_room(
    current_user: UserInfo = Depends(get_current_user)
):
    """离开游戏房间"""
    try:
        success = game_service.leave_room(current_user.user.user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您不在任何房间中"
            )
        
        return ApiResponse(
            code=200,
            msg="离开房间成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"离开房间失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="离开房间失败，请稍后重试"
        )


@router.post("/make-move", response_model=ApiResponse)
async def make_move(
    request: MakeMoveRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """下棋"""
    try:
        # 检查用户是否在指定房间
        user_room = game_service.get_player_room(current_user.user.user_id)
        if user_room != request.room_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您不在该房间中"
            )
        
        # 执行移动
        success = game_service.make_move(
            request.room_id, 
            current_user.user.user_id, 
            request.x, 
            request.y
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="下棋失败，请检查位置和游戏状态"
            )
        
        return ApiResponse(
            code=200,
            msg="下棋成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下棋失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="下棋失败，请稍后重试"
        )


@router.post("/start-game", response_model=ApiResponse)
async def start_game(
    room_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """开始游戏"""
    try:
        success = game_service.start_game(room_id, current_user.user.user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始游戏失败，请检查权限和房间状态"
            )
        
        return ApiResponse(
            code=200,
            msg="游戏开始"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"开始游戏失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="开始游戏失败，请稍后重试"
        )


@router.post("/restart-game", response_model=ApiResponse)
async def restart_game(
    room_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """重新开始游戏"""
    try:
        success = game_service.restart_game(room_id, current_user.user.user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="重新开始游戏失败，请检查权限"
            )
        
        return ApiResponse(
            code=200,
            msg="游戏重新开始"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新开始游戏失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新开始游戏失败，请稍后重试"
        )


@router.get("/room/{room_id}")
async def get_room_info(
    room_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """获取房间信息"""
    try:
        room_info = game_service.get_room_info(room_id)
        if not room_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="房间不存在"
            )
        
        # 构建响应数据
        data = {
            "room_id": room_info.room_id,
            "host": {
                "user_id": room_info.host.user_id,
                "username": room_info.host.username,
                "color": room_info.host.color.value if room_info.host.color else None,
                "is_ready": room_info.host.is_ready,
                "is_online": room_info.host.is_online
            },
            "guest": None,
            "game_state": {
                "status": room_info.game_state.status.value,
                "board": room_info.game_state.board,
                "current_player": room_info.game_state.current_player.value,
                "winner": room_info.game_state.winner.value if room_info.game_state.winner else None,
                "last_move": {
                    "x": room_info.game_state.last_move.x,
                    "y": room_info.game_state.last_move.y,
                    "color": room_info.game_state.last_move.color.value
                } if room_info.game_state.last_move else None,
                "moves_count": len(room_info.game_state.moves),
                "created_at": room_info.game_state.created_at,
                "updated_at": room_info.game_state.updated_at
            },
            "spectator_count": room_info.spectator_count
        }
        
        if room_info.guest:
            data["guest"] = {
                "user_id": room_info.guest.user_id,
                "username": room_info.guest.username,
                "color": room_info.guest.color.value if room_info.guest.color else None,
                "is_ready": room_info.guest.is_ready,
                "is_online": room_info.guest.is_online
            }
        
        return ApiResponse(
            code=200,
            msg="获取房间信息成功",
            data=data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取房间信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取房间信息失败，请稍后重试"
        )


@router.get("/events/{room_id}")
async def stream_events(
    room_id: str,
    access_token: str = None
):
    """SSE事件流"""
    
    # 手动验证token，因为SSE不支持标准的依赖注入
    try:
        from auth.user_service import user_service
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证token"
            )
        user_info = user_service.validate_user_session(access_token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证失败，请重新登录"
            )
        current_user = user_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败，请重新登录"
        )
    
    async def event_generator():
        # 创建事件队列
        queue = asyncio.Queue()
        
        # 检查用户是否在房间中
        user_room = game_service.get_player_room(current_user.user.user_id)
        if user_room != room_id:
            yield f"data: {json.dumps({'type': 'error', 'message': '您不在该房间中'})}\n\n"
            return
        
        try:
            # 添加订阅者
            game_service.add_event_subscriber(room_id, queue)
            
            # 发送连接成功事件
            yield f"data: {json.dumps({'type': 'connected', 'room_id': room_id})}\n\n"
            
            # 发送当前房间状态
            room_info = game_service.get_room_info(room_id)
            if room_info:
                yield f"data: {json.dumps({'type': 'room_state', 'data': room_info.dict()})}\n\n"
            
            # 监听事件
            while True:
                try:
                    # 等待事件，设置超时以保持连接活跃
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event.dict())}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
                except Exception as e:
                    logger.error(f"事件流错误: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    break
                    
        except Exception as e:
            logger.error(f"SSE连接错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # 移除订阅者
            game_service.remove_event_subscriber(room_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )
