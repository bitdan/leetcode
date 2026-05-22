import math
import re
from collections import defaultdict
from datetime import date, datetime
from time import monotonic
from typing import Any, Dict, List, Optional, Tuple

from market_review.schemas import (
    CandidateStock,
    DivergenceConsensusSignal,
    LimitUpStock,
    MarketReviewData,
    SectorStrength,
)
from market_review.store import MarketReviewStore, MarketReviewStoreUnavailable


class MarketReviewUnavailable(RuntimeError):
    pass


class MarketReviewService:
    def __init__(self, store: Optional[MarketReviewStore] = None, cache_ttl_seconds: int = 300):
        self.store = store
        self.cache_ttl_seconds = cache_ttl_seconds
        self._limit_up_cache: Dict[str, Tuple[float, List[LimitUpStock]]] = {}
        self._review_cache: Dict[str, Tuple[float, MarketReviewData]] = {}

    def review(self, trading_date: Optional[str] = None, refresh: bool = False) -> MarketReviewData:
        normalized_date = self._normalize_date(trading_date)
        if not refresh:
            cached = self._get_cached(self._review_cache, normalized_date)
            if cached is not None:
                return cached
            stored = self._get_stored_review(normalized_date)
            if stored is not None:
                self._prime_caches(normalized_date, stored)
                return stored
        try:
            data = self._build_review(normalized_date, refresh=refresh)
        except Exception as exc:
            self._mark_failed(normalized_date, str(exc))
            raise
        self._save_review(data)
        self._prime_caches(normalized_date, data)
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
            raise MarketReviewUnavailable("AKShare 涨停池数据暂不可用") from exc

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
            raise MarketReviewUnavailable("未安装 akshare，请先在 py/requirements.txt 安装依赖") from exc
        return ak

    def _get_stored_review(self, normalized_date: str) -> Optional[MarketReviewData]:
        if not self.store or not self.store.is_available():
            return None
        try:
            return self.store.get_review(normalized_date)
        except MarketReviewStoreUnavailable:
            return None

    def _save_review(self, data: MarketReviewData) -> None:
        if not self.store or not self.store.is_available():
            return

    def _mark_failed(self, normalized_date: str, message: str) -> None:
        if not self.store or not self.store.is_available():
            return
        try:
            self.store.mark_failed(normalized_date, message)
        except Exception:
            return
        try:
            self.store.save_review(data)
        except MarketReviewStoreUnavailable:
            return

    def status(self, trading_date: Optional[str] = None) -> Optional[dict]:
        normalized_date = self._normalize_date(trading_date)
        if not self.store or not self.store.is_available():
            return None
        try:
            return self.store.status(normalized_date)
        except MarketReviewStoreUnavailable:
            return None

    def _prime_caches(self, normalized_date: str, data: MarketReviewData) -> None:
        self._review_cache[normalized_date] = (monotonic(), data)
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
