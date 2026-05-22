import logging
from datetime import datetime
from typing import Dict, Optional

from db.session import create_session_factory, session_scope
from market_review.db_models import (
    MarketCandidatePool,
    MarketLimitUpPool,
    MarketReviewRun,
    MarketReviewSignal,
    MarketSectorStrength,
)
from market_review.schemas import (
    CandidateStock,
    DivergenceConsensusSignal,
    LimitUpStock,
    MarketReviewData,
    SectorStrength,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class MarketReviewStoreUnavailable(RuntimeError):
    pass


class MarketReviewStore:
    def __init__(self, postgres_dsn: str):
        self.unavailable_reason = ""
        self.session_factory = None
        try:
            self.session_factory = create_session_factory(postgres_dsn)
        except ModuleNotFoundError:
            self.unavailable_reason = "缺少 PostgreSQL 驱动，请先安装 py/requirements.txt 中的依赖"
        except Exception:
            logger.exception("PostgreSQL market review store initialization failed")
            self.unavailable_reason = "PostgreSQL 连接初始化失败，请检查 POSTGRES_DSN 和数据库状态"

    def close(self) -> None:
        if not self.session_factory:
            return
        self.session_factory.kw["bind"].dispose()

    def is_available(self) -> bool:
        return bool(self.session_factory)

    def get_review(self, trade_date: str) -> Optional[MarketReviewData]:
        if not self.session_factory:
            return None
        try:
            with session_scope(self.session_factory) as session:
                parsed_date = self._parse_date(trade_date)
                run = session.scalar(
                    select(MarketReviewRun).where(
                        MarketReviewRun.trade_date == parsed_date,
                        MarketReviewRun.source == "akshare",
                        MarketReviewRun.status == "success",
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

    def save_review(self, data: MarketReviewData) -> None:
        self._ensure_available()
        try:
            with session_scope(self.session_factory) as session:
                parsed_date = self._parse_date(data.date)
                for model in (
                        MarketReviewSignal,
                        MarketCandidatePool,
                        MarketSectorStrength,
                        MarketLimitUpPool,
                        MarketReviewRun,
                ):
                    session.execute(delete(model).where(model.trade_date == parsed_date))

                session.add(MarketReviewRun(trade_date=parsed_date, source="akshare", status="success"))
                session.add_all([self._stock_to_row(parsed_date, item) for item in data.limit_up_pool])
                session.add_all([self._sector_to_row(parsed_date, item) for item in data.sector_strength])
                session.add_all([self._candidate_to_row(parsed_date, item) for item in data.advancement_candidates])
                session.add_all([self._signal_to_row(parsed_date, item) for item in data.divergence_consensus])
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

    def _ensure_available(self) -> None:
        if not self.session_factory:
            raise MarketReviewStoreUnavailable(self.unavailable_reason or "POSTGRES_DSN 未配置，市场复盘快照不可用")

    def _mark_unavailable(self, exc: SQLAlchemyError):
        logger.warning("Market review store unavailable after database error: %s", exc.__class__.__name__)
        self.unavailable_reason = "市场复盘表不可用，请先运行 Alembic 迁移"
        self.session_factory = None
        raise MarketReviewStoreUnavailable(self.unavailable_reason) from exc

    @staticmethod
    def _parse_date(value: str):
        return datetime.strptime(value, "%Y-%m-%d").date()

    @staticmethod
    def _number(value):
        return float(value) if value is not None else None

    def _stock_from_row(self, row: MarketLimitUpPool) -> LimitUpStock:
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
            tags=list(row.tags or []),
            raw_payload=dict(row.raw_payload or {}),
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
            raw_payload=dict(item.raw_payload),
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
