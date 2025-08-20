@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo [92m开始构建LangGraph API Docker镜像...[0m

REM 检查Docker是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [91m错误: Docker未运行，请先启动Docker[0m
    pause
    exit /b 1
)

REM 构建镜像
echo [93m构建Docker镜像...[0m

REM 读取版本号参数，默认 1.0.0
set "APP_VERSION=%1"
if "%APP_VERSION%"=="" set "APP_VERSION=1.0.5"
set "IMAGE_NAME=biasoo/langgraph-api:%APP_VERSION%"

echo 将使用版本: %APP_VERSION%
docker build -t %IMAGE_NAME% --build-arg APP_VERSION=%APP_VERSION% .

if errorlevel 1 (
    echo [91m镜像构建失败[0m
    pause
    exit /b 1
)

echo [92m镜像构建成功![0m

REM 询问是否立即运行容器
set /p run_container="是否立即运行容器? (y/n): "
if /i "!run_container!"=="y" (
    echo [93m启动容器...[0m
    
    REM 停止并删除已存在的容器
    docker stop langgraph-api >nul 2>&1
    docker rm langgraph-api >nul 2>&1
    
        docker run -d ^
        --name langgraph-api ^
            -p 8000:8000 ^
        -e OPENAI_API_KEY=%OPENAI_API_KEY% ^
        -e OPENAI_API_BASE=%OPENAI_API_BASE% ^
            %IMAGE_NAME%
    
    if errorlevel 1 (
        echo [91m容器启动失败[0m
    ) else (
        echo [92m容器启动成功![0m
        echo [92mAPI服务运行在: http://localhost:8000[0m
        echo [92m健康检查: http://localhost:8000/health[0m
    )
)

echo.
echo [92m构建完成![0m
pause
