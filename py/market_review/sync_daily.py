import argparse
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional

from core.settings import get_settings
from market_review.schemas import StockKlineBar
from market_review.service import MarketReviewService
from market_review.store import MarketReviewStore, MarketReviewStoreUnavailable

logger = logging.getLogger(__name__)


@dataclass
class StockIdentity:
    code: str
    name: str


@dataclass
class SyncResult:
    total_codes: int
    success_count: int = 0
    failed_count: int = 0
    saved_rows: int = 0


class DailyKlineSyncer:
    def __init__(self, store: MarketReviewStore, adjust: str = "qfq", sleep_seconds: float = 0.05):
        self.store = store
        self.adjust = adjust
        self.sleep_seconds = max(sleep_seconds, 0)
        self.service = MarketReviewService(store)
        self.ak = self.service._load_akshare()

    def sync_range(
            self,
            start_date: str,
            end_date: str,
            codes: Optional[Iterable[str]] = None,
            limit_codes: int = 0,
    ) -> SyncResult:
        start = normalize_date(start_date)
        end = normalize_date(end_date)
        if start > end:
            raise ValueError("start date must be before or equal to end date")

        stocks = self._load_stock_universe(codes)
        if limit_codes > 0:
            stocks = stocks[:limit_codes]
        result = SyncResult(total_codes=len(stocks))

        for index, stock in enumerate(stocks, start=1):
            try:
                bars = self._fetch_daily_bars(stock.code, start, end)
                if not bars:
                    logger.info("[%s/%s] %s %s no rows", index, len(stocks), stock.code, stock.name)
                    continue
                result.saved_rows += self.store.upsert_stock_kline_daily(stock.code, stock.name, bars)
                result.success_count += 1
                logger.info(
                    "[%s/%s] %s %s saved %s rows",
                    index,
                    len(stocks),
                    stock.code,
                    stock.name,
                    len(bars),
                )
            except Exception as exc:
                result.failed_count += 1
                logger.warning("[%s/%s] %s %s failed: %s", index, len(stocks), stock.code, stock.name, exc)
            if self.sleep_seconds:
                time.sleep(self.sleep_seconds)

        return result

    def _load_stock_universe(self, codes: Optional[Iterable[str]]) -> List[StockIdentity]:
        requested = {normalize_code(item) for item in codes or [] if item}
        rows = self._fetch_stock_list()
        stocks: List[StockIdentity] = []
        for row in rows:
            code = normalize_code(pick(row, "代码", "code", "证券代码"))
            if not code or not re.fullmatch(r"\d{6}", code):
                continue
            if requested and code not in requested:
                continue
            name = str(pick(row, "名称", "name", "证券简称") or "").strip()
            stocks.append(StockIdentity(code=code, name=name))
        stocks.sort(key=lambda item: item.code)
        return stocks

    def _fetch_stock_list(self) -> list[dict]:
        attempts = []
        if hasattr(self.ak, "stock_info_a_code_name"):
            attempts.append(lambda: self.ak.stock_info_a_code_name())
        if hasattr(self.ak, "stock_zh_a_spot_em"):
            attempts.append(lambda: self.ak.stock_zh_a_spot_em())
        errors = []
        for fetcher in attempts:
            try:
                frame = fetcher()
                rows = frame.to_dict(orient="records")
                if rows:
                    return rows
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError(f"股票列表获取失败: {errors}")

    def _fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> List[StockKlineBar]:
        frame = self.ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust=self.adjust,
            timeout=15,
        )
        rows = frame.to_dict(orient="records")
        return self.service._rows_to_kline_bars(rows, self.service._row_to_kline_bar, "eastmoney-batch", code)


def pick(row: dict, *keys: str):
    for key in keys:
        if key in row:
            return row[key]
    return None


def normalize_code(value) -> str:
    text = str(value or "").strip()
    match = re.search(r"(\d{6})", text)
    return match.group(1) if match else ""


def normalize_date(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="同步全市场日 K 数据到 market_stock_kline_daily")
    parser.add_argument("--date", help="同步单个交易日，格式 YYYY-MM-DD")
    parser.add_argument("--start", help="范围开始日期，格式 YYYY-MM-DD")
    parser.add_argument("--end", help="范围结束日期，格式 YYYY-MM-DD")
    parser.add_argument("--codes", nargs="*", help="只同步指定股票代码，默认同步全 A")
    parser.add_argument("--limit-codes", type=int, default=0, help="限制同步股票数量，便于小批量测试")
    parser.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"], help="复权方式，默认 qfq")
    parser.add_argument("--sleep", type=float, default=0.05, help="单只股票请求后的休眠秒数")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    if args.date:
        start = end = args.date
    elif args.start and args.end:
        start, end = args.start, args.end
    else:
        raise SystemExit("请提供 --date 或同时提供 --start/--end")

    store = MarketReviewStore(get_settings().postgres_dsn)
    if not store.is_available():
        raise SystemExit(store.unavailable_reason or "PostgreSQL store unavailable")

    try:
        result = DailyKlineSyncer(store, adjust=args.adjust, sleep_seconds=args.sleep).sync_range(
            start,
            end,
            codes=args.codes,
            limit_codes=args.limit_codes,
        )
    except MarketReviewStoreUnavailable as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        store.close()

    logger.info(
        "同步完成: total=%s success=%s failed=%s rows=%s",
        result.total_codes,
        result.success_count,
        result.failed_count,
        result.saved_rows,
    )


if __name__ == "__main__":
    main()
