import logging

from auth.routes import AUTH_COOKIE_NAME
from auth.schemas import ApiResponse, UserInfo
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from post.schemas import PostCreateRequest, PostListData, PostUpdateRequest
from post.store import PostStoreUnavailable

logger = logging.getLogger(__name__)


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/posts", tags=["社区帖子"])
    post_service = container.post_service
    auth_router = getattr(container, "_auth_router", None)

    async def get_current_user_proxy() -> UserInfo:
        raise RuntimeError("Auth dependency not attached")

    get_current_user = getattr(auth_router, "get_current_user", get_current_user_proxy)

    def dump_model(model) -> dict:
        return model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()

    def get_optional_user(request: Request):
        authorization = request.headers.get("Authorization", "")
        token = ""
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        token = token or request.cookies.get(AUTH_COOKIE_NAME, "")
        return container.user_service.validate_user_session(token) if token else None

    @router.get("", response_model=ApiResponse)
    async def list_posts(
            keyword: str = Query(default="", max_length=120),
            page: int = Query(default=1, ge=1),
            page_size: int = Query(default=10, ge=1, le=50),
            current_user: UserInfo = Depends(get_optional_user),
    ):
        try:
            items, total = post_service.list_posts(keyword=keyword, page=page, page_size=page_size,
                                                   current_user=current_user)
            data = PostListData(items=items, total=total, page=page, page_size=page_size)
            return ApiResponse(code=200, msg="获取帖子列表成功", data=dump_model(data))
        except PostStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    @router.get("/{post_id}", response_model=ApiResponse)
    async def get_post(post_id: str, current_user: UserInfo = Depends(get_optional_user)):
        try:
            data = post_service.get_post(post_id, current_user=current_user)
            return ApiResponse(code=200, msg="获取帖子成功", data=dump_model(data))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        except PostStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    @router.post("", response_model=ApiResponse)
    async def create_post(payload: PostCreateRequest, current_user: UserInfo = Depends(get_current_user)):
        try:
            data = post_service.create_post(payload.title, payload.content, current_user)
            return ApiResponse(code=200, msg="发布成功", data=dump_model(data))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except PostStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
        except Exception as exc:
            logger.exception("Create post failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="发布失败，请稍后重试") from exc

    @router.put("/{post_id}", response_model=ApiResponse)
    async def update_post(
            post_id: str,
            payload: PostUpdateRequest,
            current_user: UserInfo = Depends(get_current_user),
    ):
        try:
            data = post_service.update_post(post_id, payload.title, payload.content, current_user)
            return ApiResponse(code=200, msg="更新成功", data=dump_model(data))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
        except PostStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    @router.delete("/{post_id}", response_model=ApiResponse)
    async def delete_post(post_id: str, current_user: UserInfo = Depends(get_current_user)):
        try:
            post_service.delete_post(post_id, current_user)
            return ApiResponse(code=200, msg="删除成功")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
        except PostStoreUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return router
