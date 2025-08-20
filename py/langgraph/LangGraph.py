import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import config

logger = logging.getLogger(__name__)

# 从环境变量(.env)读取OpenAI配置
llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4o-mini",
    openai_api_key=config.OPENAI_API_KEY,
    openai_api_base=config.OPENAI_API_BASE,
    request_timeout=60,
    max_retries=2,  # 最多重试2次
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
        "请围绕主题'{topic}'撰写一篇简洁的文章。要求：\n"
        "1. 内容准确、逻辑清晰\n"
        "2. 长度适中（200-400字）\n"
        "3. 语言流畅自然\n\n"
        "主题：{topic}"
    )
    chain = prompt | llm
    result_text = chain.invoke({"topic": state["topic"]}).content
    logger.info(f"生成初始草稿:\n{result_text}")
    return {"draft": result_text}


def critique_draft(state: TextState):
    """对当前草稿进行批判性评估 - 优化版本，减少不必要的修正"""
    # 如果已经是第2次或以上尝试，进行更严格的评估
    current_attempts = state.get("attempts", 0) + 1
    
    if current_attempts >= 2:
        # 后续评估更严格，避免过度修正
        prompt = PromptTemplate.from_template(
            "请简要评估以下文本质量：\n\n{draft}\n\n"
            "如果文本已经达到基本要求（内容准确、逻辑清晰、语言通顺），请回复'满意'。\n"
            "否则，请指出1-2个最关键的改进点。"
        )
    else:
        prompt = PromptTemplate.from_template(
            "请评估以下文本并提出改进建议：\n\n{draft}\n\n"
            "指出1-2项最重要的改进之处，或如果已经满意请说明。"
        )
    
    chain = prompt | llm
    feedback = chain.invoke({"draft": state["draft"]})
    logger.info(f"第{current_attempts}轮反馈:\n{feedback.content}")
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
    logger.info(f"修正后的草稿:\n{new_draft.content}")
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

    # 如果有"满意"、"无需修改"、"已经很好"等停止词则停止
    stop_words = ["满意", "无需修改", "已经很好", "质量良好", "符合要求", "达到标准"]
    if any(word in last_feedback for word in stop_words):
        return END

    # 最多尝试2次（减少循环次数以提高响应速度）
    return "refine" if state["attempts"] < 2 else END


workflow.add_conditional_edges(
    "critique", should_continue,
)

# 编译图形
graph = workflow.compile()


# ===== 4. 执行工作流 =====
def run_workflow(topic: str):
    """执行工作流并打印结果"""
    logger.info(f"\n{'=' * 40}\n 生成主题: {topic}\n{'=' * 40}")

    # 初始化状态
    state = {"topic": topic, "draft": "", "corrections": [], "attempts": 0}

    # 分步骤执行
    for step, output in enumerate(graph.stream(state)):
        step_name = list(output.keys())[0]
        if step_name == "generate":
            logger.info(f"\n[初始草稿]:\n{output[step_name]['draft']}")
        elif step_name == "critique":
            logger.info(f"\n[第{step}轮反馈]:\n{output[step_name]['corrections'][-1]}")
        elif step_name == "refine":
            logger.info(f"\n[第{step}轮修改后的草稿]:\n{output[step_name]['draft']}")

    # 最终结果
    final_state = graph.invoke(state)
    logger.info(
        f"\n{'=' * 40}\n最终结果 (经过{len(final_state['corrections'])}次修正):\n{'=' * 40}"
    )
    logger.info(final_state["draft"])

    return final_state


# ===== 5. 运行示例 =====
if __name__ == "__main__":
    run_workflow("数据太多怎么办")
