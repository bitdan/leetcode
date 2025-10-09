#!/usr/bin/env python3
"""
五子棋游戏API测试脚本
"""
import asyncio
import aiohttp
import json
import time

BASE_URL = "http://localhost:8000"

async def test_game_api():
    """测试游戏API"""
    async with aiohttp.ClientSession() as session:
        # 1. 测试创建房间
        print("1. 测试创建房间...")
        async with session.post(f"{BASE_URL}/api/v1/game/create-room") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"创建房间成功: {data}")
                room_id = data.get('data')
            else:
                print(f"创建房间失败: {resp.status}")
                return
        
        # 2. 测试获取房间信息
        print(f"2. 测试获取房间信息: {room_id}")
        async with session.get(f"{BASE_URL}/api/v1/game/room/{room_id}") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"获取房间信息成功: {data}")
            else:
                print(f"获取房间信息失败: {resp.status}")
        
        # 3. 测试SSE事件流
        print(f"3. 测试SSE事件流: {room_id}")
        try:
            async with session.get(f"{BASE_URL}/api/v1/game/events/{room_id}") as resp:
                if resp.status == 200:
                    print("SSE连接成功")
                    # 读取前几个事件
                    count = 0
                    async for line in resp.content:
                        if count >= 3:  # 只读取前3个事件
                            break
                        if line.startswith(b'data: '):
                            event_data = line[6:].decode('utf-8').strip()
                            if event_data:
                                try:
                                    event = json.loads(event_data)
                                    print(f"收到事件: {event}")
                                    count += 1
                                except json.JSONDecodeError:
                                    pass
                else:
                    print(f"SSE连接失败: {resp.status}")
        except Exception as e:
            print(f"SSE测试错误: {e}")

if __name__ == "__main__":
    print("开始测试五子棋游戏API...")
    asyncio.run(test_game_api())
    print("测试完成")
