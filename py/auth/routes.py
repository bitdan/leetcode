import logging

from auth.captcha import generate_captcha_payload
from auth.schemas import ApiResponse, UserCreate, UserInfo, UserLogin
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)
security = HTTPBearer()


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["认证"])
    user_service = container.user_service

    async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
        user_info = user_service.validate_user_session(credentials.credentials)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证失败，请重新登录",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_info

    router.get_current_user = get_current_user

    @router.post("/register", response_model=ApiResponse)
    async def register(user_data: UserCreate):
        try:
            user = user_service.register_user(user_data)
            token = user_service.create_user_session(user)
            return ApiResponse(code=200, msg="注册成功", data={"token": token})
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except Exception as exc:
            logger.exception("Register failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="注册失败，请稍后重试") from exc

    @router.post("/login", response_model=ApiResponse)
    async def login(login_data: UserLogin):
        try:
            user = user_service.authenticate_user(login_data)
            token = user_service.create_user_session(user)
            return ApiResponse(code=200, msg="登录成功", data={"token": token})
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
        except Exception as exc:
            logger.exception("Login failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="登录失败，请稍后重试") from exc

    @router.post("/logout", response_model=ApiResponse)
    async def logout(current_user: UserInfo = Depends(get_current_user)):
        user_service.logout_user(current_user.user.user_id)
        return ApiResponse(code=200, msg="登出成功")

    @router.get("/getInfo", response_model=ApiResponse)
    async def get_user_info(current_user: UserInfo = Depends(get_current_user)):
        data = current_user.model_dump(mode="json") if hasattr(current_user, "model_dump") else current_user.dict()
        return ApiResponse(code=200, msg="获取用户信息成功", data=data)

    @router.get("/captchaImage", response_model=ApiResponse)
    async def get_captcha():
        return ApiResponse(code=200, msg="获取验证码成功", data=generate_captcha_payload())

    return router
