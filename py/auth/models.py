from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None


class UserCreate(UserBase):
    password: str
    confirm_password: str
    code: str
    uuid: str
    user_type: str = "sys_user"


class UserLogin(BaseModel):
    username: str
    password: str
    code: str
    uuid: str


class User(UserBase):
    user_id: str
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None


class UserInfo(BaseModel):
    user: User
    roles: List[str] = []
    permissions: List[str] = []


class CaptchaResponse(BaseModel):
    captcha_enabled: bool = True
    uuid: str
    img: str


class ApiResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Optional[dict] = None


# 微信登录相关模型
class WechatLoginRequest(BaseModel):
    """微信登录请求"""
    code: str  # 微信授权码
    state: Optional[str] = None  # 状态参数


class WechatBindRequest(BaseModel):
    """微信绑定请求"""
    openid: str  # 微信openid
    username: str  # 要绑定的用户名
    password: str  # 密码验证


class WechatUserInfo(BaseModel):
    """微信用户信息"""
    openid: str
    nickname: Optional[str] = None
    sex: Optional[int] = None
    province: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    headimgurl: Optional[str] = None
    unionid: Optional[str] = None


class QRCodeLoginRequest(BaseModel):
    """二维码登录请求"""
    scene_str: str  # 场景字符串，用于标识登录会话


class QRCodeLoginResponse(BaseModel):
    """二维码登录响应"""
    ticket: str  # 二维码ticket
    qr_code_url: str  # 二维码URL
    scene_str: str  # 场景字符串


class QRCodeStatusResponse(BaseModel):
    """二维码状态响应"""
    status: str  # 状态：waiting, scanned, confirmed, expired
    user_info: Optional[WechatUserInfo] = None
    message: Optional[str] = None


class WechatLoginResponse(BaseModel):
    """微信登录响应"""
    success: bool
    token: Optional[str] = None
    user_info: Optional[UserInfo] = None
    wechat_info: Optional[WechatUserInfo] = None
    message: str
    need_bind: bool = False  # 是否需要绑定现有账号