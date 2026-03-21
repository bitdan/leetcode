#!/usr/bin/env python3
"""
认证功能测试脚本
"""
import sys
from pathlib import Path

import requests

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

BASE_URL = "http://localhost:8000"

def test_captcha():
    """测试获取验证码"""
    print("🔍 测试获取验证码...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/captchaImage")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 验证码获取成功: {data['data']['uuid']}")
            return data['data']
        else:
            print(f"❌ 验证码获取失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 验证码获取异常: {e}")
        return None

def test_register():
    """测试用户注册"""
    print("\n🔍 测试用户注册...")
    
    # 先获取验证码
    captcha_data = test_captcha()
    if not captcha_data:
        return None
    
    register_data = {
        "username": "testuser",
        "password": "123456",
        "confirm_password": "123456",
        "code": "TEST",  # 测试用验证码
        "uuid": captcha_data['uuid'],
        "user_type": "sys_user"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/register", json=register_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 用户注册成功")
            return data['data']['token']
        else:
            print(f"❌ 用户注册失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 用户注册异常: {e}")
        return None

def test_login():
    """测试用户登录"""
    print("\n🔍 测试用户登录...")
    
    # 先获取验证码
    captcha_data = test_captcha()
    if not captcha_data:
        return None
    
    login_data = {
        "username": "admin",  # 使用默认管理员账号
        "password": "123456",
        "code": "TEST",  # 测试用验证码
        "uuid": captcha_data['uuid']
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 用户登录成功")
            return data['data']['token']
        else:
            print(f"❌ 用户登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 用户登录异常: {e}")
        return None

def test_get_user_info(token):
    """测试获取用户信息"""
    print("\n🔍 测试获取用户信息...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/getInfo", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 获取用户信息成功: {data['data']['user']['username']}")
            return data['data']
        else:
            print(f"❌ 获取用户信息失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 获取用户信息异常: {e}")
        return None

def test_logout(token):
    """测试用户登出"""
    print("\n🔍 测试用户登出...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/logout", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 用户登出成功")
            return True
        else:
            print(f"❌ 用户登出失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 用户登出异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试Tool Hub认证功能...")
    print("=" * 50)
    
    # 测试注册
    register_token = test_register()
    
    # 测试登录
    login_token = test_login()
    
    if login_token:
        # 测试获取用户信息
        user_info = test_get_user_info(login_token)
        
        # 测试登出
        test_logout(login_token)
        
        # 测试登出后访问用户信息（应该失败）
        print("\n🔍 测试登出后访问用户信息...")
        user_info_after_logout = test_get_user_info(login_token)
        if user_info_after_logout is None:
            print("✅ 登出后无法访问用户信息（符合预期）")
        else:
            print("❌ 登出后仍能访问用户信息（不符合预期）")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")

if __name__ == "__main__":
    main()


