import os
import yaml
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")

# JWT配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "6"))

# Redis配置
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "43.156.83.246"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "database": int(os.getenv("REDIS_DATABASE", "14")),
    "password": os.getenv("REDIS_PASSWORD", "dudu0.0@"),
    "decode_responses": True
}

# 从YAML配置文件加载（如果存在）
def load_config_from_yaml():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if 'redis' in config:
                REDIS_CONFIG.update(config['redis'])
            if 'jwt' in config:
                global JWT_SECRET_KEY, JWT_EXPIRATION_HOURS
                JWT_SECRET_KEY = config['jwt'].get('secret_key', JWT_SECRET_KEY)
                JWT_EXPIRATION_HOURS = config['jwt'].get('expiration_hours', JWT_EXPIRATION_HOURS)

load_config_from_yaml()
