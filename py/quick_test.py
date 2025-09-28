#!/usr/bin/env python3
"""
快速测试登录功能
"""
import requests
import json

def test_login():
    """测试登录"""
    url = "http://localhost:8000/api/v1/login"
    data = {
        "username": "admin",
        "password": "admin123",
        "code": "TEST",
        "uuid": "test-uuid"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"登录成功! Token: {result['data']['token'][:50]}...")
        else:
            print("登录失败")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_login()
