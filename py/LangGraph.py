import os
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated

from config import OPENAI_API_KEY, OPENAI_API_BASE

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
# 配置OpenAI - 使用实际API密钥替换
llm = ChatOpenAI(
    temperature=0.7, model="gpt-4o-mini", openai_api_base=OPENAI_API_BASE
)


# ===== 1. 定义状态结构 =====
class TextState(TypedDict):
    """工作流的状态容器"""

    topic: str  # 用户输入的主题
    draft: str  # 草稿内容
    corrections: list[str]  # 所有修正记录
    attempts: int  # 尝试次数


# ===== 2. 创建节点函数 =====
def generate_draft(state: TextState):
    """根据主题生成初始草稿"""
    prompt = PromptTemplate.from_template(
        "请为{topic}写一段200字左右的介绍，包含历史背景和现代应用："
    )
    chain = prompt | llm
    return {"draft": chain.invoke({"topic": state["topic"]}).content}


def critique_draft(state: TextState):
    """对当前草稿进行批判性评估"""
    prompt = PromptTemplate.from_template(
        "请批判性分析以下文本并提出改进建议：\n\n{draft}\n\n" "指出至少2项可改进之处。"
    )
    chain = prompt | llm
    feedback = chain.invoke({"draft": state["draft"]})
    # 增加尝试次数
    current_attempts = state.get("attempts", 0) + 1
    return {"corrections": [feedback.content], "attempts": current_attempts}


def refine_draft(state: TextState):
    """根据反馈修正草稿"""
    last_feedback = state["corrections"][-1]
    prompt = PromptTemplate.from_template(
        "请根据以下反馈重写文本：\n反馈：{feedback}\n\n原文：{draft}\n\n"
        "保留原文风格但解决反馈中提到的问题。"
    )
    chain = prompt | llm
    new_draft = chain.invoke({"feedback": last_feedback, "draft": state["draft"]})
    return {"draft": new_draft.content}


# ===== 3. 构建工作流图 =====
workflow = StateGraph(TextState)

# 添加节点
workflow.add_node("generate", generate_draft)
workflow.add_node("critique", critique_draft)
workflow.add_node("refine", refine_draft)

# 设置入口点
workflow.set_entry_point("generate")

# 添加过渡路径
workflow.add_edge("generate", "critique")
workflow.add_edge("refine", "critique")


# 添加条件判断边（控制循环）
def should_continue(state: TextState):
    """检查是否满足停止条件：尝试次数>2 或 最后一次修正提到已达标"""
    last_feedback = state["corrections"][-1].lower()

    # 如果有"满意"或"无需修改"则停止
    if "满意" in last_feedback or "无需修改" in last_feedback:
        return END

    # 最多尝试3次
    return "refine" if state["attempts"] < 3 else END


workflow.add_conditional_edges(
    "critique", should_continue, {"refine": "refine", END: END}
)

# 编译图形
graph = workflow.compile()


# ===== 4. 执行工作流 =====
def run_workflow(topic: str):
    """执行工作流并打印结果"""
    print(f"\n{'=' * 40}\n 生成主题: {topic}\n{'=' * 40}")

    # 初始化状态
    state = {"topic": topic, "draft": "", "corrections": [], "attempts": 0}

    # 分步骤执行
    for step, output in enumerate(graph.stream(state)):
        step_name = list(output.keys())[0]
        if step_name == "generate":
            print(f"\n[初始草稿]:\n{output[step_name]['draft']}")
        elif step_name == "critique":
            print(f"\n[第{step}轮反馈]:\n{output[step_name]['corrections'][-1]}")
        elif step_name == "refine":
            print(f"\n[第{step}轮修改后的草稿]:\n{output[step_name]['draft']}")

    # 最终结果
    final_state = graph.invoke(state)
    print(
        f"\n{'=' * 40}\n最终结果 (经过{len(final_state['corrections'])}次修正):\n{'=' * 40}"
    )
    print(final_state["draft"])


# ===== 5. 运行示例 =====
if __name__ == "__main__":
    run_workflow("有什么好吃的融合菜,给出推荐")
