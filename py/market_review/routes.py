from auth.schemas import ApiResponse
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from market_review.service import MarketReviewUnavailable


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/market-review", tags=["市场复盘"])
    service = container.market_review_service

    def dump_model(model) -> dict:
        return model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()

    @router.get("", response_model=ApiResponse)
    async def review(date: str = Query(default="")):
        try:
            data = service.review(date or None)
            return ApiResponse(code=200, msg="获取市场复盘成功", data=dump_model(data))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    @router.post("/warmup", response_model=ApiResponse)
    async def warmup(background_tasks: BackgroundTasks, date: str = Query(default="")):
        normalized_date = service._normalize_date(date or None)
        background_tasks.add_task(service.review, normalized_date)
        return ApiResponse(code=200, msg="市场复盘预热任务已提交", data={"date": normalized_date})

    @router.get("/limit-up-pool", response_model=ApiResponse)
    async def limit_up_pool(date: str = Query(default="")):
        try:
            data = [dump_model(item) for item in service.limit_up_pool(date or None)]
            return ApiResponse(code=200, msg="获取涨停池成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    @router.get("/sector-strength", response_model=ApiResponse)
    async def sector_strength(date: str = Query(default="")):
        try:
            data = [dump_model(item) for item in service.sector_strength(date or None)]
            return ApiResponse(code=200, msg="获取板块强度成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    @router.get("/candidates/2-to-3", response_model=ApiResponse)
    async def candidates_2_to_3(date: str = Query(default="")):
        try:
            data = [dump_model(item) for item in service.candidates_2_to_3(date or None)]
            return ApiResponse(code=200, msg="获取 2进3 候选成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    @router.get("/divergence-consensus", response_model=ApiResponse)
    async def divergence_consensus(date: str = Query(default="")):
        try:
            data = [dump_model(item) for item in service.divergence_consensus(date or None)]
            return ApiResponse(code=200, msg="获取分歧转一致识别成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return router
