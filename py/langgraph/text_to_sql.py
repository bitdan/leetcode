import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from langchain_community.utilities import SQLDatabase
from langchain_community.chains import SQLDatabaseChain
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain.chains import create_sql_query_chain
from typing import TypedDict

from config.config import OPENAI_API_KEY, OPENAI_API_BASE

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# 1. 数据库连接
db = SQLDatabase.from_uri(
    "mysql+pymysql://hykjtest:hykj188?AA@192.168.9.188:3306/hykj_erp",
    include_tables=["pms_purchase_plan_order"]  # 精简表结构，防止token超限
)

# 2. LLM配置
llm = ChatOpenAI(
    model="gpt-4o-mini",  # 也可用 gpt-4o、deepseek
    openai_api_base=OPENAI_API_BASE
)


# 3. 定义状态
class QAState(TypedDict):
    question: str
    sql: str
    sql_result: str
    answer: str


# 4. LangGraph节点
chain = SQLDatabaseChain.from_llm(
    llm,
    db,
    return_intermediate_steps=True,  # 关键参数
    verbose=True
)


def ask_and_answer(state: QAState):
    result = chain({"query": state["question"]})
    sql = ""
    sql_result = ""
    if "intermediate_steps" in result and result["intermediate_steps"]:
        sql = result["intermediate_steps"][-1]["sql_cmd"]
        sql_result = result["intermediate_steps"][-1]["result"]
    answer = result.get("result", result)
    return {"sql": sql, "sql_result": str(sql_result), "answer": answer}


# 5. 构建LangGraph工作流
workflow = StateGraph(QAState)
workflow.add_node("ask_and_answer", ask_and_answer)
workflow.set_entry_point("ask_and_answer")
graph = workflow.compile()


# 6. 运行示例
def run_qa(question: str):
    print(f"\n用户提问：{question}")
    state = {"question": question, "sql": "", "sql_result": "", "answer": ""}
    for step, output in enumerate(graph.stream(state)):
        step_name = list(output.keys())[0]
        print(f"\n[{step_name}]")
        print(output[step_name])
    final = graph.invoke(state)
    print("\n最终AI回答：")
    print(final["answer"])
    print("\nSQL语句：")
    print(final["sql"])
    print("\nSQL结果：")
    print(final["sql_result"])


if __name__ == "__main__":
    run_qa("查询上个月买的最多的是什么产品,并给出数量")
