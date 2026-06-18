from auth.schemas import ApiResponse
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from market_review.service import MarketReviewUnavailable


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/market-review", tags=["市场复盘"])
    service = container.market_review_service

    def dump_model(model) -> dict:
        return model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()

    def public_error(exc: Exception) -> str:
        return str(exc).replace("AKShare", "行情服务").replace("akshare", "行情服务")

    def dump_review(data) -> dict:
        payload = dump_model(data)
        snapshot_status = service.snapshot_status(data.date)
        payload["snapshot_status"] = snapshot_status
        payload["is_final"] = service.is_final_snapshot(data.date)
        return payload

    @router.get("", response_model=ApiResponse)
    async def review(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            data = service.review(date or None, refresh=refresh)
            return ApiResponse(code=200, msg="获取市场复盘成功", data=dump_review(data))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.post("/warmup", response_model=ApiResponse)
    async def warmup(
            background_tasks: BackgroundTasks,
            date: str = Query(default=""),
            refresh: bool = Query(default=False),
    ):
        normalized_date = service.normalize_date(date or None)
        background_tasks.add_task(service.review, normalized_date, refresh)
        return ApiResponse(code=200, msg="市场复盘预热任务已提交", data={"date": normalized_date})

    @router.post("/refresh", response_model=ApiResponse)
    async def refresh(date: str = Query(default="")):
        try:
            data = service.review(date or None, refresh=True)
            return ApiResponse(code=200, msg="市场复盘快照已刷新", data=dump_review(data))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.get("/status", response_model=ApiResponse)
    async def status_view(date: str = Query(default="")):
        try:
            normalized_date = service.normalize_date(date or None)
            data = service.status(normalized_date) or {"date": normalized_date, "status": "missing"}
            return ApiResponse(code=200, msg="获取市场复盘状态成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @router.get("/radar", response_model=ApiResponse)
    async def radar(
            date: str = Query(default=""),
            refresh: bool = Query(default=False),
            sector_limit: int = Query(default=20, ge=1, le=60),
            candidate_limit: int = Query(default=80, ge=1, le=200),
    ):
        try:
            data = service.market_radar(
                date or None,
                refresh=refresh,
                sector_limit=sector_limit,
                candidate_limit=candidate_limit,
            )
            return ApiResponse(code=200, msg="获取市场雷达成功", data=dump_model(data))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.get("/limit-up-pool", response_model=ApiResponse)
    async def limit_up_pool(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            data = [dump_model(item) for item in service.review(date or None, refresh=refresh).limit_up_pool]
            return ApiResponse(code=200, msg="获取涨停池成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.get("/sector-strength", response_model=ApiResponse)
    async def sector_strength(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            data = [dump_model(item) for item in service.review(date or None, refresh=refresh).sector_strength]
            return ApiResponse(code=200, msg="获取板块强度成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.get("/candidates/2-to-3", response_model=ApiResponse)
    async def candidates_2_to_3(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            data = [dump_model(item) for item in service.review(date or None, refresh=refresh).candidates_2_to_3]
            return ApiResponse(code=200, msg="获取 2进3 候选成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.get("/candidates/advancement", response_model=ApiResponse)
    async def advancement_candidates(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            data = [dump_model(item) for item in service.review(date or None, refresh=refresh).advancement_candidates]
            return ApiResponse(code=200, msg="获取连板晋级候选成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.get("/candidates/{pool_type}", response_model=ApiResponse)
    async def candidates_by_pool_type(
            pool_type: str,
            date: str = Query(default=""),
            refresh: bool = Query(default=False),
    ):
        try:
            review_data = service.review(date or None, refresh=refresh)
            normalized_pool_type = service.normalize_pool_type(pool_type)
            data = [
                dump_model(item)
                for item in review_data.advancement_candidates
                if item.pool_type == normalized_pool_type
            ]
            return ApiResponse(code=200, msg="获取连板候选成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.get("/divergence-consensus", response_model=ApiResponse)
    async def divergence_consensus(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            data = [dump_model(item) for item in service.review(date or None, refresh=refresh).divergence_consensus]
            return ApiResponse(code=200, msg="获取分歧转一致识别成功", data=data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    @router.get("/kline/{code}", response_model=ApiResponse)
    async def stock_kline(
            code: str,
            date: str = Query(default=""),
            limit: int = Query(default=120, ge=1, le=240),
            refresh: bool = Query(default=False),
            name: str = Query(default=""),
            period: str = Query(default="day"),
    ):
        try:
            data = service.stock_kline(code, date or None, limit=limit, refresh=refresh, name=name, period=period)
            return ApiResponse(code=200, msg="获取个股K线成功", data=dump_model(data))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except MarketReviewUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))

    return router
