import meilisearch
import os
import sys
from dotenv import load_dotenv
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Meilisearch
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv()

# 导入配置
import config

# 创建 Meilisearch 客户端
client = meilisearch.Client(
    url=os.environ.get("MEILI_HTTP_ADDR"),
    api_key=os.environ.get("MEILI_API_KEY"),
)

# 创建 OpenAI 嵌入模型
embeddings = OpenAIEmbeddings(
    openai_api_base=config.OPENAI_API_BASE
)

# 创建向量存储
vector_store = Meilisearch(client=client, embedding=embeddings)

# 执行相似性搜索
query = "superhero fighting evil in a city at night"
results = vector_store.similarity_search(
    query=query,
    k=3,
)

# 显示搜索结果
print("搜索结果:")
for i, result in enumerate(results, 1):
    print(f"\n结果 {i}:")
    print(result.page_content)
