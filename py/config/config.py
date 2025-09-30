import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# OpenAI API配置（从环境变量读取）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")

# JWT配置（从环境变量读取）
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-env")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "6"))

# Redis配置
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "43.156.83.246"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "database": int(os.getenv("REDIS_DATABASE", "14")),
    "password": os.getenv("REDIS_PASSWORD", "dudu0.0@"),
    "decode_responses": True
}

# 微信登录配置
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "your_wechat_app_id")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "your_wechat_app_secret")
WECHAT_REDIRECT_URI = os.getenv("WECHAT_REDIRECT_URI", "http://localhost:8000/api/v1/wechat/callback")
FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN", "http://localhost:3000")

# 二维码配置
QR_EXPIRE_TIME = int(os.getenv("QR_EXPIRE_TIME", "300"))  # 5分钟
QR_SIZE = int(os.getenv("QR_SIZE", "300"))  # 二维码大小

