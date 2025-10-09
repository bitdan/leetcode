from pydantic import BaseModel
from typing import List, Optional, Literal
from enum import Enum


class GameStatus(str, Enum):
    """游戏状态枚举"""
    WAITING = "waiting"      # 等待玩家加入
    READY = "ready"         # 准备开始
    PLAYING = "playing"     # 游戏中
    FINISHED = "finished"   # 游戏结束


class PlayerColor(str, Enum):
    """玩家颜色枚举"""
    BLACK = "black"
    WHITE = "white"


class Player(BaseModel):
    """玩家信息"""
    user_id: str
    username: str
    color: Optional[PlayerColor] = None
    is_ready: bool = False
    is_online: bool = True


class Move(BaseModel):
    """棋子移动"""
    x: int
    y: int
    color: PlayerColor
    timestamp: float


class GameState(BaseModel):
    """游戏状态"""
    room_id: str
    status: GameStatus
    board: List[List[int]]  # 0: 空, 1: 黑棋, 2: 白棋
    current_player: PlayerColor
    winner: Optional[PlayerColor] = None
    last_move: Optional[Move] = None
    moves: List[Move] = []
    created_at: float
    updated_at: float


class RoomInfo(BaseModel):
    """房间信息"""
    room_id: str
    host: Player
    guest: Optional[Player] = None
    game_state: GameState
    spectator_count: int = 0


class CreateRoomRequest(BaseModel):
    """创建房间请求"""
    pass


class JoinRoomRequest(BaseModel):
    """加入房间请求"""
    room_id: str


class MakeMoveRequest(BaseModel):
    """下棋请求"""
    room_id: str
    x: int
    y: int


class GameEvent(BaseModel):
    """游戏事件"""
    type: Literal["player_joined", "player_left", "game_started", "move_made", "game_ended", "error"]
    room_id: str
    data: dict
    timestamp: float


