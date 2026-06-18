from auth.schemas import ApiResponse
from fastapi import HTTPException, status
from market_review.service import MarketReviewUnavailable


def dump_model(model) -> dict:
    return model.model_dump(mode="json") if hasattr(model, "model_dump") else model.dict()


def public_error(exc: Exception) -> str:
    return str(exc).replace("AKShare", "行情服务").replace("akshare", "行情服务")


def market_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, MarketReviewUnavailable):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=public_error(exc))
    raise exc


__all__ = ["ApiResponse", "dump_model", "market_http_exception"]

