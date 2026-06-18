from typing import List, Optional

from pydantic import BaseModel, Field


class LimitUpStock(BaseModel):
    code: str
    name: str
    industry: str = ""
    latest_price: Optional[float] = None
    change_percent: Optional[float] = None
    turnover_rate: Optional[float] = None
    amount: Optional[float] = None
    circulating_market_value: Optional[float] = None
    seal_amount: Optional[float] = None
    first_limit_time: str = ""
    last_limit_time: str = ""
    open_count: Optional[int] = None
    consecutive_boards: int = 1
    limit_up_stat: str = ""
    board_quality_score: float = 0
    score_breakdown: dict = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    raw_payload: dict = Field(default_factory=dict)


class SectorStrength(BaseModel):
    industry: str
    limit_up_count: int
    advanced_count: int
    max_consecutive_boards: int
    total_seal_amount: float = 0
    total_amount: float = 0
    open_count: int = 0
    core_stocks: List[str] = Field(default_factory=list)
    strength_score: float = 0
    score_breakdown: dict = Field(default_factory=dict)
    risk_tags: List[str] = Field(default_factory=list)


class CandidateStock(BaseModel):
    stock: LimitUpStock
    sector: Optional[SectorStrength] = None
    pool_type: str = "2_to_3"
    target_boards: int = 3
    candidate_score: float = 0
    score_breakdown: dict = Field(default_factory=dict)
    level: str = "观察"
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class DivergenceConsensusSignal(BaseModel):
    code: str
    name: str
    industry: str
    phase: str
    signal_score: float
    score_breakdown: dict = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class MarketEnvironment(BaseModel):
    trade_date: str
    total_amount: float = 0
    amount_change_percent: float = 0
    rise_count: int = 0
    fall_count: int = 0
    flat_count: int = 0
    limit_up_count: int = 0
    limit_down_count: int = 0
    max_boards: int = 1
    environment_score: float = 0
    source: str = "fallback"


class MarketReviewData(BaseModel):
    date: str
    limit_up_pool: List[LimitUpStock] = Field(default_factory=list)
    sector_strength: List[SectorStrength] = Field(default_factory=list)
    advancement_candidates: List[CandidateStock] = Field(default_factory=list)
    candidates_2_to_3: List[CandidateStock] = Field(default_factory=list)
    divergence_consensus: List[DivergenceConsensusSignal] = Field(default_factory=list)
    market_environment: Optional[MarketEnvironment] = None


class MarketRadarSector(BaseModel):
    sector_name: str
    sector_type: str = "industry"
    heat_score: float = 0
    momentum_score: float = 0
    liquidity_score: float = 0
    breadth_score: float = 0
    limit_up_count: int = 0
    strong_stock_count: int = 0
    stock_count: int = 0
    rise_count: int = 0
    change_percent: float = 0
    total_amount: float = 0
    core_stocks: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class MarketRadarCandidate(BaseModel):
    code: str
    name: str
    industry: str = ""
    latest_price: Optional[float] = None
    change_percent: Optional[float] = None
    turnover_rate: Optional[float] = None
    amount: Optional[float] = None
    candidate_score: float = 0
    sector_heat_score: float = 0
    signal_type: str = "sector_strength"
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class MarketRadarSectorStock(BaseModel):
    code: str
    name: str
    industry: str = ""
    latest_price: Optional[float] = None
    change_percent: Optional[float] = None
    turnover_rate: Optional[float] = None
    amount: Optional[float] = None
    sector_heat_score: float = 0
    stock_score: float = 0
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class MarketRadarData(BaseModel):
    date: str
    market_environment: Optional[MarketEnvironment] = None
    sectors: List[MarketRadarSector] = Field(default_factory=list)
    candidates: List[MarketRadarCandidate] = Field(default_factory=list)
    generated_at: str = ""


class StockKlineBar(BaseModel):
    trade_date: str
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    volume: float = 0
    amount: float = 0
    amplitude: Optional[float] = None
    change_amount: Optional[float] = None
    change_percent: Optional[float] = None
    turnover_rate: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma30: Optional[float] = None
    ma60: Optional[float] = None
    dif: Optional[float] = None
    dea: Optional[float] = None
    macd: Optional[float] = None
    is_reseal_bar: bool = False
    is_breakout_bar: bool = False


class StockKlineSummary(BaseModel):
    latest_price: float
    change_amount: Optional[float] = None
    change_percent: Optional[float] = None
    open_price: float
    high_price: float
    low_price: float
    volume: float = 0
    amount: float = 0
    turnover_rate: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma30: Optional[float] = None
    ma60: Optional[float] = None


class StockKlineSnapshot(BaseModel):
    code: str
    name: str = ""
    period: str = "day"
    date: str
    bars: List[StockKlineBar] = Field(default_factory=list)
    summary: Optional[StockKlineSummary] = None
    technical_tags: List[str] = Field(default_factory=list)
    intraday_signals: List["IntradayTradingSignal"] = Field(default_factory=list)


class IntradayTradingSignal(BaseModel):
    signal_type: str
    title: str
    phase: str
    signal_score: float
    observed_at: str = ""
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


StockKlineSnapshot.model_rebuild()
