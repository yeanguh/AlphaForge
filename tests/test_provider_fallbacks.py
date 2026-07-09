import unittest
from unittest import mock

from providers.open_source import a_stock_data, global_stock_data, wen_cai


class ProviderFallbackTest(unittest.TestCase):
    def test_a_share_quote_falls_back_after_tencent_failure(self) -> None:
        with (
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
