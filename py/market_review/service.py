import asyncio
import logging
import math
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from time import monotonic
from typing import Any, Dict, List, Optional, Tuple

from market_review.schemas import (
    CandidateStock,
    DivergenceConsensusSignal,
    IntradayTradingSignal,
    LimitUpStock,
    MarketReviewData,
    SectorStrength,
    StockKlineBar,
    StockKlineSnapshot,
    StockKlineSummary,
)
from market_review.store import MarketReviewStore, MarketReviewStoreUnavailable

logger = logging.getLogger(__name__)


class MarketReviewUnavailable(RuntimeError):
    pass


SNAPSHOT_INTRADAY = "intraday"
SNAPSHOT_FINAL = "final"
SNAPSHOT_LEGACY_SUCCESS = "success"
FINAL_SNAPSHOT_TIME = time(15, 10)


class MarketReviewService:
    def __init__(self, store: Optional[MarketReviewStore] = None, cache_ttl_seconds: int = 300):
        self.store = store
        self.cache_ttl_seconds = cache_ttl_seconds
        self._limit_up_cache: Dict[str, Tuple[float, List[LimitUpStock]]] = {}
        self._review_cache: Dict[str, Tuple[float, MarketReviewData, str]] = {}
        self._final_snapshot_task: Optional[asyncio.Task] = None

    def review(self, trading_date: Optional[str] = None, refresh: bool = False) -> MarketReviewData:
        normalized_date = self._normalize_date(trading_date)
        snapshot_status = self._snapshot_status(normalized_date)
        if not refresh:
            cached = self._get_cached_review(normalized_date, snapshot_status)
            if cached is not None:
                return cached
            if snapshot_status == SNAPSHOT_FINAL:
                stored_status = self._get_stored_status(normalized_date)
                if self._stored_snapshot_can_be_used(normalized_date, stored_status):
                    stored = self._get_stored_review(normalized_date)
                    if stored is not None:
                        self._prime_caches(normalized_date, stored, snapshot_status)
                        return stored
        try:
            data = self._build_review(normalized_date, refresh=True if snapshot_status == SNAPSHOT_FINAL else refresh)
        except Exception as exc:
            self._mark_failed(normalized_date, str(exc))
            raise
        self._save_review(data, snapshot_status)
        self._prime_caches(normalized_date, data, snapshot_status)
        return data

    def _build_review(self, normalized_date: str, refresh: bool = False) -> MarketReviewData:
        pool = self.limit_up_pool(normalized_date, refresh=refresh)
        sectors = self.sector_strength(normalized_date, pool)
        advancement_candidates = self.advancement_candidates(normalized_date, pool, sectors)
        signals = self.divergence_consensus(normalized_date, pool, sectors)
        return MarketReviewData(
            date=normalized_date,
            limit_up_pool=pool,
            sector_strength=sectors,
            advancement_candidates=advancement_candidates,
            candidates_2_to_3=[item for item in advancement_candidates if item.pool_type == "2_to_3"],
            divergence_consensus=signals,
        )

    def limit_up_pool(self, trading_date: Optional[str] = None, refresh: bool = False) -> List[LimitUpStock]:
        normalized_date = self._normalize_date(trading_date)
        cached = None if refresh else self._get_cached(self._limit_up_cache, normalized_date)
        if cached is not None:
            return cached
        ak = self._load_akshare()
        try:
            frame = ak.stock_zt_pool_em(date=normalized_date.replace("-", ""))
        except Exception as exc:
            raise MarketReviewUnavailable("涨停池数据暂不可用，请稍后重试") from exc

        rows = frame.to_dict(orient="records")
        stocks = [self._row_to_limit_up_stock(row) for row in rows]
        result = sorted(stocks, key=lambda item: (-item.consecutive_boards, item.first_limit_time or "999999"))
        self._limit_up_cache[normalized_date] = (monotonic(), result)
        return result

    def sector_strength(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
    ) -> List[SectorStrength]:
        stocks = pool if pool is not None else self.limit_up_pool(trading_date)
        grouped: Dict[str, List[LimitUpStock]] = defaultdict(list)
        for stock in stocks:
            grouped[stock.industry or "未分类"].append(stock)

        sectors: List[SectorStrength] = []
        for industry, items in grouped.items():
            advanced_count = sum(1 for item in items if item.consecutive_boards >= 2)
            open_count = sum(item.open_count or 0 for item in items)
            total_seal = sum(item.seal_amount or 0 for item in items)
            total_amount = sum(item.amount or 0 for item in items)
            max_boards = max((item.consecutive_boards for item in items), default=1)
            core = sorted(items, key=lambda item: (-item.consecutive_boards, -item.board_quality_score))[:3]
            score = (
                    len(items) * 16
                    + advanced_count * 12
                    + max_boards * 8
                    + self._money_score(total_seal, 8)
                    - min(open_count * 2.5, 18)
            )
            risks = []
            if open_count >= max(2, len(items)):
                risks.append("炸板偏多")
            if len(items) == 1:
                risks.append("板块跟随不足")
            sectors.append(SectorStrength(
                industry=industry,
                limit_up_count=len(items),
                advanced_count=advanced_count,
                max_consecutive_boards=max_boards,
                total_seal_amount=round(total_seal, 2),
                total_amount=round(total_amount, 2),
                open_count=open_count,
                core_stocks=[item.name for item in core],
                strength_score=round(max(score, 0), 2),
                risk_tags=risks,
            ))
        return sorted(sectors, key=lambda item: item.strength_score, reverse=True)

    def candidates_by_pool_type(
            self,
            pool_type: str,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            sectors: Optional[List[SectorStrength]] = None,
    ) -> List[CandidateStock]:
        normalized = self._normalize_pool_type(pool_type)
        return [
            item
            for item in self.advancement_candidates(trading_date, pool, sectors)
            if item.pool_type == normalized
        ]

    def candidates_2_to_3(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            sectors: Optional[List[SectorStrength]] = None,
    ) -> List[CandidateStock]:
        return self.candidates_by_pool_type("2_to_3", trading_date, pool, sectors)

    def advancement_candidates(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            sectors: Optional[List[SectorStrength]] = None,
    ) -> List[CandidateStock]:
        stocks = pool if pool is not None else self.limit_up_pool(trading_date)
        sector_list = sectors if sectors is not None else self.sector_strength(trading_date, stocks)
        sector_map = {item.industry: item for item in sector_list}
        candidates: List[CandidateStock] = []

        for stock in stocks:
            if stock.consecutive_boards < 1:
                continue
            target_boards = stock.consecutive_boards + 1
            pool_type = f"{stock.consecutive_boards}_to_{target_boards}"
            sector = sector_map.get(stock.industry or "未分类")
            ladder_bonus = min(stock.consecutive_boards * 4, 16)
            score = stock.board_quality_score + ((sector.strength_score if sector else 0) * 0.35) + ladder_bonus
            reasons = []
            risks = list(stock.tags)
            if sector and sector.limit_up_count >= 3:
                reasons.append("板块涨停家数靠前")
            if sector and sector.advanced_count >= 2:
                reasons.append("板块有连板梯队")
            if stock.first_limit_time and stock.first_limit_time <= "103000":
                reasons.append("封板时间较早")
            if (stock.open_count or 0) == 0:
                reasons.append("未炸板")
            if stock.turnover_rate and 3 <= stock.turnover_rate <= 18:
                reasons.append("换手相对充分")
            if stock.seal_amount and stock.amount and stock.seal_amount / max(stock.amount, 1) < 0.03:
                risks.append("封单额相对成交额偏弱")
            if stock.first_limit_time and stock.first_limit_time >= "143000":
                risks.append("尾盘封板")
            level = "高关注" if score >= 82 and len(risks) <= 1 else "观察"
            if score < 55 or len(risks) >= 3:
                level = "剔除"
            candidates.append(CandidateStock(
                stock=stock,
                sector=sector,
                pool_type=pool_type,
                target_boards=target_boards,
                candidate_score=round(score, 2),
                level=level,
                reasons=reasons or [f"{stock.consecutive_boards}连板入池"],
                risks=risks,
            ))
        return sorted(candidates, key=lambda item: item.candidate_score, reverse=True)

    def divergence_consensus(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            sectors: Optional[List[SectorStrength]] = None,
    ) -> List[DivergenceConsensusSignal]:
        stocks = pool if pool is not None else self.limit_up_pool(trading_date)
        sector_list = sectors if sectors is not None else self.sector_strength(trading_date, stocks)
        sector_map = {item.industry: item for item in sector_list}
        signals: List[DivergenceConsensusSignal] = []

        for stock in stocks:
            sector = sector_map.get(stock.industry or "未分类")
            open_count = stock.open_count or 0
            reasons = []
            risks = []
            score = 0.0
            phase = "一致"
            if open_count > 0:
                phase = "分歧转一致"
                score += min(open_count * 8, 24)
                reasons.append("盘中炸板后回封")
            if stock.last_limit_time and stock.first_limit_time and stock.last_limit_time > stock.first_limit_time:
                score += 10
                reasons.append("最后封板晚于首次封板")
            if sector and sector.limit_up_count >= 3:
                score += 24
                reasons.append("同板块涨停家数形成回流")
            if sector and sector.advanced_count >= 2:
                score += 16
                reasons.append("板块连板梯队仍在")
            if stock.seal_amount:
                score += self._money_score(stock.seal_amount, 12)
            if open_count >= 4:
                risks.append("分歧过大")
            if stock.first_limit_time and stock.first_limit_time >= "143000":
                risks.append("尾盘一致性待确认")
            if phase == "分歧转一致" or score >= 45:
                signals.append(DivergenceConsensusSignal(
                    code=stock.code,
                    name=stock.name,
                    industry=stock.industry,
                    phase=phase,
                    signal_score=round(score, 2),
                    reasons=reasons or ["封板稳定"],
                    risks=risks,
                ))
        return sorted(signals, key=lambda item: item.signal_score, reverse=True)

    @staticmethod
    def _load_akshare():
        try:
            import akshare as ak
        except ImportError as exc:
            raise MarketReviewUnavailable("行情服务依赖未就绪，请检查后端运行环境") from exc
        return ak

    def _get_stored_review(self, normalized_date: str) -> Optional[MarketReviewData]:
        if not self.store or not self.store.is_available():
            return None
        try:
            statuses = [SNAPSHOT_FINAL, SNAPSHOT_LEGACY_SUCCESS]
            return self.store.get_review(normalized_date, statuses=statuses)
        except MarketReviewStoreUnavailable as exc:
            logger.warning("Market review snapshot load skipped for %s: %s", normalized_date, exc)
            return None

    def _save_review(self, data: MarketReviewData, status: str) -> None:
        if not self.store or not self.store.is_available():
            return
        try:
            self.store.save_review(data, status=status)
        except MarketReviewStoreUnavailable as exc:
            logger.warning("Market review snapshot save skipped for %s: %s", data.date, exc)
            return

    def _get_stored_status(self, normalized_date: str) -> Optional[dict]:
        if not self.store or not self.store.is_available():
            return None
        try:
            return self.store.status(normalized_date)
        except MarketReviewStoreUnavailable as exc:
            logger.warning("Market review status lookup skipped for %s: %s", normalized_date, exc)
            return None

    def _mark_failed(self, normalized_date: str, message: str) -> None:
        if not self.store or not self.store.is_available():
            return
        try:
            self.store.mark_failed(normalized_date, message)
        except Exception:
            logger.warning("Market review failure status save skipped for %s", normalized_date, exc_info=True)
            return

    def status(self, trading_date: Optional[str] = None) -> Optional[dict]:
        normalized_date = self._normalize_date(trading_date)
        expected_status = self._snapshot_status(normalized_date)
        if not self.store:
            return {"date": normalized_date, "status": "store_missing", "expected_status": expected_status}
        if not self.store.is_available():
            return {
                "date": normalized_date,
                "status": "store_unavailable",
                "expected_status": expected_status,
                "error_message": self.store.unavailable_reason or "市场复盘存储不可用",
            }
        try:
            stored = self._get_stored_status(normalized_date)
            if stored:
                if stored.get("source"):
                    stored["source"] = "行情服务"
                stored["expected_status"] = expected_status
                stored["is_final"] = self._stored_snapshot_can_be_used(normalized_date, stored)
                return stored
            return {"date": normalized_date, "status": "missing", "expected_status": expected_status}
        except MarketReviewStoreUnavailable as exc:
            logger.warning("Market review status lookup skipped for %s: %s", normalized_date, exc)
            return {
                "date": normalized_date,
                "status": "store_unavailable",
                "expected_status": expected_status,
                "error_message": str(exc),
            }

    def stock_kline(
            self,
            code: str,
            trading_date: Optional[str] = None,
            limit: int = 120,
            refresh: bool = False,
            name: str = "",
            period: str = "day",
    ) -> StockKlineSnapshot:
        normalized_code = self._normalize_code(code)
        normalized_date = self._normalize_date(trading_date)
        normalized_period = self._normalize_kline_period(period)
        normalized_limit = max(1, min(limit, 240))
        bars: List[StockKlineBar] = []

        if normalized_period == "five_day":
            bars = self._fetch_stock_kline_five_day(normalized_code, normalized_date)
        elif normalized_period == "day":
            if not refresh and self.store and self.store.is_available():
                try:
                    bars = self.store.get_stock_kline_daily(normalized_code, normalized_limit, normalized_date)
                except MarketReviewStoreUnavailable as exc:
                    logger.warning("Market review daily kline load skipped for %s: %s", normalized_code, exc)

            if not bars:
                bars = self._fetch_stock_kline_daily(normalized_code, normalized_date, normalized_limit)
                if self.store and self.store.is_available():
                    try:
                        self.store.save_stock_kline_daily(normalized_code, name, bars)
                    except MarketReviewStoreUnavailable as exc:
                        logger.warning("Market review daily kline save skipped for %s: %s", normalized_code, exc)
        elif normalized_period == "week":
            bars = self._fetch_stock_kline_daily(normalized_code, normalized_date, normalized_limit, period="weekly")
        elif normalized_period == "year":
            daily_bars = self._fetch_stock_kline_daily(
                normalized_code,
                normalized_date,
                max(normalized_limit * 260, 260),
            )
            bars = self._aggregate_kline_bars(daily_bars, "year")[-normalized_limit:]
        else:
            if not refresh and self.store and self.store.is_available():
                try:
                    bars = self.store.get_stock_kline_intraday(normalized_code, normalized_period, normalized_date)
                except MarketReviewStoreUnavailable as exc:
                    logger.warning("Market review intraday kline load skipped for %s/%s: %s",
                                   normalized_code, normalized_period, exc)

            if not bars:
                fetch_period = "60" if normalized_period == "120" else normalized_period
                bars = self._fetch_stock_kline_intraday(normalized_code, normalized_date, fetch_period)
                if normalized_period == "120":
                    bars = self._aggregate_intraday_bars(bars, 120)
                if self.store and self.store.is_available():
                    try:
                        self.store.save_stock_kline_intraday(
                            normalized_code, name, normalized_period, normalized_date, bars
                        )
                    except MarketReviewStoreUnavailable as exc:
                        logger.warning("Market review intraday kline save skipped for %s/%s: %s",
                                       normalized_code, normalized_period, exc)

        display_name = name.strip()
        if not display_name and self.store and self.store.is_available():
            try:
                display_name = self.store.get_stock_name(normalized_code)
            except MarketReviewStoreUnavailable as exc:
                logger.warning("Market review stock name load skipped for %s: %s", normalized_code, exc)

        enriched_bars = self._apply_kline_indicators(bars)
        intraday_signals = self._build_intraday_signals(normalized_code, normalized_date, normalized_period, enriched_bars)
        return StockKlineSnapshot(
            code=normalized_code,
            name=display_name,
            date=normalized_date,
            period=normalized_period,
            bars=enriched_bars,
            summary=self._build_kline_summary(enriched_bars),
            technical_tags=self._build_kline_tags(enriched_bars, normalized_period),
            intraday_signals=intraday_signals,
        )

    def _prime_caches(self, normalized_date: str, data: MarketReviewData, status: str = SNAPSHOT_FINAL) -> None:
        self._review_cache[normalized_date] = (monotonic(), data, status)
        self._limit_up_cache[normalized_date] = (monotonic(), data.limit_up_pool)

    def _get_cached(self, cache: Dict[str, Tuple[float, Any]], key: str) -> Optional[Any]:
        cached = cache.get(key)
        if not cached:
            return None
        created_at, value = cached
        if monotonic() - created_at <= self.cache_ttl_seconds:
            return value
        cache.pop(key, None)
        return None

    def _get_cached_review(self, normalized_date: str, expected_status: str) -> Optional[MarketReviewData]:
        cached = self._review_cache.get(normalized_date)
        if not cached:
            return None
        created_at, value, status = cached
        if monotonic() - created_at > self.cache_ttl_seconds:
            self._review_cache.pop(normalized_date, None)
            return None
        if expected_status == SNAPSHOT_FINAL and status != SNAPSHOT_FINAL:
            return None
        return value

    def _snapshot_status(self, normalized_date: str) -> str:
        trade_date = datetime.strptime(normalized_date, "%Y-%m-%d").date()
        now = self._now()
        if trade_date == now.date() and now.time() < FINAL_SNAPSHOT_TIME:
            return SNAPSHOT_INTRADAY
        return SNAPSHOT_FINAL

    def _stored_snapshot_can_be_used(self, normalized_date: str, stored_status: Optional[dict]) -> bool:
        if not stored_status:
            return False
        status = stored_status.get("status")
        if status == SNAPSHOT_FINAL:
            return True
        if status != SNAPSHOT_LEGACY_SUCCESS:
            return False
        trade_date = datetime.strptime(normalized_date, "%Y-%m-%d").date()
        if trade_date != self._now().date():
            return True
        generated_at = self._parse_datetime(stored_status.get("generated_at"))
        return bool(generated_at and generated_at.time() >= FINAL_SNAPSHOT_TIME)

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    async def start_final_snapshot_scheduler(self) -> None:
        if self._final_snapshot_task and not self._final_snapshot_task.done():
            return
        self._final_snapshot_task = asyncio.create_task(self._run_final_snapshot_scheduler())

    async def stop_final_snapshot_scheduler(self) -> None:
        if not self._final_snapshot_task:
            return
        self._final_snapshot_task.cancel()
        try:
            await self._final_snapshot_task
        except asyncio.CancelledError:
            pass
        self._final_snapshot_task = None

    async def _run_final_snapshot_scheduler(self) -> None:
        while True:
            await asyncio.sleep(self._seconds_until_next_final_snapshot())
            today = self._now().strftime("%Y-%m-%d")
            try:
                await asyncio.to_thread(self.review, today, True)
                logger.info("Market review final snapshot refreshed for %s", today)
            except Exception:
                logger.warning("Market review final snapshot refresh failed for %s", today, exc_info=True)

    def _seconds_until_next_final_snapshot(self) -> float:
        now = self._now()
        next_run = datetime.combine(now.date(), FINAL_SNAPSHOT_TIME)
        if now >= next_run:
            next_run = next_run + timedelta(days=1)
        return max(1.0, (next_run - now).total_seconds())

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    @staticmethod
    def _normalize_pool_type(value: str) -> str:
        text = value.strip().lower().replace("-", "_")
        match = re.fullmatch(r"(\d+)_?to_?(\d+)", text)
        if not match:
            match = re.fullmatch(r"(\d+)_?进_?(\d+)", text)
        if not match:
            raise ValueError("候选池类型应为 1_to_2、2_to_3 等格式")
        source = int(match.group(1))
        target = int(match.group(2))
        if target != source + 1:
            raise ValueError("候选池类型仅支持连续晋级，例如 1_to_2、2_to_3")
        return f"{source}_to_{target}"

    @staticmethod
    def _normalize_code(value: str) -> str:
        text = re.sub(r"\D", "", (value or "").strip())
        if len(text) != 6:
            raise ValueError("股票代码应为 6 位数字")
        return text

    @staticmethod
    def _normalize_kline_period(value: str) -> str:
        text = (value or "day").strip().lower()
        mapping = {
            "minute": "1",
            "time": "1",
            "fs": "1",
            "分时": "1",
            "1": "1",
            "1m": "1",
            "five_day": "five_day",
            "5d": "five_day",
            "五日k": "five_day",
            "五日K": "five_day",
            "d": "day",
            "day": "day",
            "daily": "day",
            "week": "week",
            "weekly": "week",
            "w": "week",
            "周k": "week",
            "周K": "week",
            "year": "year",
            "yearly": "year",
            "y": "year",
            "年k": "year",
            "年K": "year",
            "5": "5",
            "5m": "5",
            "15": "15",
            "15m": "15",
            "30": "30",
            "30m": "30",
            "60": "60",
            "60m": "60",
            "120": "120",
            "120m": "120",
        }
        if text not in mapping:
            raise ValueError("K线周期仅支持 分时、五日K、day、week、year、120、60、30、15、5")
        return mapping[text]

    @staticmethod
    def _normalize_date(value: Optional[str]) -> str:
        if not value:
            return date.today().strftime("%Y-%m-%d")
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError("日期格式应为 YYYY-MM-DD 或 YYYYMMDD")

    def _row_to_limit_up_stock(self, row: Dict[str, Any]) -> LimitUpStock:
        stock = LimitUpStock(
            code=str(self._pick(row, "代码", "股票代码", default="")).zfill(6),
            name=str(self._pick(row, "名称", "股票简称", default="")),
            industry=str(self._pick(row, "所属行业", "行业", default="未分类") or "未分类"),
            latest_price=self._to_float(self._pick(row, "最新价", "收盘价")),
            change_percent=self._to_float(self._pick(row, "涨跌幅")),
            turnover_rate=self._to_float(self._pick(row, "换手率")),
            amount=self._to_float(self._pick(row, "成交额")),
            circulating_market_value=self._to_float(self._pick(row, "流通市值")),
            seal_amount=self._to_float(self._pick(row, "封板资金", "封单资金", "封单额")),
            first_limit_time=self._normalize_time(self._pick(row, "首次封板时间", "首次涨停时间")),
            last_limit_time=self._normalize_time(self._pick(row, "最后封板时间", "最后涨停时间")),
            open_count=self._to_int(self._pick(row, "炸板次数", "开板次数")),
            consecutive_boards=self._extract_boards(row),
            limit_up_stat=str(self._pick(row, "涨停统计", default="")),
            raw_payload=self._json_safe(row),
        )
        stock.board_quality_score = self._quality_score(stock)
        stock.tags = self._risk_tags(stock)
        return stock

    def _quality_score(self, stock: LimitUpStock) -> float:
        score = 45.0 + min(stock.consecutive_boards * 6, 24)
        if stock.first_limit_time:
            if stock.first_limit_time <= "100000":
                score += 16
            elif stock.first_limit_time <= "113000":
                score += 10
            elif stock.first_limit_time >= "143000":
                score -= 10
        score -= min((stock.open_count or 0) * 6, 24)
        if stock.seal_amount:
            score += self._money_score(stock.seal_amount, 12)
        if stock.turnover_rate:
            if 3 <= stock.turnover_rate <= 18:
                score += 8
            elif stock.turnover_rate > 30:
                score -= 8
        return round(max(min(score, 100), 0), 2)

    @staticmethod
    def _risk_tags(stock: LimitUpStock) -> List[str]:
        tags = []
        if (stock.open_count or 0) >= 3:
            tags.append("炸板偏多")
        if stock.first_limit_time and stock.first_limit_time >= "143000":
            tags.append("尾盘封板")
        if stock.turnover_rate and stock.turnover_rate > 30:
            tags.append("换手过高")
        if not stock.industry or stock.industry == "未分类":
            tags.append("板块未知")
        return tags

    @staticmethod
    def _extract_boards(row: Dict[str, Any]) -> int:
        direct = MarketReviewService._to_int(MarketReviewService._pick(row, "连板数", "连续涨停天数"))
        if direct:
            return max(direct, 1)
        stat = str(MarketReviewService._pick(row, "涨停统计", default=""))
        match = re.search(r"(\d+)\s*/\s*(\d+)", stat)
        if match:
            return max(int(match.group(1)), 1)
        match = re.search(r"(\d+)\s*连", stat)
        if match:
            return max(int(match.group(1)), 1)
        return 1

    @staticmethod
    def _json_safe(row: Dict[str, Any]) -> Dict[str, Any]:
        payload = {}
        for key, value in row.items():
            if value is None:
                payload[str(key)] = None
                continue
            try:
                if isinstance(value, float) and math.isnan(value):
                    payload[str(key)] = None
                elif isinstance(value, (datetime, date)):
                    payload[str(key)] = value.isoformat()
                elif hasattr(value, "item"):
                    item = value.item()
                    payload[str(key)] = item.isoformat() if hasattr(item, "isoformat") else item
                elif hasattr(value, "isoformat"):
                    payload[str(key)] = value.isoformat()
                else:
                    payload[str(key)] = value
            except Exception:
                payload[str(key)] = str(value)
        return payload

    @staticmethod
    def _normalize_time(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return ""
        digits = re.sub(r"\D", "", text)
        if len(digits) >= 6:
            return digits[:6]
        if len(digits) == 4:
            return f"{digits}00"
        return digits

    @staticmethod
    def _pick(row: Dict[str, Any], *names: str, default: Any = None) -> Any:
        for name in names:
            if name in row:
                return row[name]
        return default

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(str(value).replace(",", "").replace("%", ""))
            if math.isnan(number):
                return None
            return round(number, 4)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            text = str(value).strip()
            if not text or text.lower() == "nan":
                return None
            return int(float(text))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _money_score(value: float, cap: float) -> float:
        if value <= 0:
            return 0
        return min(math.log10(value + 1) * 1.8, cap)

    def _fetch_stock_kline_daily(
            self,
            code: str,
            normalized_date: str,
            limit: int,
            period: str = "daily",
    ) -> List[StockKlineBar]:
        ak = self._load_akshare()
        lookback_days = max(limit * 3, 90)
        if period == "weekly":
            lookback_days = max(limit * 10, 365)
        start_date = (datetime.strptime(normalized_date, "%Y-%m-%d") - timedelta(days=lookback_days)).strftime("%Y%m%d")
        end_date = normalized_date.replace("-", "")
        attempts = [
            ("eastmoney-qfq", lambda: ak.stock_zh_a_hist(
                symbol=code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
                timeout=15,
            )),
            ("eastmoney-raw", lambda: ak.stock_zh_a_hist(
                symbol=code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="",
                timeout=15,
            )),
        ]
        if period == "daily" and hasattr(ak, "stock_zh_a_daily"):
            attempts.extend([
                ("sina-qfq", lambda: ak.stock_zh_a_daily(
                    symbol=self._market_symbol(code),
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )),
                ("sina-raw", lambda: ak.stock_zh_a_daily(
                    symbol=self._market_symbol(code),
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                )),
            ])
        if hasattr(ak, "stock_zh_a_hist_tx"):
            attempts.extend([
                ("tencent-qfq", lambda: ak.stock_zh_a_hist_tx(
                    symbol=self._tx_symbol(code),
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                    timeout=15,
                )),
                ("tencent-raw", lambda: ak.stock_zh_a_hist_tx(
                    symbol=self._tx_symbol(code),
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                    timeout=15,
                )),
            ])

        errors: List[str] = []
        for source, fetcher in attempts:
            try:
                frame = fetcher()
                rows = frame.to_dict(orient="records")
                bars = self._rows_to_kline_bars(rows, self._row_to_kline_bar, source, code)
                if bars:
                    return bars[-limit:]
                errors.append(f"{source}: empty")
            except Exception as exc:
                logger.warning("AKShare daily kline fetch failed for %s via %s: %s", code, source, exc)
                errors.append(f"{source}: {exc}")
        logger.warning("AKShare daily kline unavailable for %s, attempts=%s", code, errors)
        raise MarketReviewUnavailable("个股 K 线数据暂不可用，请稍后重试")

    def _fetch_stock_kline_intraday(self, code: str, normalized_date: str, period: str) -> List[StockKlineBar]:
        ak = self._load_akshare()
        start_date = f"{normalized_date} 09:30:00"
        end_date = f"{normalized_date} 15:00:00"
        attempts = [
            ("eastmoney-min-qfq", "qfq"),
            ("eastmoney-min-raw", ""),
        ]
        errors: List[str] = []
        for source, adjust in attempts:
            try:
                frame = ak.stock_zh_a_hist_min_em(
                    symbol=code,
                    start_date=start_date,
                    end_date=end_date,
                    period=period,
                    adjust=adjust,
                )
                rows = frame.to_dict(orient="records")
                bars = self._rows_to_kline_bars(rows, self._row_to_intraday_kline_bar, source, code)
                if bars:
                    return bars
                errors.append(f"{source}: empty")
            except Exception as exc:
                logger.warning("AKShare intraday kline fetch failed for %s/%s via %s: %s",
                               code, period, source, exc)
                errors.append(f"{source}: {exc}")
        logger.warning("AKShare intraday kline unavailable for %s/%s, attempts=%s", code, period, errors)
        raise MarketReviewUnavailable("分钟K线数据暂不可用，请稍后重试")

    def _fetch_stock_kline_five_day(self, code: str, normalized_date: str) -> List[StockKlineBar]:
        daily_bars = self._fetch_stock_kline_daily(code, normalized_date, 10)
        trade_dates = [item.trade_date for item in daily_bars if item.trade_date <= normalized_date][-5:]
        if not trade_dates:
            trade_dates = [normalized_date]
        result: List[StockKlineBar] = []
        errors: List[str] = []
        for trade_date in trade_dates:
            try:
                result.extend(self._fetch_stock_kline_intraday(code, trade_date, "1"))
            except MarketReviewUnavailable as exc:
                errors.append(f"{trade_date}: {exc}")
        if result:
            return result
        logger.warning("AKShare five-day timeline unavailable for %s, attempts=%s", code, errors)
        raise MarketReviewUnavailable("五日分时数据暂不可用，请稍后重试")

    def _aggregate_intraday_bars(self, bars: List[StockKlineBar], minutes: int) -> List[StockKlineBar]:
        groups: Dict[str, List[StockKlineBar]] = defaultdict(list)
        for item in bars:
            bar_time = datetime.strptime(item.trade_date, "%Y-%m-%d %H:%M:%S")
            minute_of_day = bar_time.hour * 60 + bar_time.minute
            bucket_minute = (minute_of_day // minutes) * minutes
            bucket_time = bar_time.replace(hour=bucket_minute // 60, minute=bucket_minute % 60, second=0)
            groups[bucket_time.strftime("%Y-%m-%d %H:%M:%S")].append(item)
        return [self._merge_kline_group(key, items) for key, items in sorted(groups.items()) if items]

    def _aggregate_kline_bars(self, bars: List[StockKlineBar], period: str) -> List[StockKlineBar]:
        groups: Dict[str, List[StockKlineBar]] = defaultdict(list)
        for item in bars:
            trade_date = datetime.strptime(item.trade_date, "%Y-%m-%d")
            if period == "year":
                key = f"{trade_date.year}-12-31"
            else:
                key = item.trade_date
            groups[key].append(item)
        return [self._merge_kline_group(key, items) for key, items in sorted(groups.items()) if items]

    @staticmethod
    def _merge_kline_group(key: str, items: List[StockKlineBar]) -> StockKlineBar:
        ordered = sorted(items, key=lambda item: item.trade_date)
        first = ordered[0]
        last = ordered[-1]
        high = max(item.high_price for item in ordered)
        low = min(item.low_price for item in ordered)
        amount = sum(item.amount or 0 for item in ordered)
        volume = sum(item.volume or 0 for item in ordered)
        change_amount = round(last.close_price - first.open_price, 4)
        change_percent = round((change_amount / first.open_price) * 100, 4) if first.open_price else None
        return StockKlineBar(
            trade_date=key,
            open_price=first.open_price,
            close_price=last.close_price,
            high_price=high,
            low_price=low,
            volume=volume,
            amount=amount,
            change_amount=change_amount,
            change_percent=change_percent,
        )

    @staticmethod
    def _tx_symbol(code: str) -> str:
        return f"sh{code}" if code.startswith(("5", "6", "9")) else f"sz{code}"

    @staticmethod
    def _market_symbol(code: str) -> str:
        if code.startswith(("4", "8")):
            return f"bj{code}"
        if code.startswith(("5", "6", "9")):
            return f"sh{code}"
        return f"sz{code}"

    @staticmethod
    def _rows_to_kline_bars(rows: List[Dict[str, Any]], converter, source: str, code: str) -> List[StockKlineBar]:
        bars: List[StockKlineBar] = []
        for row in rows:
            try:
                bar = converter(row)
            except Exception as exc:
                logger.warning("AKShare kline row skipped for %s via %s: %s; row=%s", code, source, exc, row)
                continue
            if bar.open_price <= 0 or bar.close_price <= 0 or bar.high_price <= 0 or bar.low_price <= 0:
                logger.warning("AKShare kline row skipped for %s via %s: non-positive price row=%s", code, source, row)
                continue
            bars.append(bar)
        return bars

    def _row_to_kline_bar(self, row: Dict[str, Any]) -> StockKlineBar:
        trade_date = self._normalize_hist_date(self._pick(row, "日期", "trade_date", "date"))
        return StockKlineBar(
            trade_date=trade_date,
            open_price=self._to_float(self._pick(row, "开盘", "open")) or 0,
            close_price=self._to_float(self._pick(row, "收盘", "close")) or 0,
            high_price=self._to_float(self._pick(row, "最高", "high")) or 0,
            low_price=self._to_float(self._pick(row, "最低", "low")) or 0,
            volume=self._to_float(self._pick(row, "成交量", "volume")) or 0,
            amount=self._to_float(self._pick(row, "成交额", "amount")) or 0,
            amplitude=self._to_float(self._pick(row, "振幅", "amplitude")),
            change_amount=self._to_float(self._pick(row, "涨跌额", "change_amount")),
            change_percent=self._to_float(self._pick(row, "涨跌幅", "change_percent")),
            turnover_rate=self._to_float(self._pick(row, "换手率", "turnover_rate")),
        )

    def _row_to_intraday_kline_bar(self, row: Dict[str, Any]) -> StockKlineBar:
        bar_time = self._normalize_intraday_datetime(self._pick(row, "时间", "日期", "datetime", "time"))
        return StockKlineBar(
            trade_date=bar_time,
            open_price=self._to_float(self._pick(row, "开盘", "open")) or 0,
            close_price=self._to_float(self._pick(row, "收盘", "close")) or 0,
            high_price=self._to_float(self._pick(row, "最高", "high")) or 0,
            low_price=self._to_float(self._pick(row, "最低", "low")) or 0,
            volume=self._to_float(self._pick(row, "成交量", "volume")) or 0,
            amount=self._to_float(self._pick(row, "成交额", "amount")) or 0,
            amplitude=self._to_float(self._pick(row, "振幅", "amplitude")),
            change_amount=self._to_float(self._pick(row, "涨跌额", "change_amount")),
            change_percent=self._to_float(self._pick(row, "涨跌幅", "change_percent")),
            turnover_rate=self._to_float(self._pick(row, "换手率", "turnover_rate")),
        )

    @staticmethod
    def _normalize_hist_date(value: Any) -> str:
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError("无法解析 K 线日期")

    @staticmethod
    def _normalize_intraday_datetime(value: Any) -> str:
        text = str(value).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        raise ValueError("无法解析分时K线时间")

    def _apply_kline_indicators(self, bars: List[StockKlineBar]) -> List[StockKlineBar]:
        closes = [item.close_price for item in bars]
        volumes = [item.volume or 0 for item in bars]
        ema12_values = self._ema(closes, 12)
        ema26_values = self._ema(closes, 26)
        dif_values = [round(ema12 - ema26, 4) for ema12, ema26 in zip(ema12_values, ema26_values)]
        dea_values = self._ema(dif_values, 9)
        for index, item in enumerate(bars):
            item.ma5 = self._moving_average(closes, index, 5)
            item.ma10 = self._moving_average(closes, index, 10)
            item.ma20 = self._moving_average(closes, index, 20)
            item.ma30 = self._moving_average(closes, index, 30)
            item.ma60 = self._moving_average(closes, index, 60)
            item.dif = round(dif_values[index], 4)
            item.dea = round(dea_values[index], 4)
            item.macd = round((item.dif - item.dea) * 2, 4)
            if item.change_percent is None and index > 0 and closes[index - 1] > 0:
                item.change_percent = round(((item.close_price - closes[index - 1]) / closes[index - 1]) * 100, 4)
            if item.change_amount is None and index > 0:
                item.change_amount = round(item.close_price - closes[index - 1], 4)
        return bars

    @staticmethod
    def _moving_average(values: List[float], index: int, window: int) -> Optional[float]:
        if index + 1 < window:
            return None
        segment = values[index - window + 1:index + 1]
        return round(sum(segment) / window, 4)

    @staticmethod
    def _ema(values: List[float], period: int) -> List[float]:
        if not values:
            return []
        result = [values[0]]
        multiplier = 2 / (period + 1)
        for value in values[1:]:
            result.append((value - result[-1]) * multiplier + result[-1])
        return result

    def _build_kline_summary(self, bars: List[StockKlineBar]) -> Optional[StockKlineSummary]:
        if not bars:
            return None
        latest = bars[-1]
        return StockKlineSummary(
            latest_price=latest.close_price,
            change_amount=latest.change_amount,
            change_percent=latest.change_percent,
            open_price=latest.open_price,
            high_price=latest.high_price,
            low_price=latest.low_price,
            volume=latest.volume,
            amount=latest.amount,
            turnover_rate=latest.turnover_rate,
            ma5=latest.ma5,
            ma10=latest.ma10,
            ma20=latest.ma20,
            ma30=latest.ma30,
            ma60=latest.ma60,
        )

    def _build_kline_tags(self, bars: List[StockKlineBar], period: str = "day") -> List[str]:
        if len(bars) < 2:
            return []
        latest = bars[-1]
        previous = bars[-2]
        closes = [item.close_price for item in bars]
        volumes = [item.volume or 0 for item in bars]
        tags: List[str] = []
        recent_high_20 = max(closes[-20:]) if len(closes) >= 20 else max(closes)
        if latest.close_price >= recent_high_20:
            tags.append("近20日新高")
        if latest.ma5 and latest.ma10 and latest.ma20 and latest.close_price >= latest.ma5 >= latest.ma10 >= latest.ma20:
            tags.append("均线多头")
        elif latest.ma20 and latest.close_price >= latest.ma20:
            tags.append("站上20日线")
        else:
            tags.append("20日线下")
        avg_volume_5 = sum(volumes[-5:]) / min(len(volumes), 5)
        if avg_volume_5 > 0:
            if latest.volume >= avg_volume_5 * 1.8:
                tags.append("放量")
            elif latest.volume <= avg_volume_5 * 0.7:
                tags.append("缩量")
        if latest.macd is not None and previous.macd is not None:
            if latest.dif is not None and latest.dea is not None and previous.dif is not None and previous.dea is not None:
                if latest.dif >= latest.dea and previous.dif < previous.dea:
                    tags.append("MACD金叉")
                elif latest.dif <= latest.dea and previous.dif > previous.dea:
                    tags.append("MACD死叉")
        if latest.close_price > latest.open_price:
            tags.append("阳线")
        elif latest.close_price < latest.open_price:
            tags.append("阴线")
        if period != "day":
            if latest.close_price >= latest.high_price * 0.997:
                tags.append("收在高位")
            if latest.low_price <= min(item.low_price for item in bars[:max(1, min(6, len(bars)))]):
                tags.append("日内试探低点")
        return tags[:6]

    def _build_intraday_signals(self, code: str, normalized_date: str, period: str,
                                bars: List[StockKlineBar]) -> List[IntradayTradingSignal]:
        if period == "day" or len(bars) < 3:
            return []
        previous_close = self._get_previous_close(code, normalized_date)
        if previous_close <= 0:
            return []
        limit_up_price = self._compute_limit_up_price(code, previous_close)
        intraday_low = min(item.low_price for item in bars)
        latest = bars[-1]
        signals: List[IntradayTradingSignal] = []

        retreated = intraday_low <= previous_close * 0.985
        recovered = latest.close_price >= previous_close * 1.01
        late_strength = any(item.close_price >= previous_close * 1.015 for item in bars[-max(2, len(bars) // 4):])
        if retreated and recovered and late_strength:
            observed_bar = max(bars[-max(2, len(bars) // 4):], key=lambda item: item.close_price)
            signals.append(IntradayTradingSignal(
                signal_type="weak_to_strong",
                title="弱转强",
                phase="分时回拉",
                signal_score=round(min(((latest.close_price / previous_close) - 1) * 1000, 92), 2),
                observed_at=observed_bar.trade_date,
                reasons=[
                    "盘中回撤后重新站上昨收",
                    "尾段收盘强于开盘",
                ],
                risks=["若次日低开则信号衰减"] if latest.close_price < latest.high_price * 0.995 else [],
            ))

        broke_limit = any(item.high_price >= limit_up_price * 0.999 for item in bars)
        reseal_candidates = [
            item for item in bars
            if item.high_price >= limit_up_price * 0.999 and item.close_price >= limit_up_price * 0.997
        ]
        if broke_limit and reseal_candidates:
            last_reseal = reseal_candidates[-1]
            last_reseal.is_reseal_bar = True
            last_reseal.is_breakout_bar = True
            signals.append(IntradayTradingSignal(
                signal_type="reseal",
                title="回封确认",
                phase="炸板回封",
                signal_score=round(min(78 + len(reseal_candidates) * 4, 96), 2),
                observed_at=last_reseal.trade_date,
                reasons=[
                    "盘中触及涨停价后再次收在涨停附近",
                    f"{period}分钟级别出现回封K线",
                ],
                risks=["回封次数过多需防反复"] if len(reseal_candidates) >= 3 else [],
            ))

        return signals[:3]

    def _get_previous_close(self, code: str, normalized_date: str) -> float:
        try:
            daily_bars = self._fetch_stock_kline_daily(code, normalized_date, 3)
        except MarketReviewUnavailable:
            return 0
        if len(daily_bars) < 2:
            return 0
        target = normalized_date
        previous_bars = [item for item in daily_bars if item.trade_date < target]
        if not previous_bars:
            return daily_bars[-2].close_price
        return previous_bars[-1].close_price

    @staticmethod
    def _compute_limit_up_price(code: str, previous_close: float) -> float:
        if code.startswith(("300", "301", "688")):
            multiplier = 1.2
        else:
            multiplier = 1.1
        return round(previous_close * multiplier, 2)
