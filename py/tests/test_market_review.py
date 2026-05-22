import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from market_review.schemas import (
    CandidateStock,
    DivergenceConsensusSignal,
    LimitUpStock,
    MarketReviewData,
    SectorStrength,
    StockKlineBar,
)
from market_review.service import MarketReviewService


def build_review_data(trade_date: str = "2026-05-22") -> MarketReviewData:
    stock = LimitUpStock(
        code="000001",
        name="平安银行",
        industry="银行",
        latest_price=12.34,
        change_percent=10.0,
        turnover_rate=5.2,
        amount=123456789.0,
        circulating_market_value=987654321.0,
        seal_amount=4567890.0,
        first_limit_time="093500",
        last_limit_time="145500",
        open_count=1,
        consecutive_boards=2,
        limit_up_stat="2/2",
        board_quality_score=88.5,
        tags=["回封"],
        raw_payload={"代码": "000001"},
    )
    sector = SectorStrength(
        industry="银行",
        limit_up_count=1,
        advanced_count=1,
        max_consecutive_boards=2,
        total_seal_amount=4567890.0,
        total_amount=123456789.0,
        open_count=1,
        core_stocks=["平安银行"],
        strength_score=77.5,
        risk_tags=[],
    )
    candidate = CandidateStock(
        stock=stock,
        sector=sector,
        pool_type="2_to_3",
        target_boards=3,
        candidate_score=90.0,
        level="高关注",
        reasons=["板块有连板梯队"],
        risks=[],
    )
    signal = DivergenceConsensusSignal(
        code="000001",
        name="平安银行",
        industry="银行",
        phase="分歧转一致",
        signal_score=66.0,
        reasons=["盘中炸板后回封"],
        risks=[],
    )
    return MarketReviewData(
        date=trade_date,
        limit_up_pool=[stock],
        sector_strength=[sector],
        advancement_candidates=[candidate],
        candidates_2_to_3=[candidate],
        divergence_consensus=[signal],
    )


def build_kline_bars():
    return [
        StockKlineBar(
            trade_date="2026-05-19",
            open_price=10.0,
            close_price=10.2,
            high_price=10.3,
            low_price=9.9,
            volume=1000,
            amount=10000,
            change_amount=0.2,
            change_percent=2.0,
            turnover_rate=3.0,
        ),
        StockKlineBar(
            trade_date="2026-05-20",
            open_price=10.2,
            close_price=10.6,
            high_price=10.7,
            low_price=10.1,
            volume=1400,
            amount=14800,
            change_amount=0.4,
            change_percent=3.92,
            turnover_rate=3.6,
        ),
        StockKlineBar(
            trade_date="2026-05-21",
            open_price=10.5,
            close_price=10.9,
            high_price=11.0,
            low_price=10.4,
            volume=1800,
            amount=19000,
            change_amount=0.3,
            change_percent=2.83,
            turnover_rate=4.2,
        ),
        StockKlineBar(
            trade_date="2026-05-22",
            open_price=10.9,
            close_price=11.3,
            high_price=11.4,
            low_price=10.8,
            volume=3200,
            amount=36000,
            change_amount=0.4,
            change_percent=3.67,
            turnover_rate=5.1,
        ),
    ]


class FakeMarketReviewStore:
    def __init__(self, stored_review=None, available=True):
        self.stored_review = stored_review
        self.available = available
        self.saved_reviews = []
        self.failed_marks = []
        self.status_payload = None
        self.kline_bars = []
        self.saved_kline = []
        self.stock_name = ""

    def is_available(self):
        return self.available

    def get_review(self, trade_date):
        return self.stored_review if self.stored_review and self.stored_review.date == trade_date else None

    def save_review(self, data):
        self.saved_reviews.append(data)

    def mark_failed(self, trade_date, message):
        self.failed_marks.append((trade_date, message))

    def status(self, trade_date):
        return self.status_payload or {"date": trade_date, "status": "success"}

    def get_stock_kline_daily(self, code, limit, end_date):
        return self.kline_bars[-limit:]

    def save_stock_kline_daily(self, code, name, bars):
        self.saved_kline.append((code, name, bars))

    def get_stock_name(self, code):
        return self.stock_name


