import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from market_review.schemas import (
    CandidateStock,
    DivergenceConsensusSignal,
    LimitUpStock,
    MarketEnvironment,
    MarketReviewData,
    SectorStrength,
    StockKlineBar,
)
from market_review.service import MarketReviewService
from market_review.store import MarketReviewStore


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


def build_intraday_bars():
    return [
        StockKlineBar(
            trade_date="2026-05-22 09:35:00",
            open_price=10.0,
            close_price=9.88,
            high_price=10.05,
            low_price=9.82,
            volume=1200,
            amount=11800,
        ),
        StockKlineBar(
            trade_date="2026-05-22 10:05:00",
            open_price=9.88,
            close_price=10.06,
            high_price=10.10,
            low_price=9.85,
            volume=1800,
            amount=18200,
        ),
        StockKlineBar(
            trade_date="2026-05-22 10:35:00",
            open_price=10.06,
            close_price=11.00,
            high_price=11.00,
            low_price=10.02,
            volume=2800,
            amount=30200,
        ),
        StockKlineBar(
            trade_date="2026-05-22 11:05:00",
            open_price=10.95,
            close_price=11.00,
            high_price=11.04,
            low_price=10.90,
            volume=1600,
            amount=17600,
        ),
    ]


class FakeMarketReviewStore:
    def __init__(self, stored_review=None, available=True):
        self.stored_review = stored_review
        self.available = available
        self.saved_reviews = []
        self.saved_statuses = []
        self.failed_marks = []
        self.get_review_calls = []
        self.status_payload = None
        self.kline_bars = []
        self.intraday_bars = []
        self.get_daily_kline_calls = []
        self.get_intraday_kline_calls = []
        self.saved_kline = []
        self.saved_intraday = []
        self.stock_name = ""

    def is_available(self):
        return self.available

    def get_review(self, trade_date, statuses=None):
        self.get_review_calls.append((trade_date, statuses))
        return self.stored_review if self.stored_review and self.stored_review.date == trade_date else None

    def save_review(self, data, status="final"):
        self.saved_reviews.append(data)
        self.saved_statuses.append(status)

    def mark_failed(self, trade_date, message):
        self.failed_marks.append((trade_date, message))

    def status(self, trade_date):
        return self.status_payload or {"date": trade_date, "status": "success"}

    def get_stock_kline_daily(self, code, limit, end_date):
        self.get_daily_kline_calls.append((code, limit, end_date))
        return self.kline_bars[-limit:]

    def save_stock_kline_daily(self, code, name, bars):
        self.saved_kline.append((code, name, bars))

    def get_stock_kline_intraday(self, code, period, trade_date):
        self.get_intraday_kline_calls.append((code, period, trade_date))
        return self.intraday_bars

    def save_stock_kline_intraday(self, code, name, period, trade_date, bars):
        self.saved_intraday.append((code, name, period, trade_date, bars))

    def get_stock_name(self, code):
        return self.stock_name


