import logging
import operator
import sys
import time
from pathlib import Path
from typing import Annotated, Literal, TypedDict

import config
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

# 添加项目根目录到 Python 路径（便于本地直接运行）
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
STOP_WORDS = ["满意", "无需修改", "已经很好", "质量良好", "符合要求", "达到标准"]

llm = ChatOpenAI(
    temperature=0.7,
    model="gpt-4o-mini",
    openai_api_key=config.OPENAI_API_KEY,
    openai_api_base=config.OPENAI_API_BASE,
    request_timeout=60,
    max_retries=2,
)


class TextState(TypedDict):
    """LangGraph 状态对象（每个节点都读写这个结构）"""

    topic: str
    draft: str
    corrections: Annotated[list[str], operator.add]
    trace: Annotated[list[dict], operator.add]
    attempts: int
    next_action: Literal["refine", "end"]


def _is_feedback_good_enough(feedback: str, attempts: int) -> bool:
    feedback_text = (feedback or "").lower()
    if any(word in feedback_text for word in STOP_WORDS):
        return True
    return attempts >= MAX_ATTEMPTS


def _short_text(text: str, limit: int = 80) -> str:
    value = (text or "").replace("\n", " ").strip()
    if len(value) <= limit:
        return value
    return value[:limit] + "..."


def generate_draft(state: TextState) -> dict:
    """节点1：按 topic 生成初稿"""
    start = time.perf_counter()
    prompt = PromptTemplate.from_template(
        "请围绕主题'{topic}'撰写一篇简洁的文章。要求：\n"
        "1. 内容准确、逻辑清晰\n"
        "2. 长度适中（200-400字）\n"
        "3. 语言流畅自然\n\n"
        "主题：{topic}"
    )
    chain = prompt | llm
    draft = chain.invoke({"topic": state["topic"]}).content
    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info("[generate] 生成初稿完成")
    return {
        "draft": draft,
        "trace": [
            {
                "node": "generate",
                "input_summary": f"topic={state['topic']}",
                "output_summary": f"draft_len={len(draft)}, preview={_short_text(draft)}",
                "decision": "to critique",
                "latency_ms": latency_ms,
            }
        ],
    }


def critique_draft(state: TextState) -> dict:
    """节点2：评估当前草稿，并决定继续 refine 还是结束"""
    start = time.perf_counter()
    attempts = state.get("attempts", 0) + 1

    if attempts >= 2:
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
    feedback = chain.invoke({"draft": state["draft"]}).content
    good_enough = _is_feedback_good_enough(feedback, attempts)
    next_action: Literal["refine", "end"] = "end" if good_enough else "refine"
    latency_ms = int((time.perf_counter() - start) * 1000)

    logger.info("[critique] 第%s轮完成，next_action=%s", attempts, next_action)
    return {
        "corrections": [feedback],
        "attempts": attempts,
        "next_action": next_action,
        "trace": [
            {
                "node": "critique",
                "input_summary": f"attempt={attempts}, draft_len={len(state.get('draft', ''))}",
                "output_summary": _short_text(feedback),
                "decision": next_action,
                "latency_ms": latency_ms,
            }
        ],
    }


def refine_draft(state: TextState) -> dict:
    """节点3：基于最新 feedback 改写草稿"""
    start = time.perf_counter()
    feedback = state["corrections"][-1] if state.get("corrections") else "请优化逻辑与表达"
    prompt = PromptTemplate.from_template(
        "请根据以下反馈重写文本：\n反馈：{feedback}\n\n原文：{draft}\n\n"
        "保留原文风格但解决反馈中提到的问题。"
    )
    chain = prompt | llm
    new_draft = chain.invoke({"feedback": feedback, "draft": state["draft"]}).content
    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info("[refine] 重写完成")
    return {
        "draft": new_draft,
        "trace": [
            {
                "node": "refine",
                "input_summary": _short_text(feedback),
                "output_summary": f"draft_len={len(new_draft)}, preview={_short_text(new_draft)}",
                "decision": "to critique",
                "latency_ms": latency_ms,
            }
        ],
    }


def should_continue(state: TextState):
    """条件边：根据 critique 节点写入的 next_action 决定流向"""
    return END if state.get("next_action") == "end" else "refine"


workflow = StateGraph(TextState)
workflow.add_node("generate", generate_draft)
workflow.add_node("critique", critique_draft)
workflow.add_node("refine", refine_draft)

workflow.set_entry_point("generate")
workflow.add_edge("generate", "critique")
workflow.add_edge("refine", "critique")
workflow.add_conditional_edges("critique", should_continue)

graph = workflow.compile()


def run_workflow(topic: str) -> TextState:
    """
    运行 LangGraph 工作流并返回最终状态。
    这版用于学习：会返回 trace，便于理解每一步是如何流转的。
    """
    logger.info("开始运行工作流, topic=%s", topic)
    init_state: TextState = {
        "topic": topic,
        "draft": "",
        "corrections": [],
        "trace": [],
        "attempts": 0,
        "next_action": "refine",
    }

    final_state = graph.invoke(init_state)
    logger.info("工作流完成, attempts=%s", final_state.get("attempts", 0))
    for step in final_state.get("trace", []):
        logger.info("[trace] %s", step)
    return final_state


if __name__ == "__main__":
    run_workflow("数据太多怎么办")
