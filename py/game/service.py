import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional

from game.schemas import GameEvent, GameState, GameStatus, Move, Player, PlayerColor, RoomInfo

logger = logging.getLogger(__name__)


class GameService:
    def __init__(self):
        self.rooms: Dict[str, RoomInfo] = {}
        self.player_rooms: Dict[str, str] = {}
        self.event_subscribers: Dict[str, List[asyncio.Queue]] = {}

    def create_room(self, host: Player) -> str:
        room_id = str(uuid.uuid4())[:8]
        now = time.time()
        room = RoomInfo(
            room_id=room_id,
            host=host,
            game_state=GameState(
                room_id=room_id,
                status=GameStatus.WAITING,
                board=[[0 for _ in range(15)] for _ in range(15)],
                current_player=PlayerColor.BLACK,
                created_at=now,
                updated_at=now,
            ),
        )
        self.rooms[room_id] = room
        self.player_rooms[host.user_id] = room_id
        self.event_subscribers[room_id] = []
        logger.info("Room created: %s", room_id)
        return room_id

    def join_room(self, room_id: str, player: Player) -> bool:
        room = self.rooms.get(room_id)
        if room is None or room.guest is not None:
            return False
        player.color = PlayerColor.WHITE
        room.guest = player
        room.game_state.status = GameStatus.READY
        room.game_state.updated_at = time.time()
        self.player_rooms[player.user_id] = room_id
        self._schedule_event(
            room_id,
            GameEvent(type="player_joined", room_id=room_id, data={
                "player": {"user_id": player.user_id, "username": player.username, "color": player.color.value}},
                      timestamp=time.time()),
        )
        self._schedule_coroutine(self._auto_start_game(room_id))
        return True

    async def _auto_start_game(self, room_id: str) -> None:
        await asyncio.sleep(0.1)
        room = self.rooms.get(room_id)
        if not room or not room.host or not room.guest or room.game_state.status != GameStatus.READY:
            return
        room.game_state.status = GameStatus.PLAYING
        room.game_state.updated_at = time.time()
        await self._broadcast_event(
            room_id,
            GameEvent(
                type="game_started",
                room_id=room_id,
                data={
                    "current_player": room.game_state.current_player.value,
                    "host_color": room.host.color.value if room.host.color else None,
                    "guest_color": room.guest.color.value if room.guest.color else None,
                },
                timestamp=time.time(),
            ),
        )

    def leave_room(self, user_id: str) -> bool:
        room_id = self.player_rooms.get(user_id)
        room = self.rooms.get(room_id) if room_id else None
        if not room_id or room is None:
            return False
        self._schedule_event(room_id, GameEvent(type="player_left", room_id=room_id, data={"user_id": user_id},
                                                timestamp=time.time()))
        if room.host.user_id == user_id:
            self._delete_room(room_id)
        else:
            room.guest = None
            room.game_state.status = GameStatus.WAITING
            room.game_state.updated_at = time.time()
            self.player_rooms.pop(user_id, None)
        return True

    def make_move(self, room_id: str, user_id: str, x: int, y: int) -> bool:
        room = self.rooms.get(room_id)
        if room is None:
            return False
        state = room.game_state
        if state.status != GameStatus.PLAYING or not (0 <= x < 15 and 0 <= y < 15) or state.board[y][x] != 0:
            return False
        player_color = self._resolve_player_color(room, user_id)
        if player_color is None or state.current_player != player_color:
            return False
        color_value = 1 if player_color == PlayerColor.BLACK else 2
        state.board[y][x] = color_value
        move = Move(x=x, y=y, color=player_color, timestamp=time.time())
        state.moves.append(move)
        state.last_move = move
        state.updated_at = time.time()
        move_payload = move.model_dump(mode="json") if hasattr(move, "model_dump") else move.dict()
        if self._check_winner(state.board, x, y, color_value):
            state.winner = player_color
            state.status = GameStatus.FINISHED
            self._schedule_event(room_id, GameEvent(type="game_ended", room_id=room_id,
                                                    data={"winner": player_color.value, "move": move_payload},
                                                    timestamp=time.time()))
        else:
            state.current_player = PlayerColor.WHITE if state.current_player == PlayerColor.BLACK else PlayerColor.BLACK
            self._schedule_event(room_id, GameEvent(type="move_made", room_id=room_id, data={"move": move_payload,
                                                                                             "current_player": state.current_player.value,
                                                                                             "board": state.board},
                                                    timestamp=time.time()))
        return True

    def start_game(self, room_id: str, user_id: str) -> bool:
        room = self.rooms.get(room_id)
        if room is None or room.host.user_id != user_id or room.guest is None:
            return False
        room.game_state.status = GameStatus.PLAYING
        room.game_state.updated_at = time.time()
        self._schedule_event(
            room_id,
            GameEvent(
                type="game_started",
                room_id=room_id,
                data={
                    "current_player": room.game_state.current_player.value,
                    "host_color": room.host.color.value if room.host.color else None,
                    "guest_color": room.guest.color.value if room.guest.color else None,
                },
                timestamp=time.time(),
            ),
        )
        return True

    def restart_game(self, room_id: str, user_id: str) -> bool:
        room = self.rooms.get(room_id)
        if room is None or room.host.user_id != user_id:
            return False
        room.game_state.board = [[0 for _ in range(15)] for _ in range(15)]
        room.game_state.current_player = PlayerColor.BLACK
        room.game_state.winner = None
        room.game_state.last_move = None
        room.game_state.moves = []
        room.game_state.status = GameStatus.READY
        room.game_state.updated_at = time.time()
        self._schedule_event(room_id, GameEvent(type="game_started", room_id=room_id,
                                                data={"current_player": room.game_state.current_player.value,
                                                      "board": room.game_state.board}, timestamp=time.time()))
        return True

    def get_room_info(self, room_id: str) -> Optional[RoomInfo]:
        return self.rooms.get(room_id)

    def get_player_room(self, user_id: str) -> Optional[str]:
        return self.player_rooms.get(user_id)

    def add_event_subscriber(self, room_id: str, queue: asyncio.Queue) -> None:
        self.event_subscribers.setdefault(room_id, []).append(queue)

    def remove_event_subscriber(self, room_id: str, queue: asyncio.Queue) -> None:
        subscribers = self.event_subscribers.get(room_id, [])
        if queue in subscribers:
            subscribers.remove(queue)

    async def _broadcast_event(self, room_id: str, event: GameEvent) -> None:
        for queue in list(self.event_subscribers.get(room_id, [])):
            try:
                await queue.put(event)
            except Exception:
                logger.exception("Failed to broadcast game event")
                self.remove_event_subscriber(room_id, queue)

    def _schedule_event(self, room_id: str, event: GameEvent) -> None:
        self._schedule_coroutine(self._broadcast_event(room_id, event))

    def _schedule_coroutine(self, coroutine) -> None:
        try:
            asyncio.get_running_loop().create_task(coroutine)
        except RuntimeError:
            asyncio.run(coroutine)

    def _delete_room(self, room_id: str) -> None:
        room = self.rooms.pop(room_id, None)
        if room is None:
            return
        self.player_rooms.pop(room.host.user_id, None)
        if room.guest:
            self.player_rooms.pop(room.guest.user_id, None)
        self.event_subscribers.pop(room_id, None)

    def _resolve_player_color(self, room: RoomInfo, user_id: str) -> Optional[PlayerColor]:
        if room.host.user_id == user_id:
            return room.host.color
        if room.guest and room.guest.user_id == user_id:
            return room.guest.color
        return None

    def _check_winner(self, board: List[List[int]], x: int, y: int, color: int) -> bool:
        for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            count = 1
            for step in range(1, 5):
                next_x, next_y = x + dx * step, y + dy * step
                if next_x < 0 or next_x >= 15 or next_y < 0 or next_y >= 15 or board[next_y][next_x] != color:
                    break
                count += 1
            for step in range(1, 5):
                next_x, next_y = x - dx * step, y - dy * step
                if next_x < 0 or next_x >= 15 or next_y < 0 or next_y >= 15 or board[next_y][next_x] != color:
                    break
                count += 1
            if count >= 5:
                return True
        return False


game_service = GameService()

__all__ = ["GameService", "game_service"]
