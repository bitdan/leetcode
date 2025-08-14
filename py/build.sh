#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始构建LangGraph API Docker镜像...${NC}"

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}错误: Docker未运行，请先启动Docker${NC}"
    exit 1
fi

# 构建镜像
echo -e "${YELLOW}构建Docker镜像...${NC}"

# 读取版本号参数，默认 1.0.0
APP_VERSION=${1:-1.0.0}
IMAGE_TAG="biasoo/langgraph-api:${APP_VERSION}"
echo "将使用版本: ${APP_VERSION}"

docker build -t "${IMAGE_TAG}" --build-arg APP_VERSION="${APP_VERSION}" .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}镜像构建成功!${NC}"
    
    # 询问是否立即运行容器
    read -p "是否立即运行容器? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}启动容器...${NC}"
        docker run -d \
            --name langgraph-api \
            -p 8000:8000 \
            -e OPENAI_API_KEY=${OPENAI_API_KEY:-} \
            -e OPENAI_API_BASE=${OPENAI_API_BASE:-} \
            "${IMAGE_TAG}"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}容器启动成功!${NC}"
            echo -e "${GREEN}API服务运行在: http://localhost:8000${NC}"
            echo -e "${GREEN}健康检查: http://localhost:8000/health${NC}"
        else
            echo -e "${RED}容器启动失败${NC}"
        fi
    fi
else
    echo -e "${RED}镜像构建失败${NC}"
    exit 1
fi
