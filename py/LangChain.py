import os
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from config import OPENAI_API_KEY, OPENAI_API_BASE

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# 创建 LLM
llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-3.5-turbo",
    openai_api_base=OPENAI_API_BASE
)

# 定义提示模板
prompt = PromptTemplate(
    input_variables=["topic"],
    template="请你写一段关于{topic}的简短介绍。",
)

# 创建链（无需内存）
chain = LLMChain(llm=llm, prompt=prompt, verbose=True)

# 运行
response = chain.run({"topic": "人工智能"})
print("最终输出：", response)
