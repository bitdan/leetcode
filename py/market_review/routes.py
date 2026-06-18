from fastapi import APIRouter

from market_review.kline_routes import create_kline_router
from market_review.radar_routes import create_radar_router
from market_review.review_routes import create_review_router


def create_router(container) -> APIRouter:
    router = APIRouter()
    prefix = "/api/v1/market-review"
    tags = ["市场复盘"]
    router.include_router(create_review_router(container), prefix=prefix, tags=tags)
    router.include_router(create_radar_router(container), prefix=prefix, tags=tags)
    router.include_router(create_kline_router(container), prefix=prefix, tags=tags)
    return router
