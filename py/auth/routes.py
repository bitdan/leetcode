import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.models import (
    UserCreate, UserLogin, Token, UserInfo, 
    CaptchaResponse, ApiResponse
)
from auth.user_service import user_service
from auth.jwt_handler import jwt_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["认证"])
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """获取当前用户信息"""
    try:
        token = credentials.credentials
        user_info = user_service.validate_user_session(token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证失败，请重新登录",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=ApiResponse)
async def register(user_data: UserCreate):
    """用户注册"""
    try:
        user = user_service.register_user(user_data)
        if user:
            # 注册成功后直接登录
            token = user_service.create_user_session(user)
            return ApiResponse(
                code=200,
                msg="注册成功",
                data={"token": token}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="注册失败"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"用户注册API调用失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/login", response_model=ApiResponse)
async def login(login_data: UserLogin):
    """用户登录"""
    try:
        user = user_service.authenticate_user(login_data)
        if user:
            token = user_service.create_user_session(user)
            return ApiResponse(
                code=200,
                msg="登录成功",
                data={"token": token}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"用户登录API调用失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.post("/logout", response_model=ApiResponse)
async def logout(current_user: UserInfo = Depends(get_current_user)):
    """用户登出"""
    try:
        success = user_service.logout_user(current_user.user.user_id)
        if success:
            return ApiResponse(
                code=200,
                msg="登出成功"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="登出失败"
            )
    except Exception as e:
        logger.error(f"用户登出API调用失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败，请稍后重试"
        )


@router.get("/getInfo", response_model=ApiResponse)
async def get_user_info(current_user: UserInfo = Depends(get_current_user)):
    """获取用户信息"""
    try:
        user_info_dict = {
            "user": {
                "user_id": current_user.user.user_id,
                "username": current_user.user.username,
                "email": current_user.user.email,
                "avatar": current_user.user.avatar
            },
            "roles": current_user.roles,
            "permissions": current_user.permissions
        }
        
        return ApiResponse(
            code=200,
            msg="获取用户信息成功",
            data=user_info_dict
        )
    except Exception as e:
        logger.error(f"获取用户信息API调用失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.get("/captchaImage", response_model=ApiResponse)
async def get_captcha():
    """获取验证码"""
    try:
        import uuid
        import base64
        from io import BytesIO
        from PIL import Image, ImageDraw, ImageFont
        import random
        import string

        # 生成随机验证码
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        uuid_str = str(uuid.uuid4())
        
        # 创建验证码图片
        width, height = 120, 40
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # 绘制验证码文字
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
        
        # 绘制文字
        bbox = draw.textbbox((0, 0), code, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # 随机颜色
        colors = ['red', 'blue', 'green', 'purple', 'orange']
        color = random.choice(colors)
        draw.text((x, y), code, fill=color, font=font)
        
        # 添加干扰线
        for _ in range(3):
            start_x = random.randint(0, width)
            start_y = random.randint(0, height)
            end_x = random.randint(0, width)
            end_y = random.randint(0, height)
            draw.line([(start_x, start_y), (end_x, end_y)], fill=random.choice(colors), width=1)
        
        # 转换为base64
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return ApiResponse(
            code=200,
            msg="获取验证码成功",
            data={
                "captcha_enabled": True,
                "uuid": uuid_str,
                "img": img_base64
            }
        )
    except Exception as e:
        logger.error(f"获取验证码API调用失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取验证码失败"
        )
