from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


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
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)


class UserProfileUpdate(BaseModel):
    email: Optional[str] = None
    avatar: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    oldPassword: str
    newPassword: str
    confirmPassword: str


class TotpAccountUpsert(BaseModel):
    label: Optional[str] = None
    issuer: Optional[str] = None
    accountName: Optional[str] = None
    secret: Optional[str] = None
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"
    otpauthUri: Optional[str] = None


class TotpImportRequest(BaseModel):
    text: Optional[str] = None
    items: List[TotpAccountUpsert] = Field(default_factory=list)
    mergeMode: str = "append"


class CaptchaResponse(BaseModel):
    captcha_enabled: bool = True
    uuid: str
    img: str


class ApiResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Optional[Any] = None