class MarketReviewServiceTest(unittest.TestCase):
    def test_review_returns_stored_snapshot_without_rebuild(self):
        stored = build_review_data()
        store = FakeMarketReviewStore(stored_review=stored)
        service = MarketReviewService(store=store, cache_ttl_seconds=300)

        def unexpected_build(*args, **kwargs):
            raise AssertionError("should not rebuild when stored snapshot exists")

        service._build_review = unexpected_build

        result = service.review("2026-05-22")

        self.assertEqual("2026-05-22", result.date)
        self.assertEqual(0, len(store.saved_reviews))

    def test_review_builds_and_saves_snapshot(self):
        store = FakeMarketReviewStore()
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        built = build_review_data()
        service._build_review = lambda *args, **kwargs: built

        result = service.review("2026-05-22", refresh=True)

        self.assertEqual("2026-05-22", result.date)
        self.assertEqual(1, len(store.saved_reviews))
        self.assertEqual("2026-05-22", store.saved_reviews[0].date)

    def test_review_marks_failed_when_build_raises(self):
        store = FakeMarketReviewStore()
        service = MarketReviewService(store=store, cache_ttl_seconds=300)

        def fail_build(*args, **kwargs):
            raise RuntimeError("akshare down")

        service._build_review = fail_build

        with self.assertRaises(RuntimeError):
            service.review("2026-05-22", refresh=True)

        self.assertEqual(1, len(store.failed_marks))
        self.assertEqual("2026-05-22", store.failed_marks[0][0])
        self.assertIn("akshare down", store.failed_marks[0][1])

    def test_review_uses_memory_cache_before_store(self):
        store = FakeMarketReviewStore(stored_review=build_review_data())
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        cached = build_review_data("2026-05-23")
        service._prime_caches("2026-05-23", cached)
        store.stored_review = build_review_data("2026-05-23")

        result = service.review("2026-05-23")

        self.assertEqual("2026-05-23", result.date)
        self.assertEqual("000001", result.limit_up_pool[0].code)

    def test_status_reports_store_unavailable(self):
        store = FakeMarketReviewStore(available=False)
        store.unavailable_reason = "市场复盘表不可用，请先运行 Alembic 迁移"
        service = MarketReviewService(store=store, cache_ttl_seconds=300)

        status_payload = service.status("2026-05-22")

        self.assertEqual("store_unavailable", status_payload["status"])
        self.assertIn("Alembic", status_payload["error_message"])

    def test_stock_kline_returns_stored_bars(self):
        store = FakeMarketReviewStore()
        store.kline_bars = build_kline_bars()
        store.stock_name = "平安银行"
        service = MarketReviewService(store=store, cache_ttl_seconds=300)

        result = service.stock_kline("000001", "2026-05-22", limit=60)

        self.assertEqual("000001", result.code)
        self.assertEqual("平安银行", result.name)
        self.assertEqual(4, len(result.bars))
        self.assertEqual(11.3, result.summary.latest_price)
        self.assertTrue(result.technical_tags)
        self.assertEqual(0, len(store.saved_kline))

    def test_stock_kline_fetches_and_persists_when_store_empty(self):
        store = FakeMarketReviewStore()
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        service._fetch_stock_kline = lambda *args, **kwargs: build_kline_bars()

        result = service.stock_kline("000001", "2026-05-22", limit=60, refresh=True, name="平安银行")

        self.assertEqual(1, len(store.saved_kline))
        self.assertEqual("000001", store.saved_kline[0][0])
        self.assertEqual("平安银行", store.saved_kline[0][1])
        self.assertEqual(4, len(result.bars))
        self.assertIsNotNone(result.bars[-1].dif)
        self.assertIsNotNone(result.bars[-1].macd)


if __name__ == "__main__":
    unittest.main()