class FakeFrame:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, orient="records"):
        return self.rows


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
        self.assertEqual("final", store.saved_statuses[0])

    def test_today_intraday_ignores_stored_snapshot_and_saves_intraday(self):
        stored = build_review_data("2026-05-25")
        store = FakeMarketReviewStore(stored_review=stored)
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        service._now = lambda: datetime(2026, 5, 25, 12, 0, 0)
        built = build_review_data("2026-05-25")
        built.limit_up_pool[0].code = "000002"
        service._build_review = lambda *args, **kwargs: built

        result = service.review("2026-05-25")

        self.assertEqual("000002", result.limit_up_pool[0].code)
        self.assertEqual([], store.get_review_calls)
        self.assertEqual("intraday", store.saved_statuses[0])

    def test_today_after_cutoff_rebuilds_intraday_cache_as_final(self):
        store = FakeMarketReviewStore()
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        intraday = build_review_data("2026-05-25")
        service._prime_caches("2026-05-25", intraday, status="intraday")
        service._now = lambda: datetime(2026, 5, 25, 15, 11, 0)
        final = build_review_data("2026-05-25")
        final.limit_up_pool[0].code = "000003"
        service._build_review = lambda *args, **kwargs: final

        result = service.review("2026-05-25")

        self.assertEqual("000003", result.limit_up_pool[0].code)
        self.assertEqual("final", store.saved_statuses[0])

    def test_today_after_cutoff_rebuilds_legacy_noon_success_snapshot(self):
        store = FakeMarketReviewStore(stored_review=build_review_data("2026-05-25"))
        store.status_payload = {
            "date": "2026-05-25",
            "status": "success",
            "generated_at": "2026-05-25T12:00:00",
        }
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        service._now = lambda: datetime(2026, 5, 25, 15, 11, 0)
        final = build_review_data("2026-05-25")
        final.limit_up_pool[0].code = "000004"
        service._build_review = lambda *args, **kwargs: final

        result = service.review("2026-05-25")

        self.assertEqual("000004", result.limit_up_pool[0].code)
        self.assertEqual("final", store.saved_statuses[0])

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

    def test_today_intraday_stock_kline_bypasses_stored_bars(self):
        store = FakeMarketReviewStore()
        store.kline_bars = build_kline_bars()
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        service._now = lambda: datetime(2026, 5, 22, 10, 30, 0)
        fresh_bars = build_kline_bars()
        fresh_bars[-1].close_price = 12.0
        fresh_bars[-1].change_amount = 1.1
        service._fetch_stock_kline_daily = lambda *args, **kwargs: fresh_bars

        result = service.stock_kline("000001", "2026-05-22", limit=60)

        self.assertEqual([], store.get_daily_kline_calls)
        self.assertEqual(1, len(store.saved_kline))
        self.assertEqual(12.0, result.summary.latest_price)

    def test_stock_kline_fetches_and_persists_when_store_empty(self):
        store = FakeMarketReviewStore()
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        service._fetch_stock_kline_daily = lambda *args, **kwargs: build_kline_bars()

        result = service.stock_kline("000001", "2026-05-22", limit=60, refresh=True, name="平安银行")

        self.assertEqual(1, len(store.saved_kline))
        self.assertEqual("000001", store.saved_kline[0][0])
        self.assertEqual("平安银行", store.saved_kline[0][1])
        self.assertEqual(4, len(result.bars))
        self.assertIsNotNone(result.bars[-1].dif)
        self.assertIsNotNone(result.bars[-1].macd)

    def test_daily_kline_falls_back_to_unadjusted_when_qfq_empty(self):
        class FakeAkshare:
            calls = []

            @staticmethod
            def stock_zh_a_hist(**kwargs):
                FakeAkshare.calls.append(kwargs["adjust"])
                if kwargs["adjust"] == "qfq":
                    return FakeFrame([])
                return FakeFrame([{
                    "日期": "2026-05-22",
                    "开盘": 10.0,
                    "收盘": 10.5,
                    "最高": 10.8,
                    "最低": 9.9,
                    "成交量": 1200,
                    "成交额": 12600,
                }])

        service = MarketReviewService()
        with patch.object(service, "_load_akshare", return_value=FakeAkshare):
            bars = service._fetch_stock_kline_daily("000001", "2026-05-22", 30)

        self.assertEqual(["qfq", ""], FakeAkshare.calls)
        self.assertEqual(1, len(bars))
        self.assertEqual(10.5, bars[0].close_price)

    def test_daily_kline_falls_back_to_sina_when_eastmoney_empty(self):
        class FakeAkshare:
            calls = []

            @staticmethod
            def stock_zh_a_hist(**kwargs):
                FakeAkshare.calls.append(("eastmoney", kwargs["symbol"]))
                return FakeFrame([])

            @staticmethod
            def stock_zh_a_daily(**kwargs):
                FakeAkshare.calls.append(("sina", kwargs["symbol"]))
                return FakeFrame([{
                    "date": "2026-05-22",
                    "open": 10.0,
                    "close": 10.5,
                    "high": 10.8,
                    "low": 9.9,
                    "volume": 1200,
                    "amount": 12600,
                }])

        service = MarketReviewService()
        with patch.object(service, "_load_akshare", return_value=FakeAkshare):
            bars = service._fetch_stock_kline_daily("600001", "2026-05-22", 1)

        self.assertIn(("sina", "sh600001"), FakeAkshare.calls)
        self.assertEqual(1, len(bars))
        self.assertEqual("2026-05-22", bars[0].trade_date)

    def test_stock_kline_allows_single_daily_bar(self):
        store = FakeMarketReviewStore()
        store.kline_bars = build_kline_bars()
        service = MarketReviewService(store=store, cache_ttl_seconds=300)

        result = service.stock_kline("000001", "2026-05-22", limit=1)

        self.assertEqual(1, len(result.bars))
        self.assertEqual("2026-05-22", result.bars[0].trade_date)

    def test_stock_kline_supports_five_day_period(self):
        service = MarketReviewService()
        service._fetch_stock_kline_daily = lambda *args, **kwargs: build_kline_bars()
        service._fetch_stock_kline_intraday = lambda code, trade_date, period: [
            StockKlineBar(
                trade_date=f"{trade_date} 09:30:00",
                open_price=10.0,
                close_price=10.1,
                high_price=10.2,
                low_price=9.9,
                volume=100,
                amount=1000,
            )
        ]

        result = service.stock_kline("000001", "2026-05-22", period="five_day", limit=5)

        self.assertEqual("five_day", result.period)
        self.assertEqual(4, len(result.bars))
        self.assertEqual("2026-05-19 09:30:00", result.bars[0].trade_date)

    def test_intraday_kline_aggregates_120_minutes(self):
        service = MarketReviewService()
        service._fetch_stock_kline_intraday = lambda *args, **kwargs: build_intraday_bars()

        result = service.stock_kline("000001", "2026-05-22", period="120", limit=64, refresh=True)

        self.assertEqual("120", result.period)
        self.assertTrue(result.bars)
        self.assertLess(len(result.bars), len(build_intraday_bars()))

    def test_year_kline_aggregates_daily_bars(self):
        service = MarketReviewService()
        service._fetch_stock_kline_daily = lambda *args, **kwargs: [
            StockKlineBar(
                trade_date="2025-12-31",
                open_price=9.0,
                close_price=10.0,
                high_price=10.2,
                low_price=8.8,
                volume=100,
                amount=900,
            ),
            StockKlineBar(
                trade_date="2026-01-02",
                open_price=10.0,
                close_price=11.0,
                high_price=11.2,
                low_price=9.8,
                volume=120,
                amount=1200,
            ),
            StockKlineBar(
                trade_date="2026-05-22",
                open_price=11.0,
                close_price=12.0,
                high_price=12.5,
                low_price=10.8,
                volume=180,
                amount=2100,
            ),
        ]

        result = service.stock_kline("000001", "2026-05-22", period="year", limit=20, refresh=True)

        self.assertEqual("year", result.period)
        self.assertEqual(2, len(result.bars))
        self.assertEqual("2026-12-31", result.bars[-1].trade_date)
        self.assertEqual(10.0, result.bars[-1].open_price)
        self.assertEqual(12.0, result.bars[-1].close_price)

    def test_daily_kline_skips_bad_rows(self):
        class FakeAkshare:
            @staticmethod
            def stock_zh_a_hist(**kwargs):
                return FakeFrame([
                    {"日期": "", "开盘": 10.0, "收盘": 10.5, "最高": 10.8, "最低": 9.9},
                    {
                        "日期": "2026-05-22",
                        "开盘": 10.0,
                        "收盘": 10.5,
                        "最高": 10.8,
                        "最低": 9.9,
                        "成交量": 1200,
                        "成交额": 12600,
                    },
                ])

        service = MarketReviewService()
        with patch.object(service, "_load_akshare", return_value=FakeAkshare):
            bars = service._fetch_stock_kline_daily("000001", "2026-05-22", 30)

        self.assertEqual(1, len(bars))
        self.assertEqual("2026-05-22", bars[0].trade_date)

    def test_intraday_kline_builds_signals(self):
        store = FakeMarketReviewStore()
        store.intraday_bars = build_intraday_bars()
        store.kline_bars = [
            StockKlineBar(
                trade_date="2026-05-21",
                open_price=9.95,
                close_price=10.00,
                high_price=10.05,
                low_price=9.90,
                volume=1000,
                amount=10000,
            ),
            StockKlineBar(
                trade_date="2026-05-22",
                open_price=10.00,
                close_price=11.00,
                high_price=11.02,
                low_price=9.82,
                volume=5000,
                amount=57800,
            ),
        ]
        store.stock_name = "平安银行"
        service = MarketReviewService(store=store, cache_ttl_seconds=300)
        service._fetch_stock_kline_daily = lambda *args, **kwargs: store.kline_bars

        result = service.stock_kline("000001", "2026-05-22", period="30", limit=32)

        self.assertEqual("30", result.period)
        self.assertEqual(4, len(result.bars))
        self.assertTrue(any(item.signal_type == "weak_to_strong" for item in result.intraday_signals))
        self.assertTrue(any(item.signal_type == "reseal" for item in result.intraday_signals))

    def test_v2_quality_score_prefers_early_stable_relative_seal(self):
        service = MarketReviewService()
        strong = LimitUpStock(
            code="000001",
            name="强势股",
            industry="算力",
            turnover_rate=9.5,
            amount=100_000_000,
            circulating_market_value=4_000_000_000,
            seal_amount=8_000_000,
            first_limit_time="093800",
            last_limit_time="093800",
            open_count=0,
            consecutive_boards=2,
        )
        weak = LimitUpStock(
            code="000002",
            name="弱势股",
            industry="算力",
            turnover_rate=38.0,
            amount=500_000_000,
            circulating_market_value=5_000_000_000,
            seal_amount=3_000_000,
            first_limit_time="145000",
            last_limit_time="145500",
            open_count=3,
            consecutive_boards=2,
        )

        self.assertGreater(service._quality_score(strong), service._quality_score(weak) + 35)

    def test_v2_sector_strength_prefers_complete_ladder(self):
        service = MarketReviewService()
        complete_ladder = [
            LimitUpStock(
                code="000001",
                name="龙头",
                industry="机器人",
                amount=100_000_000,
                circulating_market_value=4_000_000_000,
                seal_amount=8_000_000,
                first_limit_time="093800",
                open_count=0,
                consecutive_boards=3,
                board_quality_score=90,
            ),
            LimitUpStock(
                code="000002",
                name="中军",
                industry="机器人",
                amount=120_000_000,
                circulating_market_value=8_000_000_000,
                seal_amount=6_000_000,
                first_limit_time="100500",
                open_count=0,
                consecutive_boards=2,
                board_quality_score=82,
            ),
            LimitUpStock(
                code="000003",
                name="助攻",
                industry="机器人",
                amount=80_000_000,
                circulating_market_value=3_000_000_000,
                seal_amount=4_000_000,
                first_limit_time="103000",
                open_count=1,
                consecutive_boards=1,
                board_quality_score=72,
            ),
        ]
        isolated = [
            LimitUpStock(
                code="000004",
                name="孤军",
                industry="零售",
                amount=80_000_000,
                circulating_market_value=3_000_000_000,
                seal_amount=2_000_000,
                first_limit_time="140000",
                open_count=1,
                consecutive_boards=3,
                board_quality_score=70,
            )
        ]

        self.assertGreater(
            service._sector_strength_score(complete_ladder),
            service._sector_strength_score(isolated) + 25,
        )

    def test_v2_candidates_reward_sector_support_and_penalize_late_weak_boards(self):
        service = MarketReviewService()
        leader = LimitUpStock(
            code="000001",
            name="龙头",
            industry="算力",
            amount=100_000_000,
            circulating_market_value=4_000_000_000,
            seal_amount=9_000_000,
            first_limit_time="094000",
            open_count=0,
            consecutive_boards=2,
        )
        follower = LimitUpStock(
            code="000002",
            name="助攻",
            industry="算力",
            amount=90_000_000,
            circulating_market_value=3_000_000_000,
            seal_amount=5_000_000,
            first_limit_time="101000",
            open_count=0,
            consecutive_boards=1,
        )
        weak = LimitUpStock(
            code="000003",
            name="尾盘弱板",
            industry="零售",
            amount=500_000_000,
            circulating_market_value=6_000_000_000,
            seal_amount=2_000_000,
            first_limit_time="145000",
            open_count=3,
            consecutive_boards=2,
        )
        pool = [leader, follower, weak]
        for item in pool:
            item.board_quality_score = service._quality_score(item)
        sectors = service.sector_strength("2026-05-22", pool)
        candidates = service.advancement_candidates("2026-05-22", pool, sectors)
        candidate_map = {item.stock.code: item for item in candidates}

        self.assertGreater(candidate_map["000001"].candidate_score, candidate_map["000003"].candidate_score + 20)
        self.assertNotEqual("高关注", candidate_map["000003"].level)

    def test_v2_score_breakdown_is_returned(self):
        service = MarketReviewService()
        pool = [
            LimitUpStock(
                code="000001",
                name="龙头",
                industry="算力",
                amount=100_000_000,
                circulating_market_value=4_000_000_000,
                seal_amount=9_000_000,
                first_limit_time="094000",
                open_count=1,
                consecutive_boards=2,
                last_limit_time="100000",
            ),
            LimitUpStock(
                code="000002",
                name="助攻",
                industry="算力",
                amount=90_000_000,
                circulating_market_value=3_000_000_000,
                seal_amount=5_000_000,
                first_limit_time="101000",
                open_count=0,
                consecutive_boards=1,
            ),
        ]
        for item in pool:
            item.score_breakdown = service._quality_score_breakdown(item)
            item.board_quality_score = item.score_breakdown["score"]

        sectors = service.sector_strength("2026-05-22", pool)
        candidates = service.advancement_candidates("2026-05-22", pool, sectors)
        signals = service.divergence_consensus("2026-05-22", pool, sectors)

        self.assertIn("seal_timing", pool[0].score_breakdown)
        self.assertIn("ladder_completeness", sectors[0].score_breakdown)
        self.assertIn("next_day_expectation", candidates[0].score_breakdown)
        self.assertIn("divergence_quality", signals[0].score_breakdown)

    def test_row_to_limit_up_stock_computes_quality_breakdown_once(self):
        service = MarketReviewService()
        call_count = 0
        original = service._seal_timing_score

        def counted(stock):
            nonlocal call_count
            call_count += 1
            return original(stock)

        with patch.object(service, "_seal_timing_score", side_effect=counted):
            stock = service._row_to_limit_up_stock({
                "代码": "000001",
                "名称": "强势股",
                "所属行业": "算力",
                "成交额": 100_000_000,
                "流通市值": 4_000_000_000,
                "封板资金": 8_000_000,
                "首次封板时间": "09:40:00",
                "炸板次数": 0,
                "涨停统计": "2/2",
            })

        self.assertEqual(1, call_count)
        self.assertEqual(stock.board_quality_score, stock.score_breakdown["score"])

    def test_store_row_conversion_preserves_score_breakdown(self):
        sector = SectorStrength(
            industry="算力",
            limit_up_count=2,
            advanced_count=1,
            max_consecutive_boards=2,
            strength_score=76.5,
            score_breakdown={"score": 76.5, "ladder_completeness": 80.0},
        )
        candidate = CandidateStock(
            stock=LimitUpStock(code="000001", name="强势股", industry="算力"),
            pool_type="2_to_3",
            target_boards=3,
            candidate_score=82.0,
            score_breakdown={"score": 82.0, "next_day_expectation": 75.0},
        )
        signal = DivergenceConsensusSignal(
            code="000001",
            name="强势股",
            industry="算力",
            phase="分歧转一致",
            signal_score=68.0,
            score_breakdown={"score": 68.0, "divergence_quality": 92.0},
        )
        trade_date = MarketReviewStore._parse_date("2026-05-22")

        sector_row = MarketReviewStore._sector_to_row(trade_date, sector)
        candidate_row = MarketReviewStore._candidate_to_row(trade_date, candidate)
        signal_row = MarketReviewStore._signal_to_row(trade_date, signal)

        store = object.__new__(MarketReviewStore)
        self.assertEqual(80.0, store._sector_from_row(sector_row).score_breakdown["ladder_completeness"])
        self.assertEqual(75.0, store._candidate_from_row(
            candidate_row,
            {"000001": candidate.stock},
            {"算力": sector},
        ).score_breakdown["next_day_expectation"])
        self.assertEqual(92.0, store._signal_from_row(signal_row).score_breakdown["divergence_quality"])

    def test_market_environment_fetches_realtime_snapshot_for_today(self):
        class FakeAkshare:
            @staticmethod
            def stock_zh_a_spot_em():
                return FakeFrame([
                    {"代码": "000001", "名称": "强势股", "最新价": 11.0, "涨跌幅": 10.01, "成交额": 100_000_000},
                    {"代码": "000002", "名称": "上涨股", "最新价": 8.0, "涨跌幅": 3.2, "成交额": 80_000_000},
                    {"代码": "000003", "名称": "下跌股", "最新价": 7.0, "涨跌幅": -2.1, "成交额": 60_000_000},
                    {"代码": "000004", "名称": "跌停股", "最新价": 6.0, "涨跌幅": -10.0, "成交额": 50_000_000},
                ])

        service = MarketReviewService()
        service._now = lambda: datetime(2026, 5, 25, 11, 0, 0)
        pool = [
            LimitUpStock(code="000001", name="强势股", industry="算力", consecutive_boards=2),
        ]

        with patch.object(service, "_load_akshare", return_value=FakeAkshare):
            environment = service.market_environment("2026-05-25", pool, refresh=True)

        self.assertEqual("stock_zh_a_spot_em", environment.source)
        self.assertEqual(290_000_000, environment.total_amount)
        self.assertEqual(2, environment.rise_count)
        self.assertEqual(2, environment.fall_count)
        self.assertEqual(1, environment.limit_down_count)
        self.assertGreater(environment.environment_score, 0)

    def test_market_environment_uses_pool_fallback_for_history(self):
        service = MarketReviewService()
        service._now = lambda: datetime(2026, 5, 25, 11, 0, 0)
        pool = [
            LimitUpStock(
                code="000001",
                name="历史涨停",
                industry="机器人",
                amount=100_000_000,
                consecutive_boards=3,
            )
        ]

        environment = service.market_environment("2026-05-22", pool, refresh=True)

        self.assertEqual("limit_up_pool", environment.source)
        self.assertEqual(100_000_000, environment.total_amount)
        self.assertEqual(1, environment.limit_up_count)
        self.assertEqual(3, environment.max_boards)

    def test_market_environment_score_uses_real_breadth_and_limit_ratio(self):
        service = MarketReviewService()
        pool = [
            LimitUpStock(code="000001", name="龙头", industry="机器人", consecutive_boards=3),
            LimitUpStock(code="000002", name="助攻", industry="机器人", consecutive_boards=2),
        ]
        strong = MarketEnvironment(
            trade_date="2026-05-25",
            total_amount=2_800_000_000_000,
            rise_count=3600,
            fall_count=1200,
            limit_up_count=90,
            limit_down_count=3,
            max_boards=5,
            source="test",
        )
        weak = MarketEnvironment(
            trade_date="2026-05-25",
            total_amount=700_000_000_000,
            rise_count=1200,
            fall_count=3600,
            limit_up_count=20,
            limit_down_count=30,
            max_boards=2,
            source="test",
        )

        strong.environment_score = service._calculate_market_environment_score(strong, pool)
        weak.environment_score = service._calculate_market_environment_score(weak, pool)

        self.assertGreater(strong.environment_score, weak.environment_score + 30)


if __name__ == "__main__":
    unittest.main()
