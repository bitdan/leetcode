from fastapi import APIRouter, Query

from market_review.route_helpers import ApiResponse, dump_model, market_http_exception


def create_kline_router(container) -> APIRouter:
    router = APIRouter()
    service = container.market_review_service

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
        except Exception as exc:
            raise market_http_exception(exc)

    return router

