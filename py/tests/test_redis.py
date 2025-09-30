#!/usr/bin/env python3
"""
Redis连接测试脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

def test_redis_connection():
    """测试Redis连接"""
    try:
        from config.config import REDIS_CONFIG
        print(f"🔍 测试Redis连接...")
        print(f"配置信息: {REDIS_CONFIG}")
        
        import redis
        
        # 创建Redis连接
        client = redis.Redis(
            host=REDIS_CONFIG["host"],
            port=REDIS_CONFIG["port"],
            db=REDIS_CONFIG["database"],
            password=REDIS_CONFIG["password"],
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # 测试连接
        result = client.ping()
        print(f"✅ Redis连接成功: {result}")
        
        # 测试基本操作
        client.set("test_key", "test_value", ex=60)
        value = client.get("test_key")
        print(f"✅ Redis读写测试成功: {value}")
        
        client.delete("test_key")
        print("✅ Redis删除测试成功")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    if success:
        print("🎉 Redis连接测试通过！")
    else:
        print("💥 Redis连接测试失败！")
        sys.exit(1)


