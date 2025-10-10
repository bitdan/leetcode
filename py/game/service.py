import asyncio
import time
import uuid
import logging
from typing import Dict, Optional, List
from fastapi import HTTPException
from game.models import (
    RoomInfo, GameState, GameStatus, Player, PlayerColor, 
    Move, GameEvent, RoomInfo
)

logger = logging.getLogger(__name__)


class GameService:
    """游戏服务类"""
    
    def __init__(self):
        self.rooms: Dict[str, RoomInfo] = {}  # 房间存储
        self.player_rooms: Dict[str, str] = {}  # 玩家ID -> 房间ID映射
        self.event_subscribers: Dict[str, List[asyncio.Queue]] = {}  # SSE订阅者
    
    def create_room(self, host: Player) -> str:
        """创建房间"""
        room_id = str(uuid.uuid4())[:8]  # 生成8位房间ID
        
        # 初始化游戏状态
        game_state = GameState(
            room_id=room_id,
            status=GameStatus.WAITING,
            board=[[0 for _ in range(15)] for _ in range(15)],
            current_player=PlayerColor.BLACK,
            created_at=time.time(),
            updated_at=time.time()
        )
        
        # 创建房间
        room = RoomInfo(
            room_id=room_id,
            host=host,
            game_state=game_state
        )
        
        self.rooms[room_id] = room
        self.player_rooms[host.user_id] = room_id
        self.event_subscribers[room_id] = []
        
        logger.info(f"房间 {room_id} 创建成功，房主: {host.username}")
        return room_id
    
    def join_room(self, room_id: str, player: Player) -> bool:
        """加入房间"""
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        
        # 检查房间是否已满
        if room.guest is not None:
            return False
        
        # 设置玩家颜色（后加入的为白棋）
        player.color = PlayerColor.WHITE
        room.guest = player
        self.player_rooms[player.user_id] = room_id
        
        # 更新游戏状态
        room.game_state.status = GameStatus.READY
        room.game_state.updated_at = time.time()
        
        logger.info(f"玩家 {player.username} 加入房间 {room_id}")
        
        # 发送玩家加入事件
        asyncio.create_task(self._broadcast_event(room_id, GameEvent(
            type="player_joined",
            room_id=room_id,
            data={
                "player": {
                    "user_id": player.user_id,
                    "username": player.username,
                    "color": player.color.value
                }
            },
            timestamp=time.time()
        )))
        # ✅ 自动开始游戏（新加逻辑）
        asyncio.create_task(self._auto_start_game(room_id))

        return True

    async def _auto_start_game(self, room_id: str):
        """当房间凑齐两人后自动开始游戏"""
        await asyncio.sleep(0.5)  # 给前端一点缓冲时间
        room = self.rooms.get(room_id)
        if not room or not room.host or not room.guest:
            return

        if room.game_state.status == GameStatus.READY:
            room.game_state.status = GameStatus.PLAYING
            room.game_state.updated_at = time.time()
            logger.info(f"房间 {room_id} 游戏自动开始")

            await self._broadcast_event(room_id, GameEvent(
                type="game_started",
                room_id=room_id,
                data={
                    "current_player": room.game_state.current_player.value,
                    "host_color": room.host.color.value if room.host.color else None,
                    "guest_color": room.guest.color.value if room.guest.color else None
                },
                timestamp=time.time()
            ))
    
    def leave_room(self, user_id: str) -> bool:
        """离开房间"""
        if user_id not in self.player_rooms:
            return False
        
        room_id = self.player_rooms[user_id]
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        
        # 发送玩家离开事件
        asyncio.create_task(self._broadcast_event(room_id, GameEvent(
            type="player_left",
            room_id=room_id,
            data={"user_id": user_id},
            timestamp=time.time()
        )))
        
        # 移除玩家
        if room.host.user_id == user_id:
            # 房主离开，删除房间（_delete_room已经清理了player_rooms映射）
            self._delete_room(room_id)
        else:
            # 客人离开
            room.guest = None
            room.game_state.status = GameStatus.WAITING
            room.game_state.updated_at = time.time()
            # 只删除当前用户的映射
            del self.player_rooms[user_id]
        
        return True
    
    def make_move(self, room_id: str, user_id: str, x: int, y: int) -> bool:
        """下棋"""
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        game_state = room.game_state
        
        # 检查游戏状态
        if game_state.status != GameStatus.PLAYING:
            return False
        
        # 检查棋盘边界
        if x < 0 or x >= 15 or y < 0 or y >= 15:
            return False
        
        # 检查位置是否已有棋子
        if game_state.board[y][x] != 0:
            return False
        
        # 确定玩家颜色
        player_color = None
        if room.host.user_id == user_id:
            player_color = room.host.color
        elif room.guest and room.guest.user_id == user_id:
            player_color = room.guest.color
        
        if not player_color:
            return False
        
        # 检查是否轮到该玩家
        if game_state.current_player != player_color:
            return False
        
        # 下棋
        color_value = 1 if player_color == PlayerColor.BLACK else 2
        game_state.board[y][x] = color_value
        
        # 记录移动
        move = Move(
            x=x, y=y, color=player_color, timestamp=time.time()
        )
        game_state.moves.append(move)
        game_state.last_move = move
        game_state.updated_at = time.time()
        
        # 检查是否获胜
        if self._check_winner(game_state.board, x, y, color_value):
            game_state.winner = player_color
            game_state.status = GameStatus.FINISHED
            
            # 发送游戏结束事件
            asyncio.create_task(self._broadcast_event(room_id, GameEvent(
                type="game_ended",
                room_id=room_id,
                data={
                    "winner": player_color.value,
                    "move": {
                        "x": x, "y": y, "color": player_color.value
                    }
                },
                timestamp=time.time()
            )))
        else:
            # 切换玩家
            game_state.current_player = PlayerColor.WHITE if game_state.current_player == PlayerColor.BLACK else PlayerColor.BLACK
            
            # 发送移动事件
            asyncio.create_task(self._broadcast_event(room_id, GameEvent(
                type="move_made",
                room_id=room_id,
                data={
                    "move": {
                        "x": x, "y": y, "color": player_color.value
                    },
                    "current_player": game_state.current_player.value,
                    "board": game_state.board
                },
                timestamp=time.time()
            )))
        
        return True
    
    def start_game(self, room_id: str, user_id: str) -> bool:
        """开始游戏"""
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        
        # 只有房主可以开始游戏
        if room.host.user_id != user_id:
            return False
        
        # 检查是否有两个玩家
        if room.guest is None:
            return False
        
        # 开始游戏
        room.game_state.status = GameStatus.PLAYING
        room.game_state.updated_at = time.time()
        
        logger.info(f"房间 {room_id} 游戏开始")
        
        # 发送游戏开始事件
        asyncio.create_task(self._broadcast_event(room_id, GameEvent(
            type="game_started",
            room_id=room_id,
            data={
                "current_player": room.game_state.current_player.value,
                "host_color": room.host.color.value if room.host.color else None,
                "guest_color": room.guest.color.value if room.guest.color else None
            },
            timestamp=time.time()
        )))
        
        return True
    
    def restart_game(self, room_id: str, user_id: str) -> bool:
        """重新开始游戏"""
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        
        # 只有房主可以重新开始
        if room.host.user_id != user_id:
            return False
        
        # 重置游戏状态
        room.game_state.board = [[0 for _ in range(15)] for _ in range(15)]
        room.game_state.current_player = PlayerColor.BLACK
        room.game_state.winner = None
        room.game_state.last_move = None
        room.game_state.moves = []
        room.game_state.status = GameStatus.READY
        room.game_state.updated_at = time.time()
        
        logger.info(f"房间 {room_id} 游戏重新开始")
        
        # 发送游戏重新开始事件
        asyncio.create_task(self._broadcast_event(room_id, GameEvent(
            type="game_started",
            room_id=room_id,
            data={
                "current_player": room.game_state.current_player.value,
                "board": room.game_state.board
            },
            timestamp=time.time()
        )))
        
        return True
    
    def get_room_info(self, room_id: str) -> Optional[RoomInfo]:
        """获取房间信息"""
        return self.rooms.get(room_id)
    
    def get_player_room(self, user_id: str) -> Optional[str]:
        """获取玩家所在房间"""
        return self.player_rooms.get(user_id)
    
    def add_event_subscriber(self, room_id: str, queue: asyncio.Queue):
        """添加事件订阅者"""
        if room_id not in self.event_subscribers:
            self.event_subscribers[room_id] = []
        self.event_subscribers[room_id].append(queue)
    
    def remove_event_subscriber(self, room_id: str, queue: asyncio.Queue):
        """移除事件订阅者"""
        if room_id in self.event_subscribers:
            try:
                self.event_subscribers[room_id].remove(queue)
            except ValueError:
                pass
    
    async def _broadcast_event(self, room_id: str, event: GameEvent):
        """广播事件给所有订阅者"""
        if room_id not in self.event_subscribers:
            return
        
        # 发送给所有订阅者
        for queue in self.event_subscribers[room_id]:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"发送事件失败: {e}")
                # 移除失效的队列
                try:
                    self.event_subscribers[room_id].remove(queue)
                except ValueError:
                    pass
    
    def _delete_room(self, room_id: str):
        """删除房间"""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            # 清理玩家映射
            if room.host.user_id in self.player_rooms:
                del self.player_rooms[room.host.user_id]
            if room.guest and room.guest.user_id in self.player_rooms:
                del self.player_rooms[room.guest.user_id]
            
            # 删除房间
            del self.rooms[room_id]
            
            # 清理事件订阅者
            if room_id in self.event_subscribers:
                del self.event_subscribers[room_id]
            
            logger.info(f"房间 {room_id} 已删除")
    
    def _check_winner(self, board: List[List[int]], x: int, y: int, color: int) -> bool:
        """检查是否获胜"""
        directions = [
            (1, 0),   # 水平
            (0, 1),   # 垂直
            (1, 1),   # 对角线
            (1, -1)   # 反对角线
        ]
        
        for dx, dy in directions:
            count = 1
            
            # 正向检查
            for i in range(1, 5):
                new_x, new_y = x + dx * i, y + dy * i
                if (new_x < 0 or new_x >= 15 or new_y < 0 or new_y >= 15 or 
                    board[new_y][new_x] != color):
                    break
                count += 1
            
            # 反向检查
            for i in range(1, 5):
                new_x, new_y = x - dx * i, y - dy * i
                if (new_x < 0 or new_x >= 15 or new_y < 0 or new_y >= 15 or 
                    board[new_y][new_x] != color):
                    break
                count += 1
            
            if count >= 5:
                return True
        
        return False


# 全局游戏服务实例
game_service = GameService()
