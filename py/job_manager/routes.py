from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from auth.schemas import ApiResponse
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from market_review.sync_daily import DailyKlineSyncer


class JobRunRequest(BaseModel):
    params: Dict[str, Any] = Field(default_factory=dict)


class JobRunRecord(BaseModel):
    run_id: str
    job_id: str
    job_name: str
    status: str
    params: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    total_codes: int = 0
    success_count: int = 0
    failed_count: int = 0
    saved_rows: int = 0
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


JOB_DEFINITIONS = [
    {
        "id": "market_daily_kline_sync",
        "name": "全市场日K同步",
        "description": "同步 A 股日 K 到 market_stock_kline_daily，支持单日或日期范围。",
        "params": [
            {"key": "date", "label": "单日", "type": "date", "placeholder": "YYYY-MM-DD"},
            {"key": "start", "label": "开始日期", "type": "date", "placeholder": "YYYY-MM-DD"},
            {"key": "end", "label": "结束日期", "type": "date", "placeholder": "YYYY-MM-DD"},
            {"key": "codes", "label": "股票代码", "type": "text", "placeholder": "000001 600519，可留空同步全A"},
            {"key": "limit_codes", "label": "限制数量", "type": "number", "placeholder": "测试用，可留空"},
            {"key": "adjust", "label": "复权", "type": "select", "options": ["qfq", "hfq", ""]},
            {"key": "sleep", "label": "请求间隔秒", "type": "number", "placeholder": "0.05"},
        ],
    }
]


def create_router(container) -> APIRouter:
    router = APIRouter(prefix="/api/v1/jobs", tags=["任务管理"])
    runs: Dict[str, JobRunRecord] = {}
    lock = Lock()

    @router.get("", response_model=ApiResponse)
    async def list_jobs():
        return ApiResponse(code=200, msg="获取任务列表成功", data=JOB_DEFINITIONS)

    @router.get("/runs", response_model=ApiResponse)
    async def list_runs(limit: int = 50):
        with lock:
            data = sorted(runs.values(), key=lambda item: item.created_at, reverse=True)[:max(1, min(limit, 200))]
            return ApiResponse(code=200, msg="获取运行记录成功", data=[item.model_dump() for item in data])

    @router.get("/runs/{run_id}", response_model=ApiResponse)
    async def get_run(run_id: str):
        with lock:
            record = runs.get(run_id)
            if not record:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运行记录不存在")
            return ApiResponse(code=200, msg="获取运行记录成功", data=record.model_dump())

    @router.post("/{job_id}/run", response_model=ApiResponse)
    async def run_job(job_id: str, request: JobRunRequest, background_tasks: BackgroundTasks):
        definition = next((item for item in JOB_DEFINITIONS if item["id"] == job_id), None)
        if not definition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

        params = normalize_params(request.params)
        validate_market_daily_params(params)
        run_id = uuid4().hex
        record = JobRunRecord(
            run_id=run_id,
            job_id=job_id,
            job_name=definition["name"],
            status="queued",
            params=params,
            created_at=now_text(),
        )
        with lock:
            runs[run_id] = record
        background_tasks.add_task(execute_market_daily_sync, container, runs, lock, run_id)
        return ApiResponse(code=200, msg="任务已提交", data=record.model_dump())

    return router


def execute_market_daily_sync(container, runs: Dict[str, JobRunRecord], lock: Lock, run_id: str) -> None:
    with lock:
        record = runs[run_id]
        record.status = "running"
        record.started_at = now_text()

    try:
        store = container.market_review_service.store
        if not store or not store.is_available():
            raise RuntimeError("PostgreSQL market review store unavailable")

        params = record.params
        date = params.get("date", "")
        start = date or params.get("start", "")
        end = date or params.get("end", "")
        codes = split_codes(params.get("codes", ""))
        limit_codes = int(params.get("limit_codes") or 0)
        adjust = params.get("adjust", "qfq")
        sleep = float(params.get("sleep") or 0.05)

        result = DailyKlineSyncer(store, adjust=adjust, sleep_seconds=sleep).sync_range(
            start,
            end,
            codes=codes,
            limit_codes=limit_codes,
        )
        with lock:
            record = runs[run_id]
            record.status = "success"
            record.total_codes = result.total_codes
            record.success_count = result.success_count
            record.failed_count = result.failed_count
            record.saved_rows = result.saved_rows
            record.message = "同步完成"
            record.finished_at = now_text()
    except Exception as exc:
        with lock:
            record = runs[run_id]
            record.status = "failed"
            record.message = str(exc)
            record.finished_at = now_text()


def normalize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
        if value != "":
            normalized[key] = value
    normalized.setdefault("adjust", "qfq")
    normalized.setdefault("sleep", 0.05)
    return normalized


def validate_market_daily_params(params: Dict[str, Any]) -> None:
    has_date = bool(params.get("date"))
    has_range = bool(params.get("start")) and bool(params.get("end"))
    if not has_date and not has_range:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请填写单日，或同时填写开始/结束日期")
    if has_date and (params.get("start") or params.get("end")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="单日和范围日期不要同时填写")
    for key in ("date", "start", "end"):
        value = params.get(key)
        if value:
            parse_date(value)
    if has_range and parse_date(params["start"]) > parse_date(params["end"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始日期不能晚于结束日期")


def split_codes(value: str) -> List[str]:
    return [item for item in str(value or "").replace(",", " ").split() if item]


def parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"日期格式错误: {value}") from exc


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")
