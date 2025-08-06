import os
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated

from config import OPENAI_API_KEY, OPENAI_API_BASE
from text_to_image import TextToImageGenerator, create_image_prompt

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
llm = ChatOpenAI(
    temperature=0.7, model="gpt-4o-mini", openai_api_base=OPENAI_API_BASE
)


# ===== 1. 扩展状态结构 =====
class ContentState(TypedDict):
    """内容创作工作流的状态容器"""
    topic: str  # 用户输入的主题
    draft: str  # 文字草稿
    corrections: list[str]  # 文字修正记录
    image_prompt: str  # 图片生成提示词
    image_paths: list[str]  # 生成的图片路径
    attempts: int  # 尝试次数


# ===== 2. 创建节点函数 =====
def generate_content_draft(state: ContentState):
    """根据主题生成内容草稿"""
    prompt = PromptTemplate.from_template(
        "请为{topic}写一段详细的内容介绍，包含以下要素：\n"
        "1. 基本介绍和背景\n"
        "2. 主要特点或优势\n"
        "3. 实际应用场景\n"
        "4. 相关建议或推荐\n\n"
        "要求：内容详实，语言生动，300-500字。"
    )
    chain = prompt | llm
    return {"draft": chain.invoke({"topic": state["topic"]}).content}


def critique_content(state: ContentState):
    """对内容进行批判性评估"""
    prompt = PromptTemplate.from_template(
        "请对以下内容进行批判性分析并提出改进建议：\n\n{draft}\n\n"
        "请从以下角度分析：\n"
        "1. 内容完整性\n"
        "2. 逻辑结构\n"
        "3. 语言表达\n"
        "4. 实用性\n"
        "指出至少2项可改进之处。"
    )
    chain = prompt | llm
    feedback = chain.invoke({"draft": state["draft"]})
    current_attempts = state.get("attempts", 0) + 1
    return {"corrections": [feedback.content], "attempts": current_attempts}


def refine_content(state: ContentState):
    """根据反馈修正内容"""
    last_feedback = state["corrections"][-1]
    prompt = PromptTemplate.from_template(
        "请根据以下反馈重写内容：\n反馈：{feedback}\n\n原文：{draft}\n\n"
        "保留原文风格但解决反馈中提到的问题，确保内容更加完善。"
    )
    chain = prompt | llm
    new_draft = chain.invoke({"feedback": last_feedback, "draft": state["draft"]})
    return {"draft": new_draft.content}


def generate_image_prompt(state: ContentState):
    """根据内容生成图片提示词"""
    prompt = PromptTemplate.from_template(
        "请根据以下内容，生成一个简洁的图片描述，用于生成配图：\n\n{draft}\n\n"
        "要求：\n"
        "1. 描述要具体且富有视觉感\n"
        "2. 突出内容的核心主题\n"
        "3. 适合生成高质量的图片\n"
        "4. 控制在50字以内\n\n"
        "请直接输出图片描述，不要添加其他说明。"
    )
    chain = prompt | llm
    image_prompt = chain.invoke({"draft": state["draft"]}).content.strip()

    # 使用提示词优化函数
    enhanced_prompt = create_image_prompt(image_prompt, style="realistic")

    return {"image_prompt": enhanced_prompt}


def generate_images(state: ContentState):
    """生成配图"""
    generator = TextToImageGenerator()

    # 生成图片
    image_paths = generator.generate_and_save(
        prompt=state["image_prompt"],
        method="dalle",
        size="1024x1024",
        quality="hd"
    )

    return {"image_paths": image_paths}


# ===== 3. 构建工作流图 =====
workflow = StateGraph(ContentState)

# 添加节点
workflow.add_node("generate_content", generate_content_draft)
workflow.add_node("critique_content", critique_content)
workflow.add_node("refine_content", refine_content)
workflow.add_node("generate_image_prompt", generate_image_prompt)
workflow.add_node("generate_images", generate_images)

# 设置入口点
workflow.set_entry_point("generate_content")

# 添加过渡路径
workflow.add_edge("generate_content", "critique_content")
workflow.add_edge("refine_content", "critique_content")
workflow.add_edge("critique_content", "generate_image_prompt")
workflow.add_edge("generate_image_prompt", "generate_images")


# 添加条件判断边
def should_continue_refinement(state: ContentState):
    """检查是否需要继续修正内容"""
    last_feedback = state["corrections"][-1].lower()

    # 如果有"满意"或"无需修改"则继续到图片生成
    if "满意" in last_feedback or "无需修改" in last_feedback:
        return "generate_image_prompt"

    # 最多尝试3次修正
    return "refine_content" if state["attempts"] < 3 else "generate_image_prompt"


workflow.add_conditional_edges(
    "critique_content",
    should_continue_refinement,
    {"refine_content": "refine_content", "generate_image_prompt": "generate_image_prompt"}
)

# 编译图形
graph = workflow.compile()


# ===== 4. 执行工作流 =====
def run_integrated_workflow(topic: str):
    """执行集成工作流"""
    print(f"\n{'=' * 60}")
    print(f"🎯 开始创作主题: {topic}")
    print(f"{'=' * 60}")

    # 初始化状态
    state = {
        "topic": topic,
        "draft": "",
        "corrections": [],
        "image_prompt": "",
        "image_paths": [],
        "attempts": 0
    }

    # 分步骤执行
    for step, output in enumerate(graph.stream(state)):
        step_name = list(output.keys())[0]

        if step_name == "generate_content":
            print(f"\n📝 [内容草稿]:")
            print(f"{output[step_name]['draft']}")

        elif step_name == "critique_content":
            print(f"\n🔍 [第{output[step_name]['attempts']}轮反馈]:")
            print(f"{output[step_name]['corrections'][-1]}")

        elif step_name == "refine_content":
            print(f"\n✏️ [修正后的内容]:")
            print(f"{output[step_name]['draft']}")

        elif step_name == "generate_image_prompt":
            print(f"\n🎨 [图片生成提示词]:")
            print(f"{output[step_name]['image_prompt']}")

        elif step_name == "generate_images":
            print(f"\n🖼️ [图片生成结果]:")
            for path in output[step_name]['image_paths']:
                print(f"图片已保存: {path}")

    # 最终结果
    final_state = graph.invoke(state)

    print(f"\n{'=' * 60}")
    print(f"🎉 创作完成！")
    print(f"{'=' * 60}")
    print(f"📊 统计信息:")
    print(f"   - 内容修正次数: {len(final_state['corrections'])}")
    print(f"   - 生成图片数量: {len(final_state['image_paths'])}")
    print(f"\n📝 最终内容:")
    print(f"{final_state['draft']}")
    print(f"\n🎨 图片提示词:")
    print(f"{final_state['image_prompt']}")
    print(f"\n🖼️ 图片文件:")
    for path in final_state['image_paths']:
        print(f"  - {path}")


# ===== 5. 运行示例 =====
if __name__ == "__main__":
    # 示例：创作关于美食的内容和配图
    run_integrated_workflow("有什么好吃的融合菜,给出推荐")
