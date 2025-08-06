#!/usr/bin/env python3
"""
文字转图片功能测试脚本
"""

import os
import sys

from text_to_image import TextToImageGenerator, create_image_prompt


def test_prompt_optimization():
    """测试提示词优化功能"""
    print("🧪 测试提示词优化功能...")

    test_texts = [
        "一盘精美的融合菜",
        "一只可爱的小猫",
        "美丽的风景画"
    ]

    styles = ["realistic", "watercolor", "cartoon"]

    for text in test_texts:
        for style in styles:
            enhanced = create_image_prompt(text, style)
            print(f"原文: {text}")
            print(f"风格: {style}")
            print(f"优化后: {enhanced}")
            print("-" * 50)


def test_image_generation():
    """测试图片生成功能（不实际调用API）"""
    print("\n🧪 测试图片生成功能...")

    generator = TextToImageGenerator()

    # 测试配置
    print(f"OpenAI API Base: {generator.openai_api_base}")
    print(f"API Key 已配置: {'是' if generator.openai_api_key else '否'}")

    # 测试提示词生成
    test_prompt = "一盘精美的融合菜，包含中式炒菜和西式配菜"
    enhanced_prompt = create_image_prompt(test_prompt, "realistic")

    print(f"测试提示词: {test_prompt}")
    print(f"优化后提示词: {enhanced_prompt}")

    # 模拟生成参数
    print("\n模拟生成参数:")
    print("- 方法: DALL-E 3")
    print("- 尺寸: 1024x1024")
    print("- 质量: HD")
    print("- 风格: Vivid")


def test_integration():
    """测试与LangGraph的集成"""
    print("\n🧪 测试与LangGraph集成...")

    try:
        from integrated_workflow import run_integrated_workflow
        print("✅ 集成工作流模块导入成功")

        # 检查工作流组件
        from langgraph.graph import StateGraph
        print("✅ LangGraph组件可用")

    except ImportError as e:
        print(f"❌ 集成测试失败: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")


def main():
    """主测试函数"""
    print("=" * 60)
    print("🎯 文字转图片功能测试")
    print("=" * 60)

    # 检查配置文件
    print("📋 检查配置文件...")
    try:
        from config import OPENAI_API_KEY, OPENAI_API_BASE
        print(f"✅ 配置文件加载成功")
        print(f"   API Base: {OPENAI_API_BASE}")
        print(f"   API Key: {'已配置' if OPENAI_API_KEY else '未配置'}")
    except ImportError as e:
        print(f"❌ 配置文件加载失败: {e}")
        return

    # 运行测试
    test_prompt_optimization()
    test_image_generation()
    test_integration()

    print("\n" + "=" * 60)
    print("🎉 测试完成！")
    print("=" * 60)

    print("\n📝 使用建议:")
    print("1. 确保已配置正确的API密钥")
    print("2. 运行 'python text_to_image.py' 进行实际图片生成")
    print("3. 运行 'python integrated_workflow.py' 体验完整工作流")
    print("4. 查看 README.md 获取详细使用说明")


if __name__ == "__main__":
    main()
