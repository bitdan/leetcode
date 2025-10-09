# 五子棋在线对局功能

## 功能概述

基于FastAPI + SSE实现的五子棋在线对局系统，支持：

- 创建房间邀请好友
- 实时在线对局
- 游戏状态同步
- 断线重连
- 游戏历史记录

## 技术架构

### 后端 (FastAPI)

- **游戏服务**: `game/service.py` - 核心游戏逻辑和状态管理
- **API路由**: `game/routes.py` - RESTful API接口
- **数据模型**: `game/models.py` - Pydantic数据模型
- **SSE事件流**: 实时推送游戏状态变化

### 前端 (Vue 3 + TypeScript)

- **游戏组件**: `Gomoku.vue` - 五子棋游戏界面
- **游戏逻辑**: `useGomokuGame.ts` - 在线游戏状态管理
- **API客户端**: `game.ts` - 后端API调用封装

## API接口

### 房间管理

- `POST /api/v1/game/create-room` - 创建游戏房间
- `POST /api/v1/game/join-room` - 加入游戏房间
- `POST /api/v1/game/leave-room` - 离开游戏房间
- `GET /api/v1/game/room/{room_id}` - 获取房间信息

### 游戏操作

- `POST /api/v1/game/make-move` - 下棋
- `POST /api/v1/game/start-game` - 开始游戏
- `POST /api/v1/game/restart-game` - 重新开始游戏

### 实时通信

- `GET /api/v1/game/events/{room_id}` - SSE事件流

## 游戏流程

1. **创建房间**: 玩家A创建房间，获得房间ID
2. **邀请好友**: 分享房间ID给玩家B
3. **加入房间**: 玩家B使用房间ID加入
4. **开始游戏**: 房主点击开始游戏
5. **实时对局**: 双方轮流下棋，状态实时同步
6. **游戏结束**: 一方获胜或重新开始

## 数据结构

### 游戏状态

```typescript
interface GameState {
  status: 'waiting' | 'ready' | 'playing' | 'finished'
  board: number[][]  // 15x15棋盘，0:空, 1:黑棋, 2:白棋
  currentPlayer: 'black' | 'white'
  winner: 'black' | 'white' | null
  lastMove: { x: number, y: number } | null
  movesCount: number
}
```

### 玩家信息

```typescript
interface Player {
  userId: string
  username: string
  color: 'black' | 'white' | null
  isReady: boolean
  isOnline: boolean
}
```

## 事件类型

SSE事件流支持以下事件类型：

- `connected` - 连接建立
- `room_state` - 房间状态更新
- `player_joined` - 玩家加入
- `player_left` - 玩家离开
- `game_started` - 游戏开始
- `move_made` - 下棋移动
- `game_ended` - 游戏结束
- `error` - 错误信息
- `heartbeat` - 心跳保持连接

## 部署说明

### 后端部署

1. 安装依赖：`pip install -r requirements.txt`
2. 配置环境变量（Redis连接等）
3. 启动服务：`python api/main.py`

### 前端部署

1. 安装依赖：`npm install`
2. 配置API地址：`VITE_API_BASE_URL`
3. 构建部署：`npm run build`

## 测试

运行测试脚本验证API功能：

```bash
python test_game_api.py
```

## 注意事项

1. **认证**: 所有API需要Bearer token认证
2. **SSE连接**: 使用查询参数传递token（EventSource限制）
3. **房间管理**: 房主离开时房间自动删除
4. **状态同步**: 通过SSE确保实时状态同步
5. **错误处理**: 完善的错误处理和用户提示

## 扩展功能

可扩展的功能：

- 观战模式
- 游戏录像回放
- 排行榜系统
- 聊天功能
- 游戏设置（时间限制等）
- 多房间管理
