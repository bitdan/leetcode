#!/usr/bin/env python3
"""
测试五子棋游戏完整流程
"""
import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

async def test_complete_flow():
    """测试完整的游戏流程"""
    async with aiohttp.ClientSession() as session:
        # 1. 获取验证码
        print("1. 获取验证码...")
        async with session.get(f"{BASE_URL}/api/v1/captchaImage") as resp:
            if resp.status == 200:
                captcha_data = await resp.json()
                captcha_uuid = captcha_data.get('data', {}).get('uuid', 'test-uuid')
                print(f"验证码UUID: {captcha_uuid}")
            else:
                print("使用默认验证码")
                captcha_uuid = "test-uuid"
        
        # 2. 登录获取token
        print("2. 用户登录...")
        login_data = {
            "username": "admin",
            "password": "admin123",
            "code": "TEST",  # 测试验证码
            "uuid": captcha_uuid
        }
        
        # 登录
        async with session.post(f"{BASE_URL}/api/v1/login", json=login_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data.get('data', {}).get('token')
                print(f"登录成功，token: {token[:20]}...")
            else:
                text = await resp.text()
                print(f"登录失败: {resp.status}, {text}")
                return
        
        # 设置认证头
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. 创建房间
        print("3. 创建游戏房间...")
        async with session.post(f"{BASE_URL}/api/v1/game/create-room", 
                               json={}, 
                               headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                room_id = data.get('data', {}).get('room_id')
                print(f"房间创建成功，房间ID: {room_id}")
            else:
                text = await resp.text()
                print(f"创建房间失败: {resp.status}, {text}")
                return
        
        # 4. 获取房间信息
        print(f"4. 获取房间信息: {room_id}")
        async with session.get(f"{BASE_URL}/api/v1/game/room/{room_id}", 
                              headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"房间信息: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                text = await resp.text()
                print(f"获取房间信息失败: {resp.status}, {text}")
        
        # 5. 测试SSE连接
        print(f"5. 测试SSE事件流: {room_id}")
        try:
            async with session.get(f"{BASE_URL}/api/v1/game/events/{room_id}?access_token={token}") as resp:
                if resp.status == 200:
                    print("SSE连接成功")
                    # 读取几个事件
                    count = 0
                    async for line in resp.content:
                        if count >= 2:
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
                    text = await resp.text()
                    print(f"SSE连接失败: {resp.status}, {text}")
        except Exception as e:
            print(f"SSE测试错误: {e}")
        
        # 6. 离开房间
        print("6. 离开房间...")
        async with session.post(f"{BASE_URL}/api/v1/game/leave-room", 
                               json={}, 
                               headers=headers) as resp:
            if resp.status == 200:
                print("离开房间成功")
            else:
                text = await resp.text()
                print(f"离开房间失败: {resp.status}, {text}")

if __name__ == "__main__":
    print("开始测试五子棋游戏完整流程...")
    asyncio.run(test_complete_flow())
    print("测试完成")
