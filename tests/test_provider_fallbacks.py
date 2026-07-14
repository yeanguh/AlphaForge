import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from providers.open_source import a_stock_data, global_stock_data, wen_cai


class ProviderFallbackTest(unittest.TestCase):
    def test_a_share_quote_falls_back_after_tencent_failure(self) -> None:
        with (
            mock.patch.object(a_stock_data, "fetch_quote_tushare", side_effect=RuntimeError("tushare down")),
            mock.patch.object(a_stock_data, "_tencent_a_quote", side_effect=RuntimeError("tencent down")) as tencent,
            mock.patch.object(
                a_stock_data,
                "_eastmoney_a_quote",
                return_value={"symbol": "600519", "source": "eastmoney_push2", "price": 1.0},
            ) as eastmoney,
        ):
            quote = a_stock_data.fetch_quote("600519")
        self.assertEqual(quote["source"], "eastmoney_push2")
        self.assertIn("fallback_errors", quote)
        tencent.assert_called_once_with("600519")
        eastmoney.assert_called_once_with("600519")

    def test_a_share_quote_prefers_tushare_when_available(self) -> None:
        tushare_quote = {"symbol": "600519", "source": "tushare_priority", "price": 1.0}
        with (
            mock.patch.object(a_stock_data, "fetch_quote_tushare", return_value=tushare_quote) as tushare,
            mock.patch.object(a_stock_data, "_tencent_a_quote") as tencent,
        ):
            quote = a_stock_data.fetch_quote("600519")

        self.assertEqual(quote["source"], "tushare_priority")
        tushare.assert_called_once_with("600519")
        tencent.assert_not_called()

    def test_price_history_success_writes_local_cache(self) -> None:
        rows = [
            {"date": f"2026-01-{idx:02d}", "open": 10 + idx, "close": 11 + idx, "high": 12 + idx, "low": 9 + idx, "volume": 1000, "turnover": 2000, "change_pct": 1.0}
            for idx in range(1, 8)
        ]
        with TemporaryDirectory() as tmp, mock.patch.object(a_stock_data, "LOCAL_A_DATA", Path(tmp)):
            a_stock_data._write_price_history_cache("600519", rows)

            cached = a_stock_data.fetch_price_history_fallback("600519", days=5)

        self.assertEqual(cached["source"], "local_a_data_hist")
        self.assertEqual(len(cached["rows"]), 5)
        self.assertEqual(cached["rows"][-1]["close"], 18.0)

    def test_cached_price_history_refreshes_when_stale(self) -> None:
        cached = {
            "symbol": "600519",
            "source": "local_a_data_hist",
            "rows": [{"date": "2026-07-09", "open": 10, "close": 11, "high": 12, "low": 9}],
        }
        fresh = {
            "symbol": "600519",
            "source": "tencent_qfq_kline",
            "rows": [{"date": "2026-07-14", "open": 12, "close": 13, "high": 14, "low": 11}],
        }
        with (
            mock.patch.object(a_stock_data, "fetch_price_history_fallback", return_value=cached),
            mock.patch.object(a_stock_data, "latest_expected_trade_date", return_value="20260714"),
            mock.patch.object(a_stock_data, "fetch_price_history_tushare", side_effect=RuntimeError("tushare down")),
            mock.patch.object(a_stock_data, "fetch_price_history_tencent", return_value=fresh) as tencent,
        ):
            history = a_stock_data.fetch_price_history_cached_or_live("600519")

        self.assertEqual(history["source"], "tencent_qfq_kline")
        self.assertTrue(history["refreshed_cache"])
        tencent.assert_called_once()

    def test_cached_price_history_returns_stale_cache_when_refresh_fails(self) -> None:
        cached = {
            "symbol": "600519",
            "source": "local_a_data_hist",
            "rows": [{"date": "2026-07-09", "open": 10, "close": 11, "high": 12, "low": 9}],
        }
        with (
            mock.patch.object(a_stock_data, "fetch_price_history_fallback", return_value=cached),
            mock.patch.object(a_stock_data, "latest_expected_trade_date", return_value="20260714"),
            mock.patch.object(a_stock_data, "fetch_price_history_tushare", side_effect=RuntimeError("tushare down")),
            mock.patch.object(a_stock_data, "fetch_price_history_tencent", side_effect=RuntimeError("tencent down")),
            mock.patch.object(a_stock_data, "fetch_price_history_efinance", side_effect=RuntimeError("efinance down")),
            mock.patch.object(a_stock_data, "fetch_price_history_baostock", side_effect=RuntimeError("baostock down")),
        ):
            history = a_stock_data.fetch_price_history_cached_or_live("600519")

        self.assertTrue(history["stale_cache"])
        self.assertTrue(history["refresh_errors"])

    def test_quote_success_writes_local_cache(self) -> None:
        quote = {"symbol": "600519", "name": "贵州茅台", "price": 1800.0, "pe": 25.0, "pb": 8.0, "source": "tencent_finance"}
        with TemporaryDirectory() as tmp, mock.patch.object(a_stock_data, "LOCAL_A_DATA", Path(tmp)):
            a_stock_data._write_quote_cache("600519", quote)

            cached = a_stock_data.fetch_quote_fallback("600519")

        self.assertEqual(cached["source"], "tencent_finance")
        self.assertEqual(cached["pe"], 25.0)

    def test_supplement_success_writes_local_cache(self) -> None:
        supplement = {"symbol": "600519", "financials": {"statements": {"indicators": [{"REPORT_DATE_NAME": "2026Q1"}]}}}
        with TemporaryDirectory() as tmp, mock.patch.object(a_stock_data, "LOCAL_A_DATA", Path(tmp)):
            a_stock_data._write_supplement_cache("600519", supplement)

            cached = a_stock_data.fetch_stock_supplement_fallback("600519")

        self.assertEqual(cached["financials"]["statements"]["indicators"][0]["REPORT_DATE_NAME"], "2026Q1")

    def test_stock_supplement_price_history_uses_extended_fallbacks(self) -> None:
        history = {
            "symbol": "600519",
            "source": "efinance_quote_history",
            "rows": [
                {"date": f"2026-01-{idx:02d}", "open": 10 + idx, "close": 11 + idx, "high": 12 + idx, "low": 9 + idx}
                for idx in range(1, 25)
            ],
        }
        with (
            mock.patch.object(a_stock_data, "fetch_basic_info", return_value={}),
            mock.patch.object(a_stock_data, "fetch_fund_flow", return_value={}),
            mock.patch.object(a_stock_data, "fetch_price_history", side_effect=RuntimeError("eastmoney empty")),
            mock.patch.object(a_stock_data, "fetch_price_history_tencent", side_effect=RuntimeError("tencent empty")),
            mock.patch.object(a_stock_data, "fetch_price_history_efinance", return_value=history),
            mock.patch.object(a_stock_data, "fetch_dragon_tiger", return_value={}),
            mock.patch.object(a_stock_data, "fetch_announcements", return_value={}),
            mock.patch.object(a_stock_data, "fetch_financials", return_value={}),
            mock.patch.object(a_stock_data, "fetch_stock_research_reports", return_value={}),
        ):
            supplement = a_stock_data.fetch_stock_supplement("600519")

        self.assertEqual(supplement["price_history"]["source"], "efinance_quote_history")
        self.assertTrue(any("price_history:" in err for err in supplement["errors"]))

    def test_stock_supplement_resilient_uses_local_cache_after_live_failure(self) -> None:
        cached = {
            "symbol": "600519",
            "financials": {"statements": {"indicators": [{"REPORT_DATE_NAME": "2026Q1"}]}},
            "price_history": {"rows": [{"date": "2026-01-01", "open": 10, "close": 11, "high": 12, "low": 9}]},
        }
        with (
            mock.patch.object(a_stock_data, "fetch_stock_supplement_tushare", side_effect=RuntimeError("tushare down")),
            mock.patch.object(a_stock_data, "fetch_stock_supplement", side_effect=RuntimeError("live down")),
            mock.patch.object(a_stock_data, "fetch_stock_supplement_fallback", return_value=cached),
        ):
            supplement = a_stock_data.fetch_stock_supplement_resilient("600519")

        self.assertEqual(supplement["financials"]["statements"]["indicators"][0]["REPORT_DATE_NAME"], "2026Q1")
        self.assertTrue(a_stock_data.stock_supplement_usable(supplement))

    def test_stock_supplement_resilient_backfills_live_holes_from_cache(self) -> None:
        live = {"symbol": "600519", "fundamental": {"name": "贵州茅台"}, "price_history": {"source": "empty"}, "errors": ["price_history timeout"]}
        cached = {"symbol": "600519", "price_history": {"source": "local_a_data_hist", "rows": [{"date": "2026-01-01", "open": 10, "close": 11, "high": 12, "low": 9}]}}
        with (
            mock.patch.object(a_stock_data, "fetch_stock_supplement_tushare", side_effect=RuntimeError("tushare down")),
            mock.patch.object(a_stock_data, "fetch_stock_supplement", return_value=live),
            mock.patch.object(a_stock_data, "fetch_stock_supplement_fallback", return_value=cached),
        ):
            supplement = a_stock_data.fetch_stock_supplement_resilient("600519")

        self.assertEqual(supplement["price_history"]["source"], "local_a_data_hist")
        self.assertTrue(supplement["cache_backfilled"])

    def test_stock_supplement_resilient_prefers_tushare_and_backfills_public(self) -> None:
        tushare = {
            "symbol": "600519",
            "source": "tushare_priority",
            "financials": {"statements": {"income": [{"end_date": "20260331"}]}},
            "price_history": {"source": "tushare_priority", "rows": [{"date": "2026-01-01", "open": 10, "close": 11, "high": 12, "low": 9}]},
        }
        public = {"symbol": "600519", "research_reports": {"rows": [{"title": "深度报告"}]}}
        with (
            mock.patch.object(a_stock_data, "fetch_stock_supplement_tushare", return_value=tushare),
            mock.patch.object(a_stock_data, "fetch_stock_supplement_public_backfill", return_value=public),
            mock.patch.object(a_stock_data, "fetch_stock_supplement") as public_full,
            mock.patch.object(a_stock_data, "fetch_stock_supplement_fallback", side_effect=RuntimeError("cache missing")),
        ):
            supplement = a_stock_data.fetch_stock_supplement_resilient("600519")

        self.assertEqual(supplement["source"], "tushare_priority")
        self.assertEqual(supplement["financials"]["statements"]["income"][0]["end_date"], "20260331")
        self.assertEqual(supplement["research_reports"]["rows"][0]["title"], "深度报告")
        public_full.assert_not_called()

    def test_fund_flow_fallback_uses_margin_trading_proxy(self) -> None:
        margin = {"symbol": "600519", "source": "vibe_research_margin_trading", "rows": [{"date": "2026-07-09", "rzye": 1}]}
        with (
            mock.patch.object(a_stock_data, "fetch_fund_flow_vibe", side_effect=RuntimeError("fund flow empty")),
            mock.patch.object(a_stock_data, "fetch_margin_trading_vibe", return_value=margin),
        ):
            fallback = a_stock_data.fetch_liquidity_fallback("600519")

        self.assertEqual(fallback["source"], "vibe_research_margin_trading")
        self.assertTrue(fallback["proxy"])
        self.assertIn("fallback_errors", fallback)

    def test_dragon_tiger_empty_daily_falls_back_to_vibe_lookback(self) -> None:
        with (
            mock.patch.object(a_stock_data, "_get_json_retry", return_value={"result": {"data": []}}),
            mock.patch.object(
                a_stock_data,
                "fetch_dragon_tiger_vibe",
                return_value={"symbol": "002436", "source": "vibe_research_dragon_tiger_30d", "rows": [{"date": "2026-06-18"}]},
            ) as vibe,
        ):
            result = a_stock_data.fetch_dragon_tiger("002436", date="2026-07-10")

        self.assertEqual(result["source"], "vibe_research_dragon_tiger_30d")
        self.assertEqual(len(result["rows"]), 1)
        vibe.assert_called_once_with("002436", date="2026-07-10")

    def test_global_chart_falls_back_to_tencent_after_yahoo_failure(self) -> None:
        with (
            mock.patch.object(global_stock_data, "_yahoo_chart", side_effect=RuntimeError("yahoo down")),
            mock.patch.object(
                global_stock_data,
                "_tencent_us_quote",
                return_value={"symbol": "AAPL", "source": "tencent_us_quote", "latest_close": 1.0},
            ),
        ):
            chart = global_stock_data.fetch_chart("AAPL")
        self.assertEqual(chart["source"], "tencent_us_quote")
        self.assertIn("fallback_reason", chart)

    def test_wen_cai_skips_without_api_key(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            result = wen_cai.query("report", "人形机器人 研报")
        self.assertEqual(result["status"], "skipped")
        self.assertIn("IWENCAI_API_KEY", result["reason"])

    def test_wen_cai_summary_counts_datas(self) -> None:
        enrichment = {
            "results": {
                "sample": {
                    "status": "ok",
                    "qtype": "business",
                    "query": "绿的谐波 主营业务",
                    "stdout": {"datas": [{"股票简称": "绿的谐波", "主营业务": "精密传动"}]},
                }
            }
        }
        rows = wen_cai.summarize_enrichment(enrichment)
        self.assertEqual(rows[0]["count"], 1)
        self.assertEqual(rows[0]["sample"], "绿的谐波")

    def test_wen_cai_live_quota_exhausted_is_warn(self) -> None:
        with (
            mock.patch.object(wen_cai, "skill_available", return_value=True),
            mock.patch.object(wen_cai, "is_configured", return_value=True),
            mock.patch.object(
                wen_cai,
                "query",
                return_value={"status": "error", "stderr": "您今天的次数已用完"},
            ),
        ):
            result = wen_cai.smoke(live=True)

        self.assertEqual(result.status, "warn")
