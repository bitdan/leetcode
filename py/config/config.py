import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
