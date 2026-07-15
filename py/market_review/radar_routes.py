from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from market_review.route_helpers import ApiResponse, dump_model, market_http_exception


def create_radar_router(container) -> APIRouter:
    router = APIRouter()
    service = container.market_review_service

    @router.get("/radar", response_model=ApiResponse)
    async def radar(
            date: str = Query(default=""),
            refresh: bool = Query(default=False),
            sector_limit: int = Query(default=20, ge=1, le=60),
            candidate_limit: int = Query(default=80, ge=1, le=200),
    ):
        try:
            data = await run_in_threadpool(
                service.market_radar,
                date or None,
                refresh,
                sector_limit,
                candidate_limit,
            )
            return ApiResponse(code=200, msg="获取市场雷达成功", data=dump_model(data))
        except Exception as exc:
            raise market_http_exception(exc)

    @router.get("/radar/sectors/{sector_name}/stocks", response_model=ApiResponse)
    async def radar_sector_stocks(
            sector_name: str,
            date: str = Query(default=""),
            refresh: bool = Query(default=False),
            limit: int = Query(default=300, ge=1, le=500),
    ):
        try:
            stocks = await run_in_threadpool(
                service.radar_sector_stocks,
                    sector_name,
                    date or None,
                    refresh,
                    limit,
            )
            data = [dump_model(item) for item in stocks]
            return ApiResponse(code=200, msg="获取板块成分股成功", data=data)
        except Exception as exc:
            raise market_http_exception(exc)

    return router
