#!/usr/bin/env python3
"""
Tool Hub API 启动脚本
"""
import os
import sys
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def main():
    """启动API服务器"""
    # 设置环境变量
    os.environ.setdefault("LOG_LEVEL", "INFO")
    
    # 启动服务器
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
