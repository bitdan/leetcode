import base64
import io
import json
import os
import requests
from PIL import Image
from datetime import datetime
from typing import Optional, List

from config import OPENAI_API_KEY, OPENAI_API_BASE


class TextToImageGenerator:
    """文字转图片生成器"""

    def __init__(self):
        self.openai_api_key = OPENAI_API_KEY
        self.openai_api_base = OPENAI_API_BASE

    def generate_with_dalle(self,
                            prompt: str,
                            size: str = "1024x1024",
                            quality: str = "standard",
                            style: str = "vivid",
                            n: int = 1) -> List[str]:
        """
        使用OpenAI DALL-E生成图片
        
        Args:
            prompt: 图片描述
            size: 图片尺寸 ("1024x1024", "1792x1024", "1024x1792")
            quality: 图片质量 ("standard", "hd")
            style: 图片风格 ("vivid", "natural")
            n: 生成图片数量
            
        Returns:
            图片URL列表
        """
        url = f"{self.openai_api_base}/images/generations"

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "dall-e-3",
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "style": style,
            "n": n
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            image_urls = [item["url"] for item in result["data"]]

            print(f"✅ 成功生成 {len(image_urls)} 张图片")
            return image_urls

        except requests.exceptions.RequestException as e:
            print(f"❌ DALL-E API调用失败: {e}")
            return []

    def generate_with_stable_diffusion(self,
                                       prompt: str,
                                       api_url: str = "http://localhost:7860",
                                       width: int = 512,
                                       height: int = 512,
                                       steps: int = 20,
                                       cfg_scale: float = 7.0) -> List[str]:
        """
        使用Stable Diffusion API生成图片
        
        Args:
            prompt: 图片描述
            api_url: Stable Diffusion API地址
            width: 图片宽度
            height: 图片高度
            steps: 生成步数
            cfg_scale: CFG比例
            
        Returns:
            图片base64编码列表
        """
        url = f"{api_url}/sdapi/v1/txt2img"

        data = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": "DPM++ 2M Karras"
        }

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()

            result = response.json()
            images = result["images"]

            print(f"✅ 成功生成 {len(images)} 张图片")
            return images

        except requests.exceptions.RequestException as e:
            print(f"❌ Stable Diffusion API调用失败: {e}")
            return []

    def save_images(self,
                    images: List[str],
                    output_dir: str = "generated_images",
                    prefix: str = "image") -> List[str]:
        """
        保存图片到本地
        
        Args:
            images: 图片URL或base64编码列表
            output_dir: 输出目录
            prefix: 文件名前缀
            
        Returns:
            保存的文件路径列表
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        saved_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i, image_data in enumerate(images):
            try:
                # 判断是URL还是base64
                if image_data.startswith("http"):
                    # 下载图片
                    response = requests.get(image_data)
                    response.raise_for_status()
                    img = Image.open(io.BytesIO(response.content))
                else:
                    # base64解码
                    image_bytes = base64.b64decode(image_data)
                    img = Image.open(io.BytesIO(image_bytes))

                # 保存图片
                filename = f"{prefix}_{timestamp}_{i + 1}.png"
                filepath = os.path.join(output_dir, filename)
                img.save(filepath)
                saved_paths.append(filepath)

                print(f"💾 图片已保存: {filepath}")

            except Exception as e:
                print(f"❌ 保存图片失败: {e}")

        return saved_paths

    def generate_and_save(self,
                          prompt: str,
                          method: str = "dalle",
                          **kwargs) -> List[str]:
        """
        生成并保存图片的便捷方法
        
        Args:
            prompt: 图片描述
            method: 生成方法 ("dalle" 或 "stable_diffusion")
            **kwargs: 其他参数
            
        Returns:
            保存的文件路径列表
        """
        print(f"🎨 开始生成图片: {prompt}")
        print(f"📋 使用方法: {method}")

        if method.lower() == "dalle":
            images = self.generate_with_dalle(prompt, **kwargs)
        elif method.lower() == "stable_diffusion":
            images = self.generate_with_stable_diffusion(prompt, **kwargs)
        else:
            print(f"❌ 不支持的方法: {method}")
            return []

        if images:
            return self.save_images(images)
        else:
            return []


def create_image_prompt(text: str, style: str = "realistic") -> str:
    """
    将普通文本转换为图片生成提示词
    
    Args:
        text: 原始文本
        style: 图片风格
        
    Returns:
        优化后的提示词
    """
    style_prompts = {
        "realistic": "高清摄影风格，",
        "artistic": "艺术插画风格，",
        "cartoon": "卡通动画风格，",
        "watercolor": "水彩画风格，",
        "oil_painting": "油画风格，",
        "digital_art": "数字艺术风格，",
        "minimalist": "极简主义风格，",
        "vintage": "复古怀旧风格，"
    }

    style_prefix = style_prompts.get(style, "")

    # 添加质量提升词
    quality_enhancers = [
        "高质量", "精细细节", "专业摄影", "4K分辨率",
        "完美构图", "自然光线", "清晰锐利"
    ]

    enhanced_prompt = f"{style_prefix}{text}，{', '.join(quality_enhancers[:3])}"

    return enhanced_prompt


# ===== 使用示例 =====
if __name__ == "__main__":
    # 创建生成器实例
    generator = TextToImageGenerator()

    # 示例1: 使用DALL-E生成图片
    print("=" * 50)
    print("示例1: 使用DALL-E生成美食图片")
    print("=" * 50)

    food_prompt = create_image_prompt(
        "一盘精美的融合菜，包含中式炒菜和西式配菜，色彩丰富，摆盘精致",
        style="realistic"
    )

    generator.generate_and_save(
        prompt=food_prompt,
        method="dalle",
        size="1024x1024",
        quality="hd"
    )

    # 示例2: 使用Stable Diffusion生成图片
    print("\n" + "=" * 50)
    print("示例2: 使用Stable Diffusion生成艺术风格图片")
    print("=" * 50)

    art_prompt = create_image_prompt(
        "一只可爱的小猫坐在花园里，周围有美丽的花朵",
        style="watercolor"
    )

    # 注意：需要本地运行Stable Diffusion API服务
    # generator.generate_and_save(
    #     prompt=art_prompt,
    #     method="stable_diffusion",
    #     width=512,
    #     height=512
    # )

    print("\n✅ 图片生成完成！请查看 generated_images 文件夹")
