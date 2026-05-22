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
    tags: List[str] = Field(default_factory=list)


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
    risk_tags: List[str] = Field(default_factory=list)


class CandidateStock(BaseModel):
    stock: LimitUpStock
    sector: Optional[SectorStrength] = None
    candidate_score: float = 0
    level: str = "观察"
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class DivergenceConsensusSignal(BaseModel):
    code: str
    name: str
    industry: str
    phase: str
    signal_score: float
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class MarketReviewData(BaseModel):
    date: str
    limit_up_pool: List[LimitUpStock] = Field(default_factory=list)
    sector_strength: List[SectorStrength] = Field(default_factory=list)
    candidates_2_to_3: List[CandidateStock] = Field(default_factory=list)
    divergence_consensus: List[DivergenceConsensusSignal] = Field(default_factory=list)
