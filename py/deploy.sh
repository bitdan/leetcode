#!/bin/bash

# Tool Hub API 部署脚本

echo "🚀 开始部署 Tool Hub API..."

# 检查Python版本
python_version=$(python3 --version 2>&1)
echo "📋 Python版本: $python_version"

# 检查Redis连接
echo "🔍 检查Redis连接..."
if command -v redis-cli &> /dev/null; then
    if redis-cli -h 192.168.9.188 -p 6379 -n 14 ping &> /dev/null; then
        echo "✅ Redis连接正常"
    else
        echo "❌ Redis连接失败，请检查Redis服务"
        exit 1
    fi
else
    echo "⚠️  未找到redis-cli，跳过Redis连接检查"
fi

# 安装依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

# 运行测试
echo "🧪 运行认证功能测试..."
python test_auth.py

# 启动服务
echo "🎯 启动API服务..."
python start.py
