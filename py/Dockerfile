# ============ 构建阶段（生成依赖 wheels） ============
FROM python:3.10.18 AS builder

WORKDIR /app

# 构建参数
ARG APP_VERSION=1.0.0

# 环境
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# 系统依赖（仅用于构建阶段）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制并预构建 wheels，最大化缓存复用
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip==24.0 setuptools==68.2.2 wheel==0.41.2 \
    && pip wheel --wheel-dir /wheels -r /app/requirements.txt


# ============ 运行阶段（精简运行时） ============
FROM python:3.10.18 AS runtime

# 应用名称与版本（可在构建时通过 --build-arg 覆盖）
ARG APP_NAME=langgraph-api
ARG APP_VERSION=1.0.0

# 镜像元数据
LABEL org.opencontainers.image.title="$APP_NAME" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.description="LangGraph API service" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# 运行时环境变量
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# 仅安装运行所需的系统依赖（健康检查与Pillow运行时）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 以及预构建的 wheels
COPY requirements.txt /app/requirements.txt
COPY --from=builder /wheels /wheels

# 安装依赖（从 wheels 离线安装，无缓存）
RUN pip install --no-index --find-links=/wheels -r /app/requirements.txt \
    && rm -rf /wheels

# 复制应用代码
COPY . /app

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "api/main.py"]
