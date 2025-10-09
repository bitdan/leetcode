from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None


class UserCreate(UserBase):
    password: str
    confirmPassword: str
    code: str
    uuid: str
    userType: str = "sys_user"


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
