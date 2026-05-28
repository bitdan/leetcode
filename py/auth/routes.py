import logging

from auth.captcha import generate_captcha_payload
from auth.schemas import (
    AdminPasswordReset,
    AdminUserPage,
    AdminUserUpdate,
    ApiResponse,
    ChangePasswordRequest,
    TotpAccountUpsert,
    TotpImportRequest,
    UserCreate,
    UserInfo,
    UserLogin,
    UserProfileUpdate,
)
from common.pagination import Pagination
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)
security = HTTPBearer()
AUTH_COOKIE_NAME = "tool_hub_token"


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["认证"])
    user_service = container.user_service
    totp_service = container.totp_service

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

    async def get_current_admin(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if "admin" not in current_user.roles and "*" not in current_user.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
        return current_user

    def set_auth_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=token,
            max_age=container.settings.jwt_expiration_hours * 60 * 60,
            httponly=True,
            secure=container.settings.auth_cookie_secure,
            samesite="lax",
            path="/",
        )

    @router.post("/register", response_model=ApiResponse)
    async def register(user_data: UserCreate, response: Response):
        try:
            user = user_service.register_user(user_data)
            token = user_service.create_user_session(user)
            set_auth_cookie(response, token)
            return ApiResponse(code=200, msg="注册成功", data={"token": token})
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except Exception as exc:
            logger.exception("Register failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="注册失败，请稍后重试") from exc

    @router.post("/login", response_model=ApiResponse)
    async def login(login_data: UserLogin, response: Response):
        try:
            user = user_service.authenticate_user(login_data)
            token = user_service.create_user_session(user)
            set_auth_cookie(response, token)
            return ApiResponse(code=200, msg="登录成功", data={"token": token})
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
        except Exception as exc:
            logger.exception("Login failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="登录失败，请稍后重试") from exc

    @router.post("/logout", response_model=ApiResponse)
    async def logout(response: Response, current_user: UserInfo = Depends(get_current_user)):
        user_service.logout_user(current_user.user.user_id)
        response.delete_cookie(AUTH_COOKIE_NAME, path="/")
        return ApiResponse(code=200, msg="登出成功")

    @router.get("/getInfo", response_model=ApiResponse)
    async def get_user_info(current_user: UserInfo = Depends(get_current_user)):
        data = current_user.model_dump(mode="json") if hasattr(current_user, "model_dump") else current_user.dict()
        return ApiResponse(code=200, msg="获取用户信息成功", data=data)

    @router.get("/profile/login-stats", response_model=ApiResponse)
    async def get_login_stats(current_user: UserInfo = Depends(get_current_user)):
        data = user_service.get_login_stats(current_user.user.user_id)
        return ApiResponse(code=200, msg="获取登录统计成功", data=data)

    @router.put("/profile", response_model=ApiResponse)
    async def update_profile(payload: UserProfileUpdate, current_user: UserInfo = Depends(get_current_user)):
        try:
            data = user_service.update_profile(current_user.user.user_id, payload)
            data_dict = data.model_dump(mode="json") if hasattr(data, "model_dump") else data.dict()
            return ApiResponse(code=200, msg="更新个人信息成功", data=data_dict)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.put("/profile/password", response_model=ApiResponse)
    async def change_password(payload: ChangePasswordRequest, current_user: UserInfo = Depends(get_current_user)):
        try:
            user_service.change_password(current_user.user.user_id, payload)
            return ApiResponse(code=200, msg="修改密码成功")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.get("/admin/users", response_model=ApiResponse)
    async def list_admin_users(keyword: str = "", pagination: Pagination = Depends(),
                               current_user: UserInfo = Depends(get_current_admin)):
        data = user_service.list_admin_users(keyword.strip() or None, pagination.page, pagination.page_size)
        data = AdminUserPage.from_pagination(data.items, data.total, pagination)
        data_dict = data.model_dump(mode="json") if hasattr(data, "model_dump") else data.dict()
        return ApiResponse(code=200, msg="获取用户列表成功", data=data_dict)

    @router.put("/admin/users/{user_id}", response_model=ApiResponse)
    async def update_admin_user(user_id: str, payload: AdminUserUpdate,
                                current_user: UserInfo = Depends(get_current_admin)):
        try:
            data = user_service.update_admin_user(user_id, payload)
            data_dict = data.model_dump(mode="json") if hasattr(data, "model_dump") else data.dict()
            return ApiResponse(code=200, msg="更新用户成功", data=data_dict)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.put("/admin/users/{user_id}/password", response_model=ApiResponse)
    async def reset_admin_user_password(user_id: str, payload: AdminPasswordReset,
                                        current_user: UserInfo = Depends(get_current_admin)):
        try:
            user_service.reset_admin_user_password(user_id, payload)
            return ApiResponse(code=200, msg="重置密码成功")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.get("/captchaImage", response_model=ApiResponse)
    async def get_captcha():
        return ApiResponse(code=200, msg="获取验证码成功", data=generate_captcha_payload())

    @router.get("/2fa/accounts", response_model=ApiResponse)
    async def list_totp_accounts(current_user: UserInfo = Depends(get_current_user)):
        data = totp_service.list_accounts(current_user.user.user_id)
        return ApiResponse(code=200, msg="获取 2FA 账号成功", data=data)

    @router.get("/2fa/accounts/export", response_model=ApiResponse)
    async def export_totp_accounts(exportFormat: str = "json", current_user: UserInfo = Depends(get_current_user)):
        try:
            data = totp_service.export_accounts(current_user.user.user_id, exportFormat)
            return ApiResponse(code=200, msg="导出 2FA 账号成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.get("/2fa/accounts/{account_id}", response_model=ApiResponse)
    async def get_totp_account(account_id: str, current_user: UserInfo = Depends(get_current_user)):
        data = totp_service.get_account(current_user.user.user_id, account_id)
        if not data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
        return ApiResponse(code=200, msg="获取 2FA 账号成功", data=data)

    @router.post("/2fa/accounts", response_model=ApiResponse)
    async def create_totp_account(payload: TotpAccountUpsert, current_user: UserInfo = Depends(get_current_user)):
        try:
            data = totp_service.create_account(
                current_user.user.user_id,
                payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else payload.dict(
                    exclude_none=True),
            )
            return ApiResponse(code=200, msg="创建 2FA 账号成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.put("/2fa/accounts/{account_id}", response_model=ApiResponse)
    async def update_totp_account(account_id: str, payload: TotpAccountUpsert,
                                  current_user: UserInfo = Depends(get_current_user)):
        try:
            data = totp_service.update_account(
                current_user.user.user_id,
                account_id,
                payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else payload.dict(
                    exclude_none=True),
            )
            return ApiResponse(code=200, msg="更新 2FA 账号成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.delete("/2fa/accounts/{account_id}", response_model=ApiResponse)
    async def delete_totp_account(account_id: str, current_user: UserInfo = Depends(get_current_user)):
        try:
            totp_service.delete_account(current_user.user.user_id, account_id)
            return ApiResponse(code=200, msg="删除 2FA 账号成功")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    @router.post("/2fa/accounts/import", response_model=ApiResponse)
    async def import_totp_accounts(payload: TotpImportRequest, current_user: UserInfo = Depends(get_current_user)):
        try:
            data = totp_service.import_accounts(
                current_user.user.user_id,
                payload.model_dump() if hasattr(payload, "model_dump") else payload.dict(),
            )
            return ApiResponse(code=200, msg="导入 2FA 账号成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return router
