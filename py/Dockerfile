FROM python:3.10.18

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY py/requirements.txt ./requirements.txt

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码。这个 Dockerfile 需要从仓库根目录构建，
# 这样 skills/ 和 py/ 才会一起进入镜像。
COPY py/ ./py/
COPY skills/ ./skills/

WORKDIR /app/py

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "start.py"]
