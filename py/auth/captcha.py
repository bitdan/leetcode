import base64
import random
import string
import uuid
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


def generate_captcha_payload() -> dict:
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    uuid_str = str(uuid.uuid4())
    width, height = 120, 40
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), code, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2

    colors = ["red", "blue", "green", "purple", "orange"]
    draw.text((x, y), code, fill=random.choice(colors), font=font)
    for _ in range(3):
        draw.line(
            [
                (random.randint(0, width), random.randint(0, height)),
                (random.randint(0, width), random.randint(0, height)),
            ],
            fill=random.choice(colors),
            width=1,
        )

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return {
        "captcha_enabled": True,
        "uuid": uuid_str,
        "img": base64.b64encode(buffer.getvalue()).decode(),
    }
