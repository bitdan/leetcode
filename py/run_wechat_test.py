#!/usr/bin/env python3
"""
微信登录功能测试启动脚本
"""
import sys
import os
import asyncio

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 现在可以导入auth模块
from auth.test_wechat_login import test_wechat_login

if __name__ == "__main__":
    print("开始运行微信登录功能测试...")
    try:
        asyncio.run(test_wechat_login())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试运行出错: {e}")
        import traceback
        traceback.print_exc()
    print("测试完成！")
