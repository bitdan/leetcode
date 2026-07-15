from fastapi import APIRouter, BackgroundTasks, Query
from starlette.concurrency import run_in_threadpool

from market_review.route_helpers import ApiResponse, dump_model, market_http_exception


def create_review_router(container) -> APIRouter:
    router = APIRouter()
    service = container.market_review_service

    def dump_stock(item) -> dict:
        return {
            "code": item.code,
            "name": item.name,
            "industry": item.industry,
            "latest_price": item.latest_price,
            "change_percent": item.change_percent,
            "turnover_rate": item.turnover_rate,
            "amount": item.amount,
            "circulating_market_value": item.circulating_market_value,
            "seal_amount": item.seal_amount,
            "first_limit_time": item.first_limit_time,
            "last_limit_time": item.last_limit_time,
            "open_count": item.open_count,
            "consecutive_boards": item.consecutive_boards,
            "limit_up_stat": item.limit_up_stat,
        }

    def dump_sector(item) -> dict:
        return {
            "industry": item.industry,
            "limit_up_count": item.limit_up_count,
            "advanced_count": item.advanced_count,
            "max_consecutive_boards": item.max_consecutive_boards,
            "total_seal_amount": item.total_seal_amount,
            "total_amount": item.total_amount,
            "open_count": item.open_count,
            "core_stocks": item.core_stocks,
        }

    def dump_review(data) -> dict:
        payload = {
            "date": data.date,
            "limit_up_pool": [dump_stock(item) for item in data.limit_up_pool],
            "sector_strength": [dump_sector(item) for item in data.sector_strength],
        }
        snapshot_status = service.snapshot_status(data.date)
        payload["snapshot_status"] = snapshot_status
        payload["is_final"] = service.is_final_snapshot(data.date)
        return payload

    @router.get("", response_model=ApiResponse)
    async def review(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            data = await run_in_threadpool(service.review, date or None, refresh)
            return ApiResponse(code=200, msg="获取市场复盘成功", data=dump_review(data))
        except Exception as exc:
            raise market_http_exception(exc)

    @router.post("/warmup", response_model=ApiResponse)
    async def warmup(
            background_tasks: BackgroundTasks,
            date: str = Query(default=""),
            refresh: bool = Query(default=False),
    ):
        try:
            normalized_date = service.normalize_date(date or None)
            background_tasks.add_task(service.review, normalized_date, refresh)
            return ApiResponse(code=200, msg="市场复盘预热任务已提交", data={"date": normalized_date})
        except Exception as exc:
            raise market_http_exception(exc)

    @router.post("/refresh", response_model=ApiResponse)
    async def refresh(date: str = Query(default="")):
        try:
            data = await run_in_threadpool(service.review, date or None, True)
            return ApiResponse(code=200, msg="市场复盘快照已刷新", data=dump_review(data))
        except Exception as exc:
            raise market_http_exception(exc)

    @router.get("/status", response_model=ApiResponse)
    async def status_view(date: str = Query(default="")):
        try:
            normalized_date = service.normalize_date(date or None)
            data = service.status(normalized_date) or {"date": normalized_date, "status": "missing"}
            return ApiResponse(code=200, msg="获取市场复盘状态成功", data=data)
        except Exception as exc:
            raise market_http_exception(exc)

    @router.get("/limit-up-pool", response_model=ApiResponse)
    async def limit_up_pool(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            review_data = await run_in_threadpool(service.review, date or None, refresh)
            data = [dump_stock(item) for item in review_data.limit_up_pool]
            return ApiResponse(code=200, msg="获取涨停池成功", data=data)
        except Exception as exc:
            raise market_http_exception(exc)

    @router.get("/sector-strength", response_model=ApiResponse)
    async def sector_strength(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            review_data = await run_in_threadpool(service.review, date or None, refresh)
            data = [dump_sector(item) for item in review_data.sector_strength]
            return ApiResponse(code=200, msg="获取板块强度成功", data=data)
        except Exception as exc:
            raise market_http_exception(exc)

    @router.get("/candidates/2-to-3", response_model=ApiResponse)
    async def candidates_2_to_3(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            review_data = await run_in_threadpool(service.review, date or None, refresh)
            data = [dump_model(item) for item in review_data.candidates_2_to_3]
            return ApiResponse(code=200, msg="获取 2进3 候选成功", data=data)
        except Exception as exc:
            raise market_http_exception(exc)

    @router.get("/candidates/advancement", response_model=ApiResponse)
    async def advancement_candidates(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            review_data = await run_in_threadpool(service.review, date or None, refresh)
            data = [dump_model(item) for item in review_data.advancement_candidates]
            return ApiResponse(code=200, msg="获取连板晋级候选成功", data=data)
        except Exception as exc:
            raise market_http_exception(exc)

    @router.get("/candidates/{pool_type}", response_model=ApiResponse)
    async def candidates_by_pool_type(
            pool_type: str,
            date: str = Query(default=""),
            refresh: bool = Query(default=False),
    ):
        try:
            review_data = await run_in_threadpool(service.review, date or None, refresh)
            normalized_pool_type = service.normalize_pool_type(pool_type)
            data = [
                dump_model(item)
                for item in review_data.advancement_candidates
                if item.pool_type == normalized_pool_type
            ]
            return ApiResponse(code=200, msg="获取连板候选成功", data=data)
        except Exception as exc:
            raise market_http_exception(exc)

    @router.get("/divergence-consensus", response_model=ApiResponse)
    async def divergence_consensus(date: str = Query(default=""), refresh: bool = Query(default=False)):
        try:
            review_data = await run_in_threadpool(service.review, date or None, refresh)
            data = [dump_model(item) for item in review_data.divergence_consensus]
            return ApiResponse(code=200, msg="获取分歧转一致识别成功", data=data)
        except Exception as exc:
            raise market_http_exception(exc)

    return router
