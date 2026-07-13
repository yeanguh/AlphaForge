import unittest
from unittest import mock

from scripts.run_full_loop import _input_quality_issues, candidate_symbols_from_pipeline, merge_candidate_market_data


class CandidateMarketDataTest(unittest.TestCase):
    def test_candidate_symbols_from_bottleneck_companies(self) -> None:
        pipeline = {
            "selected_industry_chain": {
                "bottleneck_candidates": [
                    {"companies": "兴森科技、安集科技"},
                    {"companies": "通富微电, 寒武纪"},
                ]
            }
        }

        self.assertEqual(
            candidate_symbols_from_pipeline(pipeline),
            ["002436", "688019", "002156", "688256"],
        )

    def test_merge_candidate_market_data_fetches_missing_symbols(self) -> None:
        pipeline = {"selected_industry_chain": {"bottleneck_candidates": [{"companies": "兴森科技"}]}}
        errors: list[str] = []

        with mock.patch("scripts.run_full_loop.a_stock_data.fetch_quote", return_value={"symbol": "002436", "name": "兴森科技"}), mock.patch(
            "scripts.run_full_loop.a_stock_data.fetch_stock_supplement_resilient",
            return_value={"symbol": "002436", "financials": {}, "announcements": {}, "fund_flow": {}, "dragon_tiger": {}, "research_reports": {}},
        ):
            quotes, supplements = merge_candidate_market_data(
                quotes=[],
                stock_supplements={},
                pipeline=pipeline,
                errors=errors,
            )

        self.assertEqual(errors, [])
        self.assertEqual(quotes[0]["symbol"], "002436")
        self.assertIn("002436", supplements)

    def test_merge_candidate_market_data_uses_cached_supplement_fallback(self) -> None:
        pipeline = {"selected_industry_chain": {"bottleneck_candidates": [{"companies": "兴森科技"}]}}
        errors: list[str] = []
        cached = {"symbol": "002436", "price_history": {"rows": [{"date": "2026-01-01", "open": 10, "close": 11, "high": 12, "low": 9}]}}

        with mock.patch("scripts.run_full_loop.a_stock_data.fetch_quote", return_value={"symbol": "002436", "name": "兴森科技"}), mock.patch(
            "scripts.run_full_loop.a_stock_data.fetch_stock_supplement_resilient",
            return_value=cached,
        ):
            _, supplements = merge_candidate_market_data(
                quotes=[],
                stock_supplements={},
                pipeline=pipeline,
                errors=errors,
            )

        self.assertEqual(errors, [])
        self.assertEqual(supplements["002436"]["price_history"]["rows"][0]["close"], 11)

    def test_deterministic_fallback_review_does_not_block_quality_gate(self) -> None:
        payload = {
            "status": "ok",
            "errors": [],
            "a_share_quotes": [{"symbol": "002436"}],
            "global_charts": [{"symbol": "AAPL"}],
            "news": {"headlines": [{"title": "news"}]},
            "industry_reports": [{"title": "report"}],
            "research_pipeline": {
                "hotspot_scoring": {"selected": {"theme": "ai-compute-infra"}},
                "stock_analyzer": [{"symbol": "002436"}],
                "trade_decision_engine": {"decisions": [{"symbol": "002436"}]},
            },
            "agent_review": {
                "agent_provider": "deterministic_fallback",
                "roles": {"bull": ["ok"]},
                "agent_errors": ["openai_compatible: malformed json"],
            },
        }

        self.assertNotIn("agent_review_not_usable", _input_quality_issues(payload))


if __name__ == "__main__":
    unittest.main()
