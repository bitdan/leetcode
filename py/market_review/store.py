import logging
from time import monotonic
from datetime import datetime
from typing import Dict, Optional, Sequence

from db.session import create_session_factory, session_scope
from market_review.db_models import (
    MarketCandidatePool,
    MarketLimitUpPool,
    MarketReviewRun,
    MarketReviewSignal,
    MarketSectorStrength,
    MarketStockKlineDaily,
    MarketStockKlineIntraday,
    MarketStockUniverse,
)
from market_review.schemas import (
    CandidateStock,
    DivergenceConsensusSignal,
    LimitUpStock,
    MarketReviewData,
    SectorStrength,
    StockKlineBar,
)
from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class MarketReviewStoreUnavailable(RuntimeError):
    pass


class MarketReviewStore:
    RECOVERY_RETRY_SECONDS = 300

    def __init__(self, postgres_dsn: str):
        self.postgres_dsn = postgres_dsn
        self.unavailable_reason = ""
        self.unavailable_since: Optional[float] = None
        self.session_factory = None
        self._initialize_session_factory()

    def close(self) -> None:
        if not self.session_factory:
            return
        self.session_factory.kw["bind"].dispose()

    def is_available(self) -> bool:
        if not self.session_factory:
            self._try_recover()
        return bool(self.session_factory)

    def get_review(self, trade_date: str, statuses: Optional[Sequence[str]] = None) -> Optional[MarketReviewData]:
        if not self.session_factory:
            return None
        try:
            with session_scope(self.session_factory) as session:
                parsed_date = self._parse_date(trade_date)
                allowed_statuses = tuple(statuses or ("success", "final"))
                run = session.scalar(
                    select(MarketReviewRun).where(
                        MarketReviewRun.trade_date == parsed_date,
                        MarketReviewRun.source == "akshare",
                        MarketReviewRun.status.in_(allowed_statuses),
                    )
                )
                if not run:
                    return None
                pool_rows = session.scalars(
                    select(MarketLimitUpPool)
                    .where(MarketLimitUpPool.trade_date == parsed_date)
                    .order_by(MarketLimitUpPool.consecutive_boards.desc(), MarketLimitUpPool.first_limit_time.asc())
                ).all()
                sector_rows = session.scalars(
                    select(MarketSectorStrength)
                    .where(MarketSectorStrength.trade_date == parsed_date)
                    .order_by(MarketSectorStrength.strength_score.desc())
                ).all()
                candidate_rows = session.scalars(
                    select(MarketCandidatePool)
                    .where(MarketCandidatePool.trade_date == parsed_date)
                    .order_by(MarketCandidatePool.candidate_score.desc())
                ).all()
                signal_rows = session.scalars(
                    select(MarketReviewSignal)
                    .where(MarketReviewSignal.trade_date == parsed_date)
                    .order_by(MarketReviewSignal.signal_score.desc())
                ).all()
                stock_map = {item.code: self._stock_from_row(item) for item in pool_rows}
                sector_map = {item.industry: self._sector_from_row(item) for item in sector_rows}
                candidates = [
                    self._candidate_from_row(row, stock_map, sector_map)
                    for row in candidate_rows
                    if row.code in stock_map
                ]
                return MarketReviewData(
                    date=trade_date,
                    limit_up_pool=list(stock_map.values()),
                    sector_strength=list(sector_map.values()),
                    advancement_candidates=candidates,
                    candidates_2_to_3=[item for item in candidates if item.pool_type == "2_to_3"],
                    divergence_consensus=[self._signal_from_row(item) for item in signal_rows],
                )
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)
        return None

    def save_review(self, data: MarketReviewData, status: str = "final") -> None:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                parsed_date = self._parse_date(data.date)
                self._upsert_rows(
                    session,
                    MarketReviewRun,
                    [MarketReviewRun(trade_date=parsed_date, source="akshare", status=status)],
                    "uq_market_review_runs_date_source",
                    ("trade_date", "source"),
                )
                self._replace_by_upsert(
                    session,
                    MarketLimitUpPool,
                    [self._stock_to_row(parsed_date, item) for item in data.limit_up_pool],
                    parsed_date,
                    "uq_market_limit_up_pool_date_code",
                    ("trade_date", "code"),
                    ("code",),
                )
                self._replace_by_upsert(
                    session,
                    MarketSectorStrength,
                    [self._sector_to_row(parsed_date, item) for item in data.sector_strength],
                    parsed_date,
                    "uq_market_sector_strength_date_industry",
                    ("trade_date", "industry"),
                    ("industry",),
                )
                self._replace_by_upsert(
                    session,
                    MarketCandidatePool,
                    [self._candidate_to_row(parsed_date, item) for item in data.advancement_candidates],
                    parsed_date,
                    "uq_market_candidate_pool_date_type_code",
                    ("trade_date", "pool_type", "code"),
                    ("pool_type", "code"),
                )
                self._replace_by_upsert(
                    session,
                    MarketReviewSignal,
                    [self._signal_to_row(parsed_date, item) for item in data.divergence_consensus],
                    parsed_date,
                    "uq_market_review_signal_date_type_code",
                    ("trade_date", "signal_type", "code"),
                    ("signal_type", "code"),
                )
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def mark_failed(self, trade_date: str, message: str) -> None:
        if not self.session_factory:
            return
        try:
            with session_scope(self.session_factory) as session:
                parsed_date = self._parse_date(trade_date)
                session.execute(delete(MarketReviewRun).where(MarketReviewRun.trade_date == parsed_date))
                session.add(
                    MarketReviewRun(
                        trade_date=parsed_date,
                        source="akshare",
                        status="failed",
                        error_message=message[:2000],
                    )
                )
        except SQLAlchemyError:
            logger.warning("Unable to record market review failure", exc_info=True)

    def status(self, trade_date: str) -> Optional[dict]:
        if not self.session_factory:
            return None
        try:
            with session_scope(self.session_factory) as session:
                row = session.scalar(
                    select(MarketReviewRun)
                    .where(MarketReviewRun.trade_date == self._parse_date(trade_date),
                           MarketReviewRun.source == "akshare")
                )
                if not row:
                    return None
                return {
                    "date": trade_date,
                    "source": row.source,
                    "status": row.status,
                    "error_message": row.error_message,
                    "generated_at": row.generated_at.isoformat() if row.generated_at else None,
                }
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)
        return None

    def get_stock_kline_daily(self, code: str, limit: int, end_date: str) -> list[StockKlineBar]:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                rows = session.scalars(
                    select(MarketStockKlineDaily)
                    .where(
                        MarketStockKlineDaily.code == code,
                        MarketStockKlineDaily.trade_date <= self._parse_date(end_date),
                    )
                    .order_by(MarketStockKlineDaily.trade_date.desc())
                    .limit(limit)
                ).all()
                rows = list(reversed(rows))
                return [self._kline_from_row(item) for item in rows]
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def save_stock_kline_daily(self, code: str, name: str, bars: list[StockKlineBar]) -> None:
        self._ensure_available()
        if not bars:
            return
        try:
            with session_scope(self.session_factory) as session:
                trade_dates = [self._parse_date(item.trade_date) for item in bars]
                session.execute(
                    delete(MarketStockKlineDaily).where(
                        MarketStockKlineDaily.code == code,
                        MarketStockKlineDaily.trade_date.in_(trade_dates),
                    )
                )
                session.add_all([self._kline_to_row(code, name, item) for item in bars])
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def upsert_stock_kline_daily(self, code: str, name: str, bars: list[StockKlineBar]) -> int:
        self._ensure_available()
        if not bars:
            return 0
        rows = []
        for item in bars:
            rows.append({
                "trade_date": self._parse_date(item.trade_date),
                "code": code,
                "name": name,
                "open_price": item.open_price,
                "close_price": item.close_price,
                "high_price": item.high_price,
                "low_price": item.low_price,
                "volume": item.volume or 0,
                "amount": item.amount or 0,
                "amplitude": item.amplitude,
                "change_amount": item.change_amount,
                "change_percent": item.change_percent,
                "turnover_rate": item.turnover_rate,
                "raw_payload": {},
            })
        try:
            with session_scope(self.session_factory) as session:
                stmt = pg_insert(MarketStockKlineDaily).values(rows)
                update_columns = {
                    column: getattr(stmt.excluded, column)
                    for column in (
                        "name",
                        "open_price",
                        "close_price",
                        "high_price",
                        "low_price",
                        "volume",
                        "amount",
                        "amplitude",
                        "change_amount",
                        "change_percent",
                        "turnover_rate",
                        "raw_payload",
                    )
                }
                update_columns["updated_at"] = datetime.now()
                session.execute(
                    stmt.on_conflict_do_update(
                        constraint="uq_market_stock_kline_daily_date_code",
                        set_=update_columns,
                    )
                )
                return len(rows)
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def get_stock_kline_intraday(self, code: str, period: str, trade_date: str) -> list[StockKlineBar]:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                rows = session.scalars(
                    select(MarketStockKlineIntraday)
                    .where(
                        MarketStockKlineIntraday.code == code,
                        MarketStockKlineIntraday.period == period,
                        MarketStockKlineIntraday.trade_date == self._parse_date(trade_date),
                    )
                    .order_by(MarketStockKlineIntraday.bar_time.asc())
                ).all()
                return [self._intraday_from_row(item) for item in rows]
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def save_stock_kline_intraday(self, code: str, name: str, period: str, trade_date: str,
                                  bars: list[StockKlineBar]) -> None:
        self._ensure_available()
        if not bars:
            return
        try:
            with session_scope(self.session_factory) as session:
                parsed_date = self._parse_date(trade_date)
                session.execute(
                    delete(MarketStockKlineIntraday).where(
                        MarketStockKlineIntraday.code == code,
                        MarketStockKlineIntraday.period == period,
                        MarketStockKlineIntraday.trade_date == parsed_date,
                    )
                )
                session.add_all([self._intraday_to_row(code, name, period, parsed_date, item) for item in bars])
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def get_stock_name(self, code: str) -> str:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                kline_name = session.scalar(
                    select(MarketStockKlineDaily.name)
                    .where(MarketStockKlineDaily.code == code, MarketStockKlineDaily.name != "")
                    .order_by(MarketStockKlineDaily.trade_date.desc())
                    .limit(1)
                )
                if kline_name:
                    return kline_name
                pool_name = session.scalar(
                    select(MarketLimitUpPool.name)
                    .where(MarketLimitUpPool.code == code)
                    .order_by(MarketLimitUpPool.trade_date.desc())
                    .limit(1)
                )
                return pool_name or ""
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def get_stock_universe(self) -> list[dict]:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                rows = session.scalars(
                    select(MarketStockUniverse)
                    .where(MarketStockUniverse.status == "active")
                    .order_by(MarketStockUniverse.code.asc())
                ).all()
                return [
                    {
                        "code": item.code,
                        "name": item.name,
                        "market": item.market,
                        "status": item.status,
                    }
                    for item in rows
                ]
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def upsert_stock_universe(self, stocks: list[dict]) -> int:
        self._ensure_available()
        rows = []
        for item in stocks:
            code = str(item.get("code") or "").strip()
            if not code:
                continue
            rows.append({
                "code": code,
                "name": str(item.get("name") or "").strip(),
                "market": str(item.get("market") or self._infer_market(code)),
                "status": str(item.get("status") or "active"),
                "raw_payload": item.get("raw_payload") or {},
            })
        if not rows:
            return 0
        try:
            with session_scope(self.session_factory) as session:
                stmt = pg_insert(MarketStockUniverse).values(rows)
                session.execute(
                    stmt.on_conflict_do_update(
                        index_elements=[MarketStockUniverse.code],
                        set_={
                            "name": stmt.excluded.name,
                            "market": stmt.excluded.market,
                            "status": stmt.excluded.status,
                            "raw_payload": stmt.excluded.raw_payload,
                            "updated_at": datetime.now(),
                        },
                    )
                )
                return len(rows)
        except SQLAlchemyError as exc:
            self._mark_unavailable(exc)

    def _ensure_available(self) -> None:
        if not self.session_factory:
            self._try_recover()
        if not self.session_factory:
            raise MarketReviewStoreUnavailable(self.unavailable_reason or "POSTGRES_DSN 未配置，市场复盘快照不可用")

    def _mark_unavailable(self, exc: SQLAlchemyError):
        logger.warning("Market review store unavailable after database error: %s", exc.__class__.__name__)
        self.unavailable_reason = "市场复盘表不可用，请先运行 Alembic 迁移"
        self.unavailable_since = monotonic()
        if self.session_factory:
            try:
                self.session_factory.kw["bind"].dispose()
            except Exception:
                logger.debug("Unable to dispose market review store engine", exc_info=True)
        self.session_factory = None
        raise MarketReviewStoreUnavailable(self.unavailable_reason) from exc

    def _initialize_session_factory(self) -> None:
        try:
            self.session_factory = create_session_factory(self.postgres_dsn)
            self.unavailable_reason = ""
            self.unavailable_since = None
        except ModuleNotFoundError:
            self.unavailable_reason = "缺少 PostgreSQL 驱动，请先安装 py/requirements.txt 中的依赖"
            self.unavailable_since = monotonic()
        except Exception:
            logger.exception("PostgreSQL market review store initialization failed")
            self.unavailable_reason = "PostgreSQL 连接初始化失败，请检查 POSTGRES_DSN 和数据库状态"
            self.unavailable_since = monotonic()

    def _try_recover(self) -> None:
        if self.session_factory:
            return
        if self.unavailable_since and monotonic() - self.unavailable_since < self.RECOVERY_RETRY_SECONDS:
            return
        logger.info("Retrying PostgreSQL market review store initialization")
        self._initialize_session_factory()

    def _replace_by_upsert(
            self,
            session,
            model,
            model_rows: list,
            trade_date,
            constraint: str,
            conflict_columns: tuple[str, ...],
            stale_key_columns: tuple[str, ...],
    ) -> None:
        if model_rows:
            self._upsert_rows(session, model, model_rows, constraint, conflict_columns)
            current_keys = [
                tuple(getattr(row, column) for column in stale_key_columns)
                for row in model_rows
            ]
            if len(stale_key_columns) == 1:
                column = getattr(model, stale_key_columns[0])
                session.execute(
                    delete(model).where(model.trade_date == trade_date, column.not_in([key[0] for key in current_keys]))
                )
            else:
                columns = tuple_(*(getattr(model, column) for column in stale_key_columns))
                session.execute(
                    delete(model).where(model.trade_date == trade_date, columns.not_in(current_keys))
                )
            return
        session.execute(delete(model).where(model.trade_date == trade_date))

    @staticmethod
    def _upsert_rows(session, model, model_rows: list, constraint: str, conflict_columns: tuple[str, ...]) -> None:
        if not model_rows:
            return
        rows = [MarketReviewStore._model_to_insert_dict(row) for row in model_rows]
        stmt = pg_insert(model).values(rows)
        update_columns = {
            column.name: getattr(stmt.excluded, column.name)
            for column in model.__table__.columns
            if column.name not in {"id", "created_at"} and column.name not in conflict_columns
        }
        if "updated_at" in model.__table__.columns:
            update_columns["updated_at"] = datetime.now()
        if "generated_at" in model.__table__.columns:
            update_columns["generated_at"] = datetime.now()
        session.execute(stmt.on_conflict_do_update(constraint=constraint, set_=update_columns))

    @staticmethod
    def _model_to_insert_dict(row) -> dict:
        result = {}
        for column in row.__table__.columns:
            if column.name in {"id", "created_at", "updated_at", "generated_at"}:
                continue
            result[column.name] = getattr(row, column.name)
        return result

    @staticmethod
    def _parse_date(value: str):
        return datetime.strptime(value, "%Y-%m-%d").date()

    @staticmethod
    def _number(value):
        return float(value) if value is not None else None

    @staticmethod
    def _infer_market(code: str) -> str:
        if code.startswith(("5", "6", "9")):
            return "SH"
        if code.startswith(("0", "1", "2", "3")):
            return "SZ"
        if code.startswith(("4", "8")):
            return "BJ"
        return ""

    def _stock_from_row(self, row: MarketLimitUpPool) -> LimitUpStock:
        raw_payload = dict(row.raw_payload or {})
        return LimitUpStock(
            code=row.code,
            name=row.name,
            industry=row.industry,
            latest_price=self._number(row.latest_price),
            change_percent=self._number(row.change_percent),
            turnover_rate=self._number(row.turnover_rate),
            amount=self._number(row.amount),
            circulating_market_value=self._number(row.circulating_market_value),
            seal_amount=self._number(row.seal_amount),
            first_limit_time=row.first_limit_time,
            last_limit_time=row.last_limit_time,
            open_count=row.open_count,
            consecutive_boards=row.consecutive_boards,
            limit_up_stat=row.limit_up_stat,
            board_quality_score=float(row.board_quality_score or 0),
            score_breakdown=dict(raw_payload.get("score_breakdown") or {}),
            tags=list(row.tags or []),
            raw_payload=raw_payload,
        )

    def _sector_from_row(self, row: MarketSectorStrength) -> SectorStrength:
        return SectorStrength(
            industry=row.industry,
            limit_up_count=row.limit_up_count,
            advanced_count=row.advanced_count,
            max_consecutive_boards=row.max_consecutive_boards,
            total_seal_amount=float(row.total_seal_amount or 0),
            total_amount=float(row.total_amount or 0),
            open_count=row.open_count,
            core_stocks=list(row.core_stocks or []),
            strength_score=float(row.strength_score or 0),
            risk_tags=list(row.risk_tags or []),
        )

    def _candidate_from_row(
            self,
            row: MarketCandidatePool,
            stock_map: Dict[str, LimitUpStock],
            sector_map: Dict[str, SectorStrength],
    ) -> CandidateStock:
        stock = stock_map[row.code]
        return CandidateStock(
            stock=stock,
            sector=sector_map.get(stock.industry),
            pool_type=row.pool_type,
            target_boards=row.target_boards,
            candidate_score=float(row.candidate_score or 0),
            level=row.level,
            reasons=list(row.reasons or []),
            risks=list(row.risks or []),
        )

    def _signal_from_row(self, row: MarketReviewSignal) -> DivergenceConsensusSignal:
        return DivergenceConsensusSignal(
            code=row.code,
            name=row.name,
            industry=row.industry,
            phase=row.phase,
            signal_score=float(row.signal_score or 0),
            reasons=list(row.reasons or []),
            risks=list(row.risks or []),
        )

    @staticmethod
    def _stock_to_row(trade_date, item: LimitUpStock) -> MarketLimitUpPool:
        raw_payload = dict(item.raw_payload)
        if item.score_breakdown:
            raw_payload["score_breakdown"] = dict(item.score_breakdown)
        return MarketLimitUpPool(
            trade_date=trade_date,
            code=item.code,
            name=item.name,
            industry=item.industry,
            latest_price=item.latest_price,
            change_percent=item.change_percent,
            turnover_rate=item.turnover_rate,
            amount=item.amount,
            circulating_market_value=item.circulating_market_value,
            seal_amount=item.seal_amount,
            first_limit_time=item.first_limit_time,
            last_limit_time=item.last_limit_time,
            open_count=item.open_count,
            consecutive_boards=item.consecutive_boards,
            limit_up_stat=item.limit_up_stat,
            board_quality_score=item.board_quality_score,
            tags=list(item.tags),
            raw_payload=raw_payload,
        )

    @staticmethod
    def _sector_to_row(trade_date, item: SectorStrength) -> MarketSectorStrength:
        return MarketSectorStrength(
            trade_date=trade_date,
            industry=item.industry,
            limit_up_count=item.limit_up_count,
            advanced_count=item.advanced_count,
            max_consecutive_boards=item.max_consecutive_boards,
            total_seal_amount=item.total_seal_amount,
            total_amount=item.total_amount,
            open_count=item.open_count,
            core_stocks=list(item.core_stocks),
            strength_score=item.strength_score,
            risk_tags=list(item.risk_tags),
        )

    @staticmethod
    def _candidate_to_row(trade_date, item: CandidateStock) -> MarketCandidatePool:
        return MarketCandidatePool(
            trade_date=trade_date,
            pool_type=item.pool_type,
            code=item.stock.code,
            industry=item.stock.industry,
            target_boards=item.target_boards,
            candidate_score=item.candidate_score,
            level=item.level,
            reasons=list(item.reasons),
            risks=list(item.risks),
            rule_version="v1",
        )

    @staticmethod
    def _signal_to_row(trade_date, item: DivergenceConsensusSignal) -> MarketReviewSignal:
        return MarketReviewSignal(
            trade_date=trade_date,
            signal_type="divergence_consensus",
            code=item.code,
            name=item.name,
            industry=item.industry,
            phase=item.phase,
            signal_score=item.signal_score,
            reasons=list(item.reasons),
            risks=list(item.risks),
            rule_version="v1",
        )

    def _kline_from_row(self, row: MarketStockKlineDaily) -> StockKlineBar:
        return StockKlineBar(
            trade_date=row.trade_date.isoformat(),
            open_price=float(row.open_price or 0),
            close_price=float(row.close_price or 0),
            high_price=float(row.high_price or 0),
            low_price=float(row.low_price or 0),
            volume=float(row.volume or 0),
            amount=float(row.amount or 0),
            amplitude=self._number(row.amplitude),
            change_amount=self._number(row.change_amount),
            change_percent=self._number(row.change_percent),
            turnover_rate=self._number(row.turnover_rate),
        )

    @staticmethod
    def _kline_to_row(code: str, name: str, item: StockKlineBar) -> MarketStockKlineDaily:
        return MarketStockKlineDaily(
            trade_date=datetime.strptime(item.trade_date, "%Y-%m-%d").date(),
            code=code,
            name=name,
            open_price=item.open_price,
            close_price=item.close_price,
            high_price=item.high_price,
            low_price=item.low_price,
            volume=item.volume or 0,
            amount=item.amount or 0,
            amplitude=item.amplitude,
            change_amount=item.change_amount,
            change_percent=item.change_percent,
            turnover_rate=item.turnover_rate,
            raw_payload={},
        )

    def _intraday_from_row(self, row: MarketStockKlineIntraday) -> StockKlineBar:
        return StockKlineBar(
            trade_date=row.bar_time.strftime("%Y-%m-%d %H:%M:%S"),
            open_price=float(row.open_price or 0),
            close_price=float(row.close_price or 0),
            high_price=float(row.high_price or 0),
            low_price=float(row.low_price or 0),
            volume=float(row.volume or 0),
            amount=float(row.amount or 0),
            amplitude=self._number(row.amplitude),
            change_amount=self._number(row.change_amount),
            change_percent=self._number(row.change_percent),
            turnover_rate=self._number(row.turnover_rate),
        )

    @staticmethod
    def _intraday_to_row(code: str, name: str, period: str, trade_date, item: StockKlineBar) -> MarketStockKlineIntraday:
        return MarketStockKlineIntraday(
            trade_date=trade_date,
            bar_time=datetime.strptime(item.trade_date, "%Y-%m-%d %H:%M:%S"),
            code=code,
            period=period,
            name=name,
            open_price=item.open_price,
            close_price=item.close_price,
            high_price=item.high_price,
            low_price=item.low_price,
            volume=item.volume or 0,
            amount=item.amount or 0,
            amplitude=item.amplitude,
            change_amount=item.change_amount,
            change_percent=item.change_percent,
            turnover_rate=item.turnover_rate,
            raw_payload={},
        )
