"""
微信登录功能测试文件
"""
import asyncio
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.wechat_service import wechat_service
from auth.user_service import user_service
from auth.models import WechatLoginRequest, WechatBindRequest, QRCodeLoginRequest


async def test_wechat_login():
    """测试微信登录功能"""
    print("=== 微信登录功能测试 ===")
    
    # 1. 测试获取微信登录URL
    print("\n1. 测试获取微信登录URL")
    login_url = wechat_service.get_wechat_login_url()
    print(f"微信登录URL: {login_url}")
    
    # 2. 测试微信登录（模拟）
    print("\n2. 测试微信登录")
    mock_code = "mock_wechat_code_123"
    login_result = wechat_service.wechat_login(mock_code)
    print(f"登录结果: {login_result}")
    
    # 3. 测试创建二维码登录
    print("\n3. 测试创建二维码登录")
    scene_str = "test_login_session_123"
    qr_result = wechat_service.create_qr_code_login(scene_str)
    if qr_result:
        print(f"二维码登录创建成功:")
        print(f"  Ticket: {qr_result.ticket}")
        print(f"  QR URL: {qr_result.qr_code_url}")
        print(f"  Scene: {qr_result.scene_str}")
    
    # 4. 测试检查二维码状态
    print("\n4. 测试检查二维码状态")
    status_result = wechat_service.check_qr_code_status(scene_str)
    print(f"二维码状态: {status_result}")
    
    # 5. 测试用户绑定微信
    print("\n5. 测试用户绑定微信")
    # 先创建一个测试用户（直接添加到数据库，绕过验证码）
    try:
        import uuid
        from datetime import datetime
        from auth.jwt_handler import jwt_handler
        
        # 直接创建用户数据
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        password_hash = jwt_handler.get_password_hash("test123456")
        
        user_dict = {
            "user_id": user_id,
            "username": "test_wechat_user",
            "password_hash": password_hash,
            "email": "test@example.com",
            "avatar": None,
            "roles": ["user"],
            "permissions": [],
            "wechat_openid": None,
            "login_type": "password",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 直接添加到用户数据库
        user_service.users_db["test_wechat_user"] = user_dict
        print(f"测试用户创建成功: test_wechat_user")
        
        # 绑定微信
        bind_result = wechat_service.bind_wechat_user(
            "mock_openid_123",
            "test_wechat_user",
            "test123456"
        )
        print(f"绑定结果: {bind_result}")
        
    except Exception as e:
        print(f"用户创建或绑定失败: {e}")
    
    # 6. 测试根据openid获取用户
    print("\n6. 测试根据openid获取用户")
    wechat_user = user_service.get_user_by_wechat_openid("mock_openid_123")
    if wechat_user:
        print(f"找到微信用户: {wechat_user.username}")
    else:
        print("未找到微信用户")
    
    print("\n=== 测试完成 ===")


async def test_api_endpoints():
    """测试API端点（需要运行服务器）"""
    print("\n=== API端点测试 ===")
    print("注意：此测试需要服务器正在运行")
    
    import requests
    
    base_url = "http://localhost:8000/api/v1"
    
    try:
        # 测试获取微信登录URL
        response = requests.get(f"{base_url}/wechat/login-url")
        if response.status_code == 200:
            data = response.json()
            print(f"获取微信登录URL成功: {data}")
        else:
            print(f"获取微信登录URL失败: {response.status_code}")
        
        # 测试创建二维码登录
        qr_data = {"scene_str": "api_test_123"}
        response = requests.post(f"{base_url}/wechat/qr/create", json=qr_data)
        if response.status_code == 200:
            data = response.json()
            print(f"创建二维码登录成功: {data}")
        else:
            print(f"创建二维码登录失败: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("无法连接到服务器，请确保服务器正在运行")


if __name__ == "__main__":
    print("开始测试微信登录功能...")
    
    # 运行基础功能测试
    asyncio.run(test_wechat_login())
    
    # 运行API测试（可选）
    # asyncio.run(test_api_endpoints())
    
    print("\n测试完成！")
