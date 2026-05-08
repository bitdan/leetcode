from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class GameStatus(str, Enum):
    WAITING = "waiting"
    READY = "ready"
    PLAYING = "playing"
    FINISHED = "finished"


class PlayerColor(str, Enum):
    BLACK = "black"
    WHITE = "white"


class Player(BaseModel):
    user_id: str
    username: str
    color: Optional[PlayerColor] = None
    is_ready: bool = False
    is_online: bool = True


class Move(BaseModel):
    x: int
    y: int
    color: PlayerColor
    timestamp: float


class GameState(BaseModel):
    room_id: str
    status: GameStatus
    board: List[List[int]]
    current_player: PlayerColor
    winner: Optional[PlayerColor] = None
    last_move: Optional[Move] = None
    moves: List[Move] = Field(default_factory=list)
    created_at: float
    updated_at: float


class RoomInfo(BaseModel):
    room_id: str
    host: Player
    guest: Optional[Player] = None
    game_state: GameState
    spectator_count: int = 0


class CreateRoomRequest(BaseModel):
    pass


class JoinRoomRequest(BaseModel):
    room_id: str


class MakeMoveRequest(BaseModel):
    room_id: str
    x: int
    y: int


class GameEvent(BaseModel):
    type: Literal[
        "connected",
        "room_state",
        "player_joined",
        "player_left",
        "game_started",
        "move_made",
        "game_ended",
        "error",
        "heartbeat",
    ]
    room_id: str
    data: Dict[str, object]
    timestamp: float
