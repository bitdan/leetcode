import asyncio
import logging
import math
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import date, datetime, time, timedelta
from time import monotonic
from typing import Any, Dict, List, Optional, Tuple

from market_review.schemas import (
    CandidateStock,
    DivergenceConsensusSignal,
    IntradayTradingSignal,
    LimitUpStock,
    MarketEnvironment,
    MarketRadarCandidate,
    MarketRadarData,
    MarketRadarSector,
    MarketRadarSectorStock,
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
    KLINE_SOURCE_TIMEOUT_SECONDS = 8
    KLINE_TOTAL_TIMEOUT_SECONDS = 32

    def __init__(self, store: Optional[MarketReviewStore] = None, cache_ttl_seconds: int = 300):
        self.store = store
        self.cache_ttl_seconds = cache_ttl_seconds
        self._limit_up_cache: Dict[str, Tuple[float, List[LimitUpStock]]] = {}
        self._review_cache: Dict[str, Tuple[float, MarketReviewData, str]] = {}
        self._environment_cache: Dict[str, Tuple[float, MarketEnvironment]] = {}
        self._radar_cache: Dict[str, Tuple[float, MarketRadarData, str]] = {}
        self._final_snapshot_task: Optional[asyncio.Task] = None
        self._kline_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="market-review-kline")

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

    def market_radar(
            self,
            trading_date: Optional[str] = None,
            refresh: bool = False,
            sector_limit: int = 20,
            candidate_limit: int = 80,
    ) -> MarketRadarData:
        normalized_date = self._normalize_date(trading_date)
        snapshot_status = self._snapshot_status(normalized_date)
        if not refresh:
            cached = self._get_cached_radar(normalized_date, snapshot_status)
            if cached is not None:
                return cached
            if snapshot_status == SNAPSHOT_FINAL and self.store and self.store.is_available():
                try:
                    stored = self.store.get_radar(normalized_date)
                    if stored is not None:
                        review_data = self.review(normalized_date, refresh=False)
                        stored.market_environment = review_data.market_environment
                        stored.generated_at = self._now().isoformat()
                        self._radar_cache[normalized_date] = (monotonic(), stored, snapshot_status)
                        return stored
                except MarketReviewStoreUnavailable as exc:
                    logger.warning("Market radar snapshot load skipped for %s: %s", normalized_date, exc)

        review_data = self.review(normalized_date, refresh=refresh)
        radar = self._build_market_radar(
            normalized_date,
            review_data,
            sector_limit=max(1, min(sector_limit, 60)),
            candidate_limit=max(1, min(candidate_limit, 200)),
        )
        if self.store and self.store.is_available():
            try:
                self.store.save_radar(radar)
            except MarketReviewStoreUnavailable as exc:
                logger.warning("Market radar snapshot save skipped for %s: %s", normalized_date, exc)
        self._radar_cache[normalized_date] = (monotonic(), radar, snapshot_status)
        return radar

    def radar_sector_stocks(
            self,
            sector_name: str,
            trading_date: Optional[str] = None,
            refresh: bool = False,
            limit: int = 300,
    ) -> List[MarketRadarSectorStock]:
        normalized_date = self._normalize_date(trading_date)
        normalized_sector = self._normalize_sector_name(sector_name)
        if not normalized_sector:
            raise ValueError("板块名称不能为空")
        radar = self.market_radar(normalized_date, refresh=refresh)
        sector_score = next(
            (item.heat_score for item in radar.sectors if item.sector_name == normalized_sector),
            0,
        )
        normalized_limit = max(1, min(limit, 500))
        pool = self.review(normalized_date, refresh=False).limit_up_pool
        limit_up_by_code = {item.code: item for item in pool}

        if normalized_date == self._now().strftime("%Y-%m-%d"):
            try:
                rows = self._fetch_market_spot_rows()
                stocks = [
                    self._build_sector_stock(row, normalized_sector, sector_score, limit_up_by_code)
                    for row in rows
                ]
                result = [item for item in stocks if item is not None]
                self._enrich_sector_stocks_with_trend(result, normalized_date)
                result.sort(key=lambda item: (item.stock_score, item.amount or 0), reverse=True)
                return result[:normalized_limit]
            except Exception as exc:
                logger.warning("Market radar sector stock spot fetch skipped for %s/%s: %s",
                               normalized_date, normalized_sector, exc)

        fallback = [
            MarketRadarSectorStock(
                code=item.code,
                name=item.name,
                industry=item.industry,
                latest_price=item.latest_price,
                change_percent=item.change_percent,
                turnover_rate=item.turnover_rate,
                amount=item.amount,
                sector_heat_score=round(sector_score, 2),
                stock_score=round(self._clamp_score(item.board_quality_score * 0.62 + sector_score * 0.38), 2),
                reasons=["历史/快照降级，仅展示该板块涨停池标的"],
                risks=list(item.tags),
                tags=["涨停确认", f"{item.consecutive_boards}板"],
            )
            for item in pool
            if (item.industry or "未分类") == normalized_sector
        ]
        self._enrich_sector_stocks_with_trend(fallback, normalized_date)
        fallback.sort(key=lambda item: (item.stock_score, item.amount or 0), reverse=True)
        return fallback[:normalized_limit]

    def _build_review(self, normalized_date: str, refresh: bool = False) -> MarketReviewData:
        pool = self.limit_up_pool(normalized_date, refresh=refresh)
        environment = self.market_environment(normalized_date, pool, refresh=refresh)
        sectors = self.sector_strength(normalized_date, pool, environment)
        advancement_candidates = self.advancement_candidates(normalized_date, pool, sectors, environment)
        signals = self.divergence_consensus(normalized_date, pool, sectors, environment)
        return MarketReviewData(
            date=normalized_date,
            limit_up_pool=pool,
            sector_strength=sectors,
            advancement_candidates=advancement_candidates,
            candidates_2_to_3=[item for item in advancement_candidates if item.pool_type == "2_to_3"],
            divergence_consensus=signals,
            market_environment=environment,
        )

    def _build_market_radar(
            self,
            normalized_date: str,
            review_data: MarketReviewData,
            sector_limit: int,
            candidate_limit: int,
    ) -> MarketRadarData:
        pool = review_data.limit_up_pool
        environment = review_data.market_environment or self.market_environment(normalized_date, pool)
        spot_rows: List[dict] = []
        source_note = ""
        if normalized_date == self._now().strftime("%Y-%m-%d"):
            try:
                spot_rows = self._fetch_market_spot_rows()
            except Exception as exc:
                source_note = "全市场快照不可用，已退化为涨停池雷达"
                logger.warning("Market radar spot fetch skipped for %s: %s", normalized_date, exc)
        else:
            source_note = "历史日期暂无全市场快照，已退化为涨停池雷达"

        if spot_rows:
            sectors, candidates = self._radar_from_spot_rows(
                spot_rows,
                pool,
                sector_limit=sector_limit,
                candidate_limit=candidate_limit,
            )
        else:
            sectors, candidates = self._radar_from_limit_up_pool(
                pool,
                review_data.sector_strength,
                candidate_limit=candidate_limit,
                source_note=source_note,
            )
        return MarketRadarData(
            date=normalized_date,
            market_environment=environment,
            sectors=sectors[:sector_limit],
            candidates=candidates[:candidate_limit],
            generated_at=self._now().isoformat(),
        )

    def _fetch_market_spot_rows(self) -> List[dict]:
        ak = self._load_akshare()
        if not hasattr(ak, "stock_zh_a_spot_em"):
            raise MarketReviewUnavailable("行情服务缺少 A 股实时快照接口")
        frame = ak.stock_zh_a_spot_em()
        rows = frame.to_dict(orient="records")
        if not rows:
            raise MarketReviewUnavailable("A 股实时快照为空")
        return rows

    def _radar_from_spot_rows(
            self,
            rows: List[dict],
            pool: List[LimitUpStock],
            sector_limit: int,
            candidate_limit: int,
    ) -> Tuple[List[MarketRadarSector], List[MarketRadarCandidate]]:
        limit_up_by_code = {item.code: item for item in pool}
        grouped: Dict[str, List[dict]] = defaultdict(list)
        for row in rows:
            code = self._normalize_code(str(self._pick(row, "代码", "code", "股票代码", default="")))
            name = str(self._pick(row, "名称", "name", "股票简称", default="") or "").strip()
            if not code or not name or self._is_excluded_stock_name(name):
                continue
            industry = self._normalize_sector_name(self._pick(row, "所属行业", "行业", "industry", default=""))
            if not industry:
                industry = "未分类"
            grouped[industry].append(row)

        sectors: List[MarketRadarSector] = []
        for industry, items in grouped.items():
            sector = self._build_spot_sector(industry, items, limit_up_by_code)
            if sector.stock_count < 2 and sector.limit_up_count == 0:
                continue
            sectors.append(sector)
        sectors.sort(key=lambda item: item.heat_score, reverse=True)
        sector_score_map = {item.sector_name: item.heat_score for item in sectors[:sector_limit]}

        candidates: List[MarketRadarCandidate] = []
        for row in rows:
            candidate = self._build_spot_candidate(row, sector_score_map, limit_up_by_code)
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(key=lambda item: item.candidate_score, reverse=True)
        return sectors, candidates[:candidate_limit]

    def _build_spot_sector(
            self,
            industry: str,
            rows: List[dict],
            limit_up_by_code: Dict[str, LimitUpStock],
    ) -> MarketRadarSector:
        stock_count = len(rows)
        rise_count = 0
        strong_count = 0
        total_amount = 0.0
        weighted_change = 0.0
        limit_up_count = 0
        ranked_rows = []
        for row in rows:
            code = self._normalize_code(str(self._pick(row, "代码", "code", "股票代码", default="")))
            name = str(self._pick(row, "名称", "name", "股票简称", default="") or "").strip()
            change = self._to_float(self._pick(row, "涨跌幅", "change_percent")) or 0.0
            amount = self._to_float(self._pick(row, "成交额", "amount")) or 0.0
            total_amount += amount
            weighted_change += change * max(amount, 1.0)
            if change > 0:
                rise_count += 1
            if change >= 5:
                strong_count += 1
            if code in limit_up_by_code or change >= self._limit_up_percent_threshold(row):
                limit_up_count += 1
            ranked_rows.append((change, amount, name))

        change_percent = weighted_change / max(total_amount, 1.0)
        rise_ratio = rise_count / max(stock_count, 1)
        strong_ratio = strong_count / max(stock_count, 1)
        momentum_score = self._ratio_score(
            change_percent,
            [(5.0, 96), (3.0, 84), (1.5, 70), (0.5, 56), (0.0, 42), (-2.0, 24), (-100.0, 10)],
        )
        breadth_score = self._ratio_score(
            rise_ratio,
            [(0.82, 96), (0.70, 84), (0.58, 70), (0.48, 56), (0.35, 36), (0.0, 18)],
        )
        liquidity_score = self._amount_activity_score(total_amount)
        pulse_score = self._ratio_score(
            strong_ratio,
            [(0.16, 96), (0.10, 84), (0.06, 70), (0.03, 54), (0.0, 34)],
        )
        limit_score = self._limit_up_diffusion_score(limit_up_count)
        heat_score = self._clamp_score(
            momentum_score * 0.28
            + breadth_score * 0.24
            + liquidity_score * 0.18
            + pulse_score * 0.18
            + limit_score * 0.12
        )
        core_stocks = [
            name for _, _, name in sorted(ranked_rows, key=lambda item: (item[0], item[1]), reverse=True)[:4]
            if name
        ]
        reasons = []
        risks = []
        if change_percent >= 1.5:
            reasons.append("板块涨幅领先")
        if rise_ratio >= 0.6:
            reasons.append("板块内上涨家数占优")
        if strong_count >= 3:
            reasons.append("强势股扩散")
        if limit_up_count > 0:
            reasons.append("有涨停情绪确认")
        if stock_count < 4:
            risks.append("样本数量偏少")
        if rise_ratio < 0.45:
            risks.append("内部一致性不足")
        if total_amount <= 0:
            risks.append("成交额缺失")
        return MarketRadarSector(
            sector_name=industry,
            heat_score=round(heat_score, 2),
            momentum_score=round(momentum_score, 2),
            liquidity_score=round(liquidity_score, 2),
            breadth_score=round(breadth_score, 2),
            limit_up_count=limit_up_count,
            strong_stock_count=strong_count,
            stock_count=stock_count,
            rise_count=rise_count,
            change_percent=round(change_percent, 4),
            total_amount=round(total_amount, 2),
            core_stocks=core_stocks,
            reasons=reasons or ["板块进入雷达观察"],
            risks=risks,
        )

    def _build_spot_candidate(
            self,
            row: dict,
            sector_score_map: Dict[str, float],
            limit_up_by_code: Dict[str, LimitUpStock],
    ) -> Optional[MarketRadarCandidate]:
        code = self._normalize_code(str(self._pick(row, "代码", "code", "股票代码", default="")))
        name = str(self._pick(row, "名称", "name", "股票简称", default="") or "").strip()
        if not code or not name or self._is_excluded_stock_name(name):
            return None
        industry = self._normalize_sector_name(self._pick(row, "所属行业", "行业", "industry", default="")) or "未分类"
        sector_heat = sector_score_map.get(industry, 0)
        if sector_heat <= 0:
            return None

        change = self._to_float(self._pick(row, "涨跌幅", "change_percent"))
        amount = self._to_float(self._pick(row, "成交额", "amount"))
        turnover = self._to_float(self._pick(row, "换手率", "turnover_rate"))
        latest_price = self._to_float(self._pick(row, "最新价", "收盘价", "close", "price"))
        if amount is not None and amount < 20000000 and code not in limit_up_by_code:
            return None
        if change is None or change < -3:
            return None

        momentum_score = self._ratio_score(
            change,
            [(9.5, 96), (6.0, 86), (3.0, 74), (1.0, 58), (0.0, 42), (-3.0, 24), (-100.0, 10)],
        )
        amount_score = self._amount_activity_score(amount or 0)
        turnover_score = self._band_score(turnover or 0, 1.0, 18.0, 35.0) if turnover is not None else 42
        limit_up_bonus = 10 if code in limit_up_by_code else 0
        score = self._clamp_score(
            sector_heat * 0.38
            + momentum_score * 0.28
            + amount_score * 0.18
            + turnover_score * 0.10
            + limit_up_bonus
        )
        if score < 55:
            return None

        reasons = ["所属板块热度靠前"]
        risks = []
        tags = []
        if change is not None and change >= 3:
            reasons.append("个股涨幅强于市场")
            tags.append("强势上涨")
        if amount is not None and amount >= 100000000:
            reasons.append("成交额达到活跃区间")
            tags.append("资金活跃")
        if turnover is not None and 2 <= turnover <= 18:
            reasons.append("换手处于可跟踪区间")
        if code in limit_up_by_code:
            tags.append("涨停确认")
            limit_stock = limit_up_by_code[code]
            if limit_stock.tags:
                risks.extend(limit_stock.tags)
        if turnover is not None and turnover > 30:
            risks.append("换手过高")
        if change is not None and change >= 9:
            risks.append("短线涨幅已高")
        if industry == "未分类":
            risks.append("板块归属缺失")

        return MarketRadarCandidate(
            code=code,
            name=name,
            industry=industry,
            latest_price=latest_price,
            change_percent=change,
            turnover_rate=turnover,
            amount=amount,
            candidate_score=round(score, 2),
            sector_heat_score=round(sector_heat, 2),
            signal_type="limit_up" if code in limit_up_by_code else "sector_strength",
            reasons=list(dict.fromkeys(reasons)),
            risks=list(dict.fromkeys(risks)),
            tags=list(dict.fromkeys(tags)),
        )

    def _build_sector_stock(
            self,
            row: dict,
            target_sector: str,
            sector_heat: float,
            limit_up_by_code: Dict[str, LimitUpStock],
    ) -> Optional[MarketRadarSectorStock]:
        code = self._normalize_code(str(self._pick(row, "代码", "code", "股票代码", default="")))
        name = str(self._pick(row, "名称", "name", "股票简称", default="") or "").strip()
        if not code or not name or self._is_excluded_stock_name(name):
            return None
        industry = self._normalize_sector_name(self._pick(row, "所属行业", "行业", "industry", default="")) or "未分类"
        if industry != target_sector:
            return None

        change = self._to_float(self._pick(row, "涨跌幅", "change_percent"))
        amount = self._to_float(self._pick(row, "成交额", "amount"))
        turnover = self._to_float(self._pick(row, "换手率", "turnover_rate"))
        latest_price = self._to_float(self._pick(row, "最新价", "收盘价", "close", "price"))
        momentum_score = self._ratio_score(
            change,
            [(9.5, 96), (6.0, 86), (3.0, 74), (1.0, 58), (0.0, 42), (-3.0, 24), (-100.0, 10)],
        )
        amount_score = self._amount_activity_score(amount or 0)
        turnover_score = self._band_score(turnover or 0, 1.0, 18.0, 35.0) if turnover is not None else 42
        limit_bonus = 10 if code in limit_up_by_code else 0
        score = self._clamp_score(
            sector_heat * 0.25
            + momentum_score * 0.35
            + amount_score * 0.25
            + turnover_score * 0.15
            + limit_bonus
        )

        reasons = []
        risks = []
        tags = []
        if change is not None and change > 0:
            reasons.append("跟随板块上涨")
        if amount is not None and amount >= 100000000:
            reasons.append("成交额活跃")
            tags.append("资金活跃")
        if turnover is not None and 2 <= turnover <= 18:
            reasons.append("换手处于观察区间")
        if code in limit_up_by_code:
            tags.append("涨停确认")
            risks.extend(limit_up_by_code[code].tags)
        if change is not None and change <= -3:
            risks.append("逆板块走弱")
        if turnover is not None and turnover > 30:
            risks.append("换手过高")
        if amount is not None and amount < 20000000:
            risks.append("成交额偏低")

        return MarketRadarSectorStock(
            code=code,
            name=name,
            industry=industry,
            latest_price=latest_price,
            change_percent=change,
            turnover_rate=turnover,
            amount=amount,
            sector_heat_score=round(sector_heat, 2),
            stock_score=round(score, 2),
            reasons=list(dict.fromkeys(reasons or ["板块成分股"])),
            risks=list(dict.fromkeys(risks)),
            tags=list(dict.fromkeys(tags)),
        )

    def _enrich_sector_stocks_with_trend(
            self,
            stocks: List[MarketRadarSectorStock],
            normalized_date: str,
    ) -> None:
        if not stocks:
            return

        for stock in stocks:
            metrics = self._stock_trend_metrics(stock.code, normalized_date)
            if not metrics:
                stock.trend_score = 45
                stock.volume_score = 36
                stock.relative_strength_score = 45
                stock.risks = list(dict.fromkeys([*stock.risks, "K线不足"]))
                continue
            stock.trend_score = metrics["trend_score"]
            stock.volume_score = metrics["volume_score"]
            stock.ma_state = metrics["ma_state"]
            stock.return_5d = metrics["return_5d"]
            stock.return_10d = metrics["return_10d"]
            stock.return_20d = metrics["return_20d"]
            stock.volume_ratio_5d = metrics["volume_ratio_5d"]
            stock.trend_tags = list(metrics["trend_tags"])
            stock.risks = list(dict.fromkeys([*stock.risks, *metrics["risks"]]))

        sector_avg_5d = self._average_optional([item.return_5d for item in stocks])
        sector_avg_10d = self._average_optional([item.return_10d for item in stocks])

        for stock in stocks:
            strength_gap = None
            if stock.return_5d is not None and sector_avg_5d is not None:
                strength_gap = stock.return_5d - sector_avg_5d
            elif stock.return_10d is not None and sector_avg_10d is not None:
                strength_gap = stock.return_10d - sector_avg_10d
            stock.relative_strength_score = self._ratio_score(
                strength_gap,
                [(6.0, 96), (3.0, 84), (1.2, 70), (0.0, 56), (-2.0, 38), (-100.0, 18)],
            )
            if strength_gap is not None:
                if strength_gap >= 1.2:
                    stock.trend_tags = list(dict.fromkeys([*stock.trend_tags, "跑赢板块"]))
                    stock.reasons = list(dict.fromkeys([*stock.reasons, "相对板块强"]))
                elif strength_gap <= -2:
                    stock.risks = list(dict.fromkeys([*stock.risks, "弱于板块"]))

            spot_momentum = self._ratio_score(
                stock.change_percent,
                [(9.5, 96), (6.0, 86), (3.0, 74), (1.0, 58), (0.0, 42), (-3.0, 24), (-100.0, 10)],
            )
            limit_bonus = 8 if "涨停确认" in stock.tags else 0
            risk_penalty = 8 if "K线不足" in stock.risks else 0
            stock.stock_score = round(self._clamp_score(
                stock.sector_heat_score * 0.20
                + stock.trend_score * 0.30
                + stock.relative_strength_score * 0.25
                + stock.volume_score * 0.15
                + spot_momentum * 0.10
                + limit_bonus
                - risk_penalty
            ), 2)

    def _stock_trend_metrics(self, code: str, normalized_date: str) -> Optional[dict]:
        if not self.store or not self.store.is_available():
            return None
        try:
            bars = self.store.get_stock_kline_daily(code, 80, normalized_date)
        except MarketReviewStoreUnavailable as exc:
            logger.warning("Market radar stock trend load skipped for %s: %s", code, exc)
            return None
        if len(bars) < 21:
            return None

        bars = sorted([item for item in bars if item.trade_date <= normalized_date], key=lambda item: item.trade_date)
        if len(bars) < 21:
            return None

        latest = bars[-1]
        closes = [item.close_price for item in bars]
        volumes = [item.volume or 0 for item in bars]
        close = latest.close_price
        ma5 = self._tail_average(closes, 5)
        ma10 = self._tail_average(closes, 10)
        ma20 = self._tail_average(closes, 20)
        ma60 = self._tail_average(closes, 60)
        return_5d = self._window_return(closes, 5)
        return_10d = self._window_return(closes, 10)
        return_20d = self._window_return(closes, 20)
        volume_ratio_5d = self._latest_volume_ratio(volumes, 5)
        trend_tags: List[str] = []
        risks: List[str] = []
        score = 45.0

        if ma20 and close >= ma20:
            score += 14
            trend_tags.append("站上20日线")
        elif ma20:
            score -= 12
            risks.append("20日线下")

        if ma5 and ma10 and ma20 and close >= ma5 >= ma10 >= ma20:
            score += 22
            trend_tags.append("均线多头")
        elif ma5 and ma10 and close >= ma10 and ma5 >= ma10:
            score += 10
            trend_tags.append("短均线走强")

        recent_high_20 = max(closes[-20:])
        recent_low_20 = min(closes[-20:])
        if close >= recent_high_20 * 0.98:
            score += 12
            trend_tags.append("接近20日高位")
        if close <= recent_low_20 * 1.03:
            score -= 10
            risks.append("接近20日低位")

        if return_5d is not None and return_5d > 0:
            score += min(return_5d, 8)
        if return_20d is not None and return_20d > 0:
            score += min(return_20d * 0.35, 8)
        if volume_ratio_5d is not None:
            if 1.2 <= volume_ratio_5d <= 2.8:
                trend_tags.append("温和放量")
            elif volume_ratio_5d > 3.5:
                risks.append("放量过急")
            elif volume_ratio_5d < 0.65:
                risks.append("量能不足")

        latest_date = latest.trade_date[:10]
        if latest_date < normalized_date:
            risks.append("K线未含当日")
            try:
                gap_days = (datetime.strptime(normalized_date, "%Y-%m-%d") -
                            datetime.strptime(latest_date, "%Y-%m-%d")).days
                if gap_days >= 7:
                    risks.append("K线偏旧")
            except ValueError:
                pass

        ma_state = "均线不足"
        if ma5 and ma10 and ma20:
            if close >= ma5 >= ma10 >= ma20:
                ma_state = "多头"
            elif close >= ma20:
                ma_state = "站上20日"
            else:
                ma_state = "20日线下"
        return {
            "trend_score": round(self._clamp_score(score), 2),
            "volume_score": round(self._volume_ratio_score(volume_ratio_5d), 2),
            "ma_state": ma_state,
            "return_5d": return_5d,
            "return_10d": return_10d,
            "return_20d": return_20d,
            "volume_ratio_5d": volume_ratio_5d,
            "trend_tags": list(dict.fromkeys(trend_tags)),
            "risks": list(dict.fromkeys(risks)),
            "ma60": ma60,
        }

    @staticmethod
    def _tail_average(values: List[float], window: int) -> Optional[float]:
        if len(values) < window:
            return None
        segment = values[-window:]
        return round(sum(segment) / window, 4)

    @staticmethod
    def _window_return(values: List[float], window: int) -> Optional[float]:
        if len(values) <= window:
            return None
        base = values[-window - 1]
        if base <= 0:
            return None
        return round(((values[-1] / base) - 1) * 100, 4)

    @staticmethod
    def _latest_volume_ratio(values: List[float], window: int) -> Optional[float]:
        if len(values) <= window:
            return None
        latest = values[-1]
        previous = values[-window - 1:-1]
        average = sum(previous) / len(previous) if previous else 0
        if average <= 0:
            return None
        return round(latest / average, 4)

    @staticmethod
    def _average_optional(values: List[Optional[float]]) -> Optional[float]:
        available = [item for item in values if item is not None]
        if not available:
            return None
        return sum(available) / len(available)

    @staticmethod
    def _volume_ratio_score(value: Optional[float]) -> float:
        if value is None:
            return 45.0
        if 1.2 <= value <= 2.8:
            return 86.0
        if 0.8 <= value < 1.2:
            return 66.0
        if 2.8 < value <= 4.0:
            return 62.0
        if 0.5 <= value < 0.8:
            return 42.0
        if value > 4.0:
            return 38.0
        return 28.0

    def _radar_from_limit_up_pool(
            self,
            pool: List[LimitUpStock],
            sector_strength: List[SectorStrength],
            candidate_limit: int,
            source_note: str,
    ) -> Tuple[List[MarketRadarSector], List[MarketRadarCandidate]]:
        sectors = [
            MarketRadarSector(
                sector_name=item.industry,
                heat_score=item.strength_score,
                momentum_score=item.strength_score,
                liquidity_score=self._amount_activity_score(item.total_amount),
                breadth_score=50,
                limit_up_count=item.limit_up_count,
                strong_stock_count=item.advanced_count,
                stock_count=item.limit_up_count,
                rise_count=item.limit_up_count,
                total_amount=item.total_amount,
                core_stocks=list(item.core_stocks),
                reasons=["涨停池强度靠前"],
                risks=list(dict.fromkeys([source_note, *item.risk_tags])) if source_note else list(item.risk_tags),
            )
            for item in sector_strength
        ]
        sector_score_map = {item.sector_name: item.heat_score for item in sectors}
        candidates = [
            MarketRadarCandidate(
                code=item.code,
                name=item.name,
                industry=item.industry,
                latest_price=item.latest_price,
                change_percent=item.change_percent,
                turnover_rate=item.turnover_rate,
                amount=item.amount,
                candidate_score=round(
                    self._clamp_score(item.board_quality_score * 0.58 + sector_score_map.get(item.industry, 0) * 0.42),
                    2,
                ),
                sector_heat_score=round(sector_score_map.get(item.industry, 0), 2),
                signal_type="limit_up",
                reasons=["涨停池入选", "所属板块在涨停池中靠前"],
                risks=list(dict.fromkeys([source_note, *item.tags])) if source_note else list(item.tags),
                tags=["涨停确认", f"{item.consecutive_boards}板"],
            )
            for item in pool
        ]
        return sectors, sorted(candidates, key=lambda item: item.candidate_score, reverse=True)[:candidate_limit]

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
        known_codes = {item.code for item in stocks}
        stocks.extend(self._fetch_missing_limit_up_strong_stocks(ak, normalized_date, known_codes))
        stocks.extend(self._fetch_missing_st_limit_up_stocks(ak, normalized_date, known_codes))
        result = sorted(stocks, key=lambda item: (-item.consecutive_boards, item.first_limit_time or "999999"))
        self._limit_up_cache[normalized_date] = (monotonic(), result)
        return result

    def _fetch_missing_limit_up_strong_stocks(self, ak: Any, normalized_date: str, known_codes: set) -> List[LimitUpStock]:
        try:
            frame = ak.stock_zt_pool_strong_em(date=normalized_date.replace("-", ""))
        except Exception as exc:
            logger.warning("Strong limit-up pool supplement skipped: %s", exc)
            return []

        result = []
        for row in frame.to_dict(orient="records"):
            code = str(self._pick(row, "代码", "股票代码", default="")).zfill(6)
            if not code or code in known_codes or not self._is_limit_price_row(row):
                continue
            stock = self._row_to_limit_up_stock(row)
            stock.tags = list(dict.fromkeys([*stock.tags, "强势池补充"]))
            result.append(stock)
            known_codes.add(stock.code)
        return result

    def _fetch_missing_st_limit_up_stocks(self, ak: Any, normalized_date: str, known_codes: set) -> List[LimitUpStock]:
        if normalized_date != self._now().strftime("%Y-%m-%d"):
            return []
        try:
            frame = ak.stock_zh_a_st_em()
        except Exception as exc:
            logger.warning("ST limit-up pool supplement skipped: %s", exc)
            return []

        result = []
        for row in frame.to_dict(orient="records"):
            code = str(self._pick(row, "代码", "股票代码", default="")).zfill(6)
            if not code or code in known_codes:
                continue
            change_percent = self._to_float(self._pick(row, "涨跌幅"))
            if change_percent is None or change_percent < 4.8:
                continue
            boards = self._estimate_st_consecutive_boards(code, normalized_date)
            stock = self._row_to_limit_up_stock({
                **row,
                "所属行业": self._pick(row, "所属行业", default="风险警示"),
                "涨停统计": f"{boards}连" if boards > 1 else "1/1",
                "连板数": boards,
                "炸板次数": 0,
            })
            stock.tags = list(dict.fromkeys([*stock.tags, "ST补充"]))
            result.append(stock)
            known_codes.add(stock.code)
        return result

    def _estimate_st_consecutive_boards(self, code: str, normalized_date: str) -> int:
        try:
            bars = self._fetch_stock_kline_daily(code, normalized_date, 12)
        except Exception as exc:
            logger.warning("ST consecutive board estimate skipped for %s: %s", code, exc)
            return 1
        if len(bars) < 2:
            return 1
        ordered = [item for item in sorted(bars, key=lambda item: item.trade_date) if item.trade_date <= normalized_date]
        count = 0
        for index in range(len(ordered) - 1, 0, -1):
            previous_close = ordered[index - 1].close_price
            limit_price = round(previous_close * 1.05, 2)
            if ordered[index].close_price >= limit_price * 0.998:
                count += 1
                continue
            break
        return max(count, 1)

    def sector_strength(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            environment: Optional[MarketEnvironment] = None,
    ) -> List[SectorStrength]:
        stocks = pool if pool is not None else self.limit_up_pool(trading_date)
        env = environment or self.market_environment(trading_date, stocks)
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
            breakdown = self._sector_strength_breakdown(items, env)
            score = breakdown["score"]
            risks = []
            if open_count >= max(2, len(items)):
                risks.append("炸板偏多")
            if len(items) == 1:
                risks.append("板块跟随不足")
            if len(core) == 1 or (core and core[0].board_quality_score - core[-1].board_quality_score > 35):
                risks.append("核心断层明显")
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
                score_breakdown=breakdown,
                risk_tags=risks,
            ))
        return sorted(sectors, key=lambda item: item.strength_score, reverse=True)

    def candidates_by_pool_type(
            self,
            pool_type: str,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            sectors: Optional[List[SectorStrength]] = None,
            environment: Optional[MarketEnvironment] = None,
    ) -> List[CandidateStock]:
        normalized = self._normalize_pool_type(pool_type)
        return [
            item
            for item in self.advancement_candidates(trading_date, pool, sectors, environment)
            if item.pool_type == normalized
        ]

    def candidates_2_to_3(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            sectors: Optional[List[SectorStrength]] = None,
            environment: Optional[MarketEnvironment] = None,
    ) -> List[CandidateStock]:
        return self.candidates_by_pool_type("2_to_3", trading_date, pool, sectors, environment)

    def advancement_candidates(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            sectors: Optional[List[SectorStrength]] = None,
            environment: Optional[MarketEnvironment] = None,
    ) -> List[CandidateStock]:
        stocks = pool if pool is not None else self.limit_up_pool(trading_date)
        env = environment or self.market_environment(trading_date, stocks)
        sector_list = sectors if sectors is not None else self.sector_strength(trading_date, stocks, env)
        sector_map = {item.industry: item for item in sector_list}
        candidates: List[CandidateStock] = []

        for stock in stocks:
            if stock.consecutive_boards < 1:
                continue
            target_boards = stock.consecutive_boards + 1
            pool_type = f"{stock.consecutive_boards}_to_{target_boards}"
            sector = sector_map.get(stock.industry or "未分类")
            breakdown = self._candidate_score_breakdown(stock, sector, stocks, env)
            score = breakdown["score"]
            reasons = []
            risks = list(stock.tags)
            if sector and sector.limit_up_count >= 3:
                reasons.append("板块涨停家数靠前")
            if sector and sector.advanced_count >= 2:
                reasons.append("板块有连板梯队")
            if self._is_sector_leader(stock, stocks):
                reasons.append("板块梯队前排")
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
            level = "高关注" if score >= 80 and len(risks) <= 1 and "尾盘封板" not in risks else "观察"
            if score < 60 or len(risks) >= 3:
                level = "剔除"
            candidates.append(CandidateStock(
                stock=stock,
                sector=sector,
                pool_type=pool_type,
                target_boards=target_boards,
                candidate_score=round(score, 2),
                score_breakdown=breakdown,
                level=level,
                reasons=reasons or [f"{stock.consecutive_boards}板入池"],
                risks=risks,
            ))
        return sorted(candidates, key=lambda item: item.candidate_score, reverse=True)

    def divergence_consensus(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            sectors: Optional[List[SectorStrength]] = None,
            environment: Optional[MarketEnvironment] = None,
    ) -> List[DivergenceConsensusSignal]:
        stocks = pool if pool is not None else self.limit_up_pool(trading_date)
        env = environment or self.market_environment(trading_date, stocks)
        sector_list = sectors if sectors is not None else self.sector_strength(trading_date, stocks, env)
        sector_map = {item.industry: item for item in sector_list}
        signals: List[DivergenceConsensusSignal] = []

        for stock in stocks:
            sector = sector_map.get(stock.industry or "未分类")
            open_count = stock.open_count or 0
            reasons = []
            risks = []
            phase = "一致"
            if open_count > 0:
                phase = "分歧转一致"
                reasons.append("盘中炸板后回封")
            if stock.last_limit_time and stock.first_limit_time and stock.last_limit_time > stock.first_limit_time:
                reasons.append("最后封板晚于首次封板")
            if sector and sector.limit_up_count >= 3:
                reasons.append("同板块涨停家数形成回流")
            if sector and sector.advanced_count >= 2:
                reasons.append("板块连板梯队仍在")
            breakdown = self._divergence_signal_score_breakdown(stock, sector, stocks, env)
            score = breakdown["score"]
            if open_count >= 4:
                risks.append("分歧过大")
            if stock.first_limit_time and stock.first_limit_time >= "143000":
                risks.append("尾盘一致性待确认")
            if phase == "分歧转一致" or score >= 55:
                signals.append(DivergenceConsensusSignal(
                    code=stock.code,
                    name=stock.name,
                    industry=stock.industry,
                    phase=phase,
                    signal_score=round(score, 2),
                    score_breakdown=breakdown,
                    reasons=reasons or ["封板稳定"],
                    risks=risks,
                ))
        return sorted(signals, key=lambda item: item.signal_score, reverse=True)

    def market_environment(
            self,
            trading_date: Optional[str] = None,
            pool: Optional[List[LimitUpStock]] = None,
            refresh: bool = False,
    ) -> MarketEnvironment:
        normalized_date = self._normalize_date(trading_date)
        stocks = pool if pool is not None else self.limit_up_pool(normalized_date)
        cached = None if refresh else self._get_cached(self._environment_cache, normalized_date)
        if cached is not None:
            return cached

        environment: Optional[MarketEnvironment] = None
        if normalized_date == self._now().strftime("%Y-%m-%d"):
            try:
                environment = self._fetch_market_environment(normalized_date, stocks)
            except Exception as exc:
                logger.warning("Market environment fetch skipped for %s: %s", normalized_date, exc)
        if environment is None:
            environment = self._fallback_market_environment(normalized_date, stocks)
        self._environment_cache[normalized_date] = (monotonic(), environment)
        return environment

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

    def normalize_date(self, value: Optional[str] = None) -> str:
        return self._normalize_date(value)

    def snapshot_status(self, trading_date: Optional[str] = None) -> str:
        return self._snapshot_status(self.normalize_date(trading_date))

    def is_final_snapshot(self, trading_date: Optional[str] = None) -> bool:
        return self.snapshot_status(trading_date) == SNAPSHOT_FINAL

    def normalize_pool_type(self, value: str) -> str:
        return self._normalize_pool_type(value)

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
        use_stored_bars = not refresh and self._snapshot_status(normalized_date) == SNAPSHOT_FINAL
        bars: List[StockKlineBar] = []

        if normalized_period == "five_day":
            bars = self._fetch_stock_kline_five_day(normalized_code, normalized_date)
        elif normalized_period == "day":
            if use_stored_bars and self.store and self.store.is_available():
                try:
                    bars = self.store.get_stock_kline_daily(normalized_code, normalized_limit, normalized_date)
                    if bars and not self._daily_bars_cover_date(bars, normalized_date):
                        logger.info(
                            "Stored daily kline is stale for %s, latest=%s, requested=%s",
                            normalized_code,
                            bars[-1].trade_date,
                            normalized_date,
                        )
                        bars = []
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
            if use_stored_bars and self.store and self.store.is_available():
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

    def _get_cached_radar(self, normalized_date: str, expected_status: str) -> Optional[MarketRadarData]:
        cached = self._radar_cache.get(normalized_date)
        if not cached:
            return None
        created_at, value, status = cached
        if monotonic() - created_at > self.cache_ttl_seconds:
            self._radar_cache.pop(normalized_date, None)
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

    def close(self) -> None:
        self._kline_executor.shutdown(wait=False, cancel_futures=True)

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
        breakdown = self._quality_score_breakdown(stock)
        stock.board_quality_score = breakdown["score"]
        stock.score_breakdown = breakdown
        stock.tags = self._risk_tags(stock)
        return stock

    def _quality_score(self, stock: LimitUpStock) -> float:
        breakdown = self._quality_score_breakdown(stock)
        return self._clamp_score(breakdown["score"])

    def _quality_score_breakdown(self, stock: LimitUpStock) -> dict:
        seal_timing = self._seal_timing_score(stock)
        seal_stability = self._seal_stability_score(stock)
        seal_strength = self._seal_strength_score(stock)
        turnover_structure = self._turnover_structure_score(stock)
        ladder_position = self._ladder_position_score(stock)
        market_fit = 60.0
        risk_penalty = self._stock_risk_penalty(stock)
        score = (
                seal_timing * 0.22
                + seal_stability * 0.18
                + seal_strength * 0.20
                + turnover_structure * 0.15
                + ladder_position * 0.15
                + market_fit * 0.10
                - risk_penalty
        )
        return self._score_breakdown(
            score=score,
            seal_timing=seal_timing,
            seal_stability=seal_stability,
            seal_strength=seal_strength,
            turnover_structure=turnover_structure,
            ladder_position=ladder_position,
            market_fit=market_fit,
            risk_penalty=risk_penalty,
        )

    def _sector_strength_score(
            self,
            items: List[LimitUpStock],
            environment: Optional[MarketEnvironment] = None,
    ) -> float:
        return self._sector_strength_breakdown(items, environment)["score"]

    def _sector_strength_breakdown(
            self,
            items: List[LimitUpStock],
            environment: Optional[MarketEnvironment] = None,
    ) -> dict:
        if not items:
            return self._score_breakdown(score=0.0)
        limit_up_count = len(items)
        open_count = sum(item.open_count or 0 for item in items)
        top_quality = sorted((item.board_quality_score for item in items), reverse=True)[:3]
        leader_quality = sum(top_quality) / len(top_quality) if top_quality else 0.0
        total_seal = sum(item.seal_amount or 0 for item in items)
        total_amount = sum(item.amount or 0 for item in items)
        seal_amount_ratio = total_seal / total_amount if total_amount > 0 else 0.0
        open_rate = open_count / max(limit_up_count, 1)
        diffusion = self._limit_up_diffusion_score(limit_up_count)
        ladder_completeness = self._sector_ladder_completeness_score(items)
        capital_confirmation = (
                self._ratio_score(seal_amount_ratio, [(0.10, 100), (0.06, 85), (0.03, 65), (0.015, 45), (0.0, 20)])
                * 0.65
                + (self._money_score(total_seal, 10) / 10) * 100 * 0.35
        )
        persistence = min(max((max(item.consecutive_boards for item in items) - 1) * 22, 25), 100)
        market_environment = self._market_environment_score(items, environment)
        risk_penalty = min(open_rate * 22, 28)
        if limit_up_count == 1:
            risk_penalty += 12
        score = (
                diffusion * 0.25
                + ladder_completeness * 0.25
                + leader_quality * 0.20
                + capital_confirmation * 0.15
                + persistence * 0.10
                + market_environment * 0.05
                - risk_penalty
        )
        return self._score_breakdown(
            score=score,
            limit_up_diffusion=diffusion,
            ladder_completeness=ladder_completeness,
            leader_quality=leader_quality,
            capital_confirmation=capital_confirmation,
            persistence=persistence,
            market_environment=market_environment,
            risk_penalty=risk_penalty,
        )

    def _candidate_score(
            self,
            stock: LimitUpStock,
            sector: Optional[SectorStrength],
            pool: List[LimitUpStock],
            environment: Optional[MarketEnvironment] = None,
    ) -> float:
        return self._candidate_score_breakdown(stock, sector, pool, environment)["score"]

    def _candidate_score_breakdown(
            self,
            stock: LimitUpStock,
            sector: Optional[SectorStrength],
            pool: List[LimitUpStock],
            environment: Optional[MarketEnvironment] = None,
    ) -> dict:
        sector_score = sector.strength_score if sector else 35.0
        ladder_position = self._ladder_position_score(stock, pool)
        next_day_expectation = self._next_day_expectation_score(stock, sector, pool)
        market_environment = self._market_environment_score(pool, environment)
        risk_penalty = 0.0
        if stock.first_limit_time and stock.first_limit_time >= "143000":
            risk_penalty += 8
        if stock.seal_amount and stock.amount and stock.seal_amount / max(stock.amount, 1) < 0.03:
            risk_penalty += 8
        if (stock.open_count or 0) >= 3:
            risk_penalty += 12
        if sector and sector.limit_up_count <= 1 and market_environment < 55:
            risk_penalty += 8
        score = (
                stock.board_quality_score * 0.42
                + sector_score * 0.28
                + ladder_position * 0.15
                + next_day_expectation * 0.10
                + market_environment * 0.05
                - risk_penalty
        )
        return self._score_breakdown(
            score=score,
            board_quality=stock.board_quality_score,
            sector_strength=sector_score,
            ladder_position=ladder_position,
            next_day_expectation=next_day_expectation,
            market_environment=market_environment,
            risk_penalty=risk_penalty,
        )

    def _divergence_signal_score(
            self,
            stock: LimitUpStock,
            sector: Optional[SectorStrength],
            pool: List[LimitUpStock],
            environment: Optional[MarketEnvironment] = None,
    ) -> float:
        return self._divergence_signal_score_breakdown(stock, sector, pool, environment)["score"]

    def _divergence_signal_score_breakdown(
            self,
            stock: LimitUpStock,
            sector: Optional[SectorStrength],
            pool: List[LimitUpStock],
            environment: Optional[MarketEnvironment] = None,
    ) -> dict:
        open_count = stock.open_count or 0
        divergence_quality = 0.0
        if open_count == 1:
            divergence_quality = 92.0
        elif open_count == 2:
            divergence_quality = 72.0
        elif open_count == 3:
            divergence_quality = 48.0
        elif open_count >= 4:
            divergence_quality = 22.0
        elif stock.last_limit_time and stock.first_limit_time and stock.last_limit_time > stock.first_limit_time:
            divergence_quality = 56.0
        reseal_strength = self._seal_strength_score(stock)
        sector_return = sector.strength_score if sector else 30.0
        leader_status = self._ladder_position_score(stock, pool)
        market_environment = self._market_environment_score(pool, environment)
        risk_penalty = 0.0
        if open_count >= 4:
            risk_penalty += 18
        if stock.first_limit_time and stock.first_limit_time >= "143000":
            risk_penalty += 10
        score = (
                divergence_quality * 0.30
                + reseal_strength * 0.25
                + sector_return * 0.25
                + leader_status * 0.10
                + market_environment * 0.10
                - risk_penalty
        )
        return self._score_breakdown(
            score=score,
            divergence_quality=divergence_quality,
            reseal_strength=reseal_strength,
            sector_return=sector_return,
            leader_status=leader_status,
            market_environment=market_environment,
            risk_penalty=risk_penalty,
        )

    @staticmethod
    def _score_breakdown(score: float, **parts: float) -> dict:
        result = {"score": round(max(min(score, 100.0), 0.0), 2)}
        result.update({key: round(float(value), 2) for key, value in parts.items()})
        return result

    @staticmethod
    def _seal_timing_score(stock: LimitUpStock) -> float:
        first_time = stock.first_limit_time
        if not first_time:
            return 45.0
        if first_time <= "093500":
            return 100.0
        if first_time <= "100000":
            return 88.0
        if first_time <= "113000":
            return 70.0
        if first_time < "143000":
            return 52.0
        return 28.0

    @staticmethod
    def _seal_stability_score(stock: LimitUpStock) -> float:
        open_count = stock.open_count or 0
        if open_count <= 0:
            return 100.0
        if open_count == 1:
            return 76.0
        if open_count == 2:
            return 52.0
        if open_count == 3:
            return 28.0
        return 12.0

    def _seal_strength_score(self, stock: LimitUpStock) -> float:
        absolute_score = (self._money_score(stock.seal_amount or 0, 12) / 12) * 100
        amount_ratio = (stock.seal_amount or 0) / stock.amount if stock.seal_amount and stock.amount else None
        float_ratio = (
            (stock.seal_amount or 0) / stock.circulating_market_value
            if stock.seal_amount and stock.circulating_market_value
            else None
        )
        amount_score = self._ratio_score(
            amount_ratio,
            [(0.10, 100), (0.06, 85), (0.03, 65), (0.015, 45), (0.0, 20)],
        )
        float_score = self._ratio_score(
            float_ratio,
            [(0.005, 100), (0.003, 82), (0.001, 62), (0.0005, 42), (0.0, 20)],
        )
        if amount_ratio is None and float_ratio is None:
            return absolute_score
        if amount_ratio is None:
            return float_score * 0.75 + absolute_score * 0.25
        if float_ratio is None:
            return amount_score * 0.75 + absolute_score * 0.25
        return amount_score * 0.55 + float_score * 0.35 + absolute_score * 0.10

    def _turnover_structure_score(self, stock: LimitUpStock) -> float:
        turnover = stock.turnover_rate
        if turnover is None:
            return 50.0
        market_value = stock.circulating_market_value or 0
        if market_value and market_value < 5_000_000_000:
            return self._band_score(turnover, 6, 26, 40)
        if market_value and market_value >= 20_000_000_000:
            return self._band_score(turnover, 2, 12, 22)
        return self._band_score(turnover, 3, 18, 30)

    def _ladder_position_score(self, stock: LimitUpStock, pool: Optional[List[LimitUpStock]] = None) -> float:
        score = min(stock.consecutive_boards * 18, 72)
        if not pool:
            return max(score, 35)
        market_highest = max((item.consecutive_boards for item in pool), default=stock.consecutive_boards)
        sector_highest = max(
            (item.consecutive_boards for item in pool if (item.industry or "未分类") == (stock.industry or "未分类")),
            default=stock.consecutive_boards,
        )
        if stock.consecutive_boards >= market_highest:
            score += 20
        elif stock.consecutive_boards >= sector_highest:
            score += 12
        if self._is_sector_leader(stock, pool):
            score += 8
        return self._clamp_score(score)

    @staticmethod
    def _is_sector_leader(stock: LimitUpStock, pool: List[LimitUpStock]) -> bool:
        sector = stock.industry or "未分类"
        sector_highest = max((item.consecutive_boards for item in pool if (item.industry or "未分类") == sector),
                             default=0)
        return stock.consecutive_boards >= sector_highest

    def _next_day_expectation_score(
            self,
            stock: LimitUpStock,
            sector: Optional[SectorStrength],
            pool: List[LimitUpStock],
    ) -> float:
        score = 45.0
        if stock.first_limit_time and stock.first_limit_time <= "100000":
            score += 18
        if (stock.open_count or 0) == 0:
            score += 14
        if sector and sector.limit_up_count >= 3:
            score += 12
        if sector and sector.advanced_count >= 2:
            score += 8
        if self._is_sector_leader(stock, pool):
            score += 8
        if stock.first_limit_time and stock.first_limit_time >= "143000":
            score -= 18
        if stock.seal_amount and stock.amount and stock.seal_amount / max(stock.amount, 1) < 0.03:
            score -= 12
        return self._clamp_score(score)

    def _market_environment_score(
            self,
            pool: List[LimitUpStock],
            environment: Optional[MarketEnvironment] = None,
    ) -> float:
        if environment is not None and environment.environment_score > 0:
            return environment.environment_score
        if not pool:
            return 35.0
        limit_up_count = len(pool)
        advanced_count = sum(1 for item in pool if item.consecutive_boards >= 2)
        max_boards = max((item.consecutive_boards for item in pool), default=1)
        open_count = sum(item.open_count or 0 for item in pool)
        grouped: Dict[str, int] = defaultdict(int)
        for item in pool:
            grouped[item.industry or "未分类"] += 1
        top_three_count = sum(sorted(grouped.values(), reverse=True)[:3])
        concentration = top_three_count / limit_up_count

        turnover_heat = self._limit_up_diffusion_score(limit_up_count)
        breadth = self._ratio_score(
            advanced_count / limit_up_count,
            [(0.35, 100), (0.25, 82), (0.16, 64), (0.08, 46), (0.0, 28)],
        )
        limit_up_down_proxy = max(20.0, 100.0 - min((open_count / limit_up_count) * 35, 70))
        height_score = min(max_boards * 18, 100)
        theme_score = self._ratio_score(concentration, [(0.55, 100), (0.42, 82), (0.30, 64), (0.18, 45), (0.0, 28)])
        return self._clamp_score(
            turnover_heat * 0.30
            + breadth * 0.20
            + limit_up_down_proxy * 0.25
            + height_score * 0.15
            + theme_score * 0.10
        )

    def _fetch_market_environment(self, normalized_date: str, pool: List[LimitUpStock]) -> MarketEnvironment:
        ak = self._load_akshare()
        if not hasattr(ak, "stock_zh_a_spot_em"):
            raise MarketReviewUnavailable("行情服务缺少 A 股实时快照接口")
        frame = ak.stock_zh_a_spot_em()
        rows = frame.to_dict(orient="records")
        if not rows:
            raise MarketReviewUnavailable("A 股实时快照为空")

        total_amount = 0.0
        rise_count = 0
        fall_count = 0
        flat_count = 0
        limit_up_count = 0
        limit_down_count = 0

        for row in rows:
            amount = self._to_float(self._pick(row, "成交额", "amount")) or 0
            change_percent = self._to_float(self._pick(row, "涨跌幅", "change_percent"))
            latest_price = self._to_float(self._pick(row, "最新价", "收盘价", "close", "price"))
            total_amount += amount
            if change_percent is None:
                continue
            if change_percent > 0:
                rise_count += 1
            elif change_percent < 0:
                fall_count += 1
            else:
                flat_count += 1
            if latest_price and latest_price > 0 and change_percent >= self._limit_up_percent_threshold(row):
                limit_up_count += 1
            if latest_price and latest_price > 0 and change_percent <= -self._limit_up_percent_threshold(row):
                limit_down_count += 1

        max_boards = max((item.consecutive_boards for item in pool), default=1)
        environment = MarketEnvironment(
            trade_date=normalized_date,
            total_amount=round(total_amount, 2),
            rise_count=rise_count,
            fall_count=fall_count,
            flat_count=flat_count,
            limit_up_count=max(limit_up_count, len(pool)),
            limit_down_count=limit_down_count,
            max_boards=max_boards,
            source="stock_zh_a_spot_em",
        )
        environment.environment_score = self._calculate_market_environment_score(environment, pool)
        return environment

    def _fallback_market_environment(self, normalized_date: str, pool: List[LimitUpStock]) -> MarketEnvironment:
        limit_up_count = len(pool)
        max_boards = max((item.consecutive_boards for item in pool), default=1)
        environment = MarketEnvironment(
            trade_date=normalized_date,
            total_amount=round(sum(item.amount or 0 for item in pool), 2),
            limit_up_count=limit_up_count,
            max_boards=max_boards,
            source="limit_up_pool",
        )
        environment.environment_score = self._calculate_market_environment_score(environment, pool)
        return environment

    def _calculate_market_environment_score(
            self,
            environment: MarketEnvironment,
            pool: List[LimitUpStock],
    ) -> float:
        total_stock_count = environment.rise_count + environment.fall_count + environment.flat_count
        rise_ratio = environment.rise_count / total_stock_count if total_stock_count > 0 else None
        limit_up_down_ratio = (
            environment.limit_up_count / max(environment.limit_down_count, 1)
            if environment.limit_up_count or environment.limit_down_count
            else None
        )
        top_three_count = 0
        if pool:
            grouped: Dict[str, int] = defaultdict(int)
            for item in pool:
                grouped[item.industry or "未分类"] += 1
            top_three_count = sum(sorted(grouped.values(), reverse=True)[:3])
        concentration = top_three_count / len(pool) if pool else None
        advanced_ratio = (
            sum(1 for item in pool if item.consecutive_boards >= 2) / len(pool)
            if pool else None
        )

        turnover_heat = self._market_total_amount_score(environment.total_amount)
        breadth_score = self._ratio_score(
            rise_ratio,
            [(0.65, 100), (0.55, 82), (0.48, 64), (0.40, 46), (0.0, 28)],
        )
        limit_score = self._ratio_score(
            limit_up_down_ratio,
            [(8.0, 100), (4.0, 82), (2.0, 64), (1.0, 46), (0.0, 28)],
        )
        height_score = min(environment.max_boards * 18, 100)
        theme_score = self._ratio_score(concentration, [(0.55, 100), (0.42, 82), (0.30, 64), (0.18, 45), (0.0, 28)])
        advanced_score = self._ratio_score(
            advanced_ratio,
            [(0.35, 100), (0.25, 82), (0.16, 64), (0.08, 46), (0.0, 28)],
        )
        return self._clamp_score(
            turnover_heat * 0.25
            + breadth_score * 0.20
            + limit_score * 0.25
            + height_score * 0.12
            + theme_score * 0.08
            + advanced_score * 0.10
        )

    @staticmethod
    def _market_total_amount_score(total_amount: float) -> float:
        if total_amount >= 2_500_000_000_000:
            return 100.0
        if total_amount >= 1_800_000_000_000:
            return 84.0
        if total_amount >= 1_200_000_000_000:
            return 68.0
        if total_amount >= 800_000_000_000:
            return 52.0
        if total_amount > 0:
            return 36.0
        return 45.0

    @staticmethod
    def _amount_activity_score(amount: float) -> float:
        if amount >= 5_000_000_000:
            return 96.0
        if amount >= 2_000_000_000:
            return 84.0
        if amount >= 1_000_000_000:
            return 70.0
        if amount >= 300_000_000:
            return 56.0
        if amount >= 50_000_000:
            return 42.0
        if amount > 0:
            return 28.0
        return 36.0

    @staticmethod
    def _limit_up_percent_threshold(row: Dict[str, Any]) -> float:
        name = str(MarketReviewService._pick(row, "名称", "name", "股票简称", default="") or "")
        code = str(MarketReviewService._pick(row, "代码", "code", "股票代码", default="") or "")
        if "ST" in name.upper():
            return 4.8
        if code.startswith(("688", "300")):
            return 19.5
        return 9.8

    @staticmethod
    def _limit_up_diffusion_score(limit_up_count: int) -> float:
        if limit_up_count >= 100:
            return 100.0
        if limit_up_count >= 70:
            return 84.0
        if limit_up_count >= 45:
            return 68.0
        if limit_up_count >= 25:
            return 52.0
        if limit_up_count >= 10:
            return 36.0
        return 24.0

    @staticmethod
    def _sector_ladder_completeness_score(items: List[LimitUpStock]) -> float:
        boards = {item.consecutive_boards for item in items}
        score = 20.0
        if 1 in boards:
            score += 20
        if 2 in boards:
            score += 25
        if any(board >= 3 for board in boards):
            score += 30
        if len(items) >= 3:
            score += 10
        return min(score, 100.0)

    @staticmethod
    def _stock_risk_penalty(stock: LimitUpStock) -> float:
        penalty = 0.0
        if (stock.open_count or 0) >= 3:
            penalty += 12
        if stock.first_limit_time and stock.first_limit_time >= "143000":
            penalty += 10
        if stock.turnover_rate and stock.turnover_rate > 35:
            penalty += 8
        if stock.seal_amount and stock.amount and stock.seal_amount / max(stock.amount, 1) < 0.015:
            penalty += 8
        return penalty

    @staticmethod
    def _band_score(value: float, low: float, high: float, hard_high: float) -> float:
        if value < low:
            return max(25.0, 100.0 - (low - value) * 12)
        if value <= high:
            return 100.0
        if value <= hard_high:
            return max(45.0, 100.0 - (value - high) * 4)
        return max(10.0, 45.0 - (value - hard_high) * 2)

    @staticmethod
    def _ratio_score(value: Optional[float], bands: List[Tuple[float, float]]) -> float:
        if value is None:
            return 45.0
        for threshold, score in bands:
            if value >= threshold:
                return score
        return 20.0

    @staticmethod
    def _clamp_score(value: float) -> float:
        return round(max(min(value, 100), 0), 2)

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
            return max(int(match.group(2)), 1)
        match = re.search(r"(\d+)\s*连", stat)
        if match:
            return max(int(match.group(1)), 1)
        return 1

    @staticmethod
    def _is_limit_price_row(row: Dict[str, Any]) -> bool:
        latest_price = MarketReviewService._to_float(MarketReviewService._pick(row, "最新价", "收盘价"))
        limit_price = MarketReviewService._to_float(MarketReviewService._pick(row, "涨停价"))
        if latest_price is None or limit_price is None or limit_price <= 0:
            return False
        return latest_price >= limit_price * 0.999

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
    def _normalize_sector_name(value: Any) -> str:
        text = str(value or "").strip()
        if not text or text.lower() == "nan" or text in {"-", "--"}:
            return ""
        return text

    @staticmethod
    def _is_excluded_stock_name(name: str) -> bool:
        text = name.strip().upper()
        return (
            not text
            or "退" in text
            or text.startswith("ST")
            or text.startswith("*ST")
            or text.startswith("SST")
        )

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
                timeout=self.KLINE_SOURCE_TIMEOUT_SECONDS,
            )),
            ("eastmoney-raw", lambda: ak.stock_zh_a_hist(
                symbol=code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="",
                timeout=self.KLINE_SOURCE_TIMEOUT_SECONDS,
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
                    timeout=self.KLINE_SOURCE_TIMEOUT_SECONDS,
                )),
                ("tencent-raw", lambda: ak.stock_zh_a_hist_tx(
                    symbol=self._tx_symbol(code),
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                    timeout=self.KLINE_SOURCE_TIMEOUT_SECONDS,
                )),
            ])

        errors: List[str] = []
        deadline = monotonic() + self.KLINE_TOTAL_TIMEOUT_SECONDS
        for source, fetcher in attempts:
            remaining = deadline - monotonic()
            if remaining <= 0:
                errors.append("total timeout")
                break
            try:
                frame = self._call_with_timeout(fetcher, min(self.KLINE_SOURCE_TIMEOUT_SECONDS, remaining))
                rows = frame.to_dict(orient="records")
                bars = self._rows_to_kline_bars(rows, self._row_to_kline_bar, source, code)
                if bars:
                    return bars[-limit:]
                errors.append(f"{source}: empty")
            except TimeoutError as exc:
                logger.warning("AKShare daily kline fetch timed out for %s via %s", code, source)
                errors.append(f"{source}: {exc}")
            except Exception as exc:
                logger.warning("AKShare daily kline fetch failed for %s via %s: %s", code, source, exc)
                errors.append(f"{source}: {exc}")
        logger.warning("AKShare daily kline unavailable for %s, attempts=%s", code, errors)
        raise MarketReviewUnavailable("个股 K 线数据暂不可用，请稍后重试")

    def _call_with_timeout(self, fetcher, timeout_seconds: float):
        future = self._kline_executor.submit(fetcher)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"timeout after {timeout_seconds:.1f}s") from exc

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
        if self.store and self.store.is_available():
            try:
                stored_bars = self.store.get_stock_kline_daily(code, 3, normalized_date)
                previous_close = self._previous_close_from_bars(stored_bars, normalized_date)
                if previous_close > 0:
                    return previous_close
            except MarketReviewStoreUnavailable as exc:
                logger.warning("Market review previous close load skipped for %s: %s", code, exc)
        try:
            daily_bars = self._fetch_stock_kline_daily(code, normalized_date, 3)
        except MarketReviewUnavailable:
            return 0
        return self._previous_close_from_bars(daily_bars, normalized_date)

    @staticmethod
    def _previous_close_from_bars(daily_bars: List[StockKlineBar], normalized_date: str) -> float:
        if len(daily_bars) < 2:
            return 0
        previous_bars = [item for item in daily_bars if item.trade_date < normalized_date]
        if not previous_bars:
            return daily_bars[-2].close_price
        return previous_bars[-1].close_price

    @staticmethod
    def _daily_bars_cover_date(bars: List[StockKlineBar], normalized_date: str) -> bool:
        if not bars:
            return False
        latest_date = max(item.trade_date[:10] for item in bars if item.trade_date)
        return latest_date >= normalized_date

    @staticmethod
    def _compute_limit_up_price(code: str, previous_close: float) -> float:
        if code.startswith(("300", "301", "688")):
            multiplier = 1.2
        else:
            multiplier = 1.1
        return round(previous_close * multiplier, 2)
