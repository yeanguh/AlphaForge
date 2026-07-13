import tempfile
import unittest
from pathlib import Path
from unittest import mock

from loop_os.domain.evidence_service import write_evidence
from providers.open_source import vibe_research, vibe_trading
from scripts import generate_physical_ai_chain_report as physical_report
from scripts import generate_theme_deep_report as theme_report
from scripts.run_full_loop import collect_provider_insights


def _payload() -> dict:
    return {
        "started_at": "2026-07-09T00:00:00+00:00",
        "finished_at": "2026-07-09T00:05:00+00:00",
        "cycle": 1,
        "a_share_quotes": [{"symbol": "688017", "name": "绿的谐波", "price": 120.0}],
        "stock_supplements": {
            "688017": {
                "price_history": {"rows": [{"date": "2026-07-01", "open": 10, "close": 11, "high": 12, "low": 9}] * 80},
                "financials": {"statements": {"indicators": [{"REPORT_DATE_NAME": "2026Q1"}]}},
                "research_reports": {"rows": [{"title": "人形机器人链跟踪"}]},
            }
        },
        "evidence_ids": ["ev-provider-abc", "ev-market-cn-abc"],
    }


def _pipeline() -> dict:
    return {
        "selected_industry_chain": {"selected_theme": "physical-ai", "score": 42},
        "stock_analyzer": [
            {
                "symbol": "688017",
                "name": "绿的谐波",
                "valuation": {"pe": 120, "pb": 8},
                "technical": {"score": 3.5},
            }
        ],
        "trade_decision_engine": {
            "decisions": [{"symbol": "688017", "name": "绿的谐波", "action": "reject_or_wait", "passed_conditions": 2}]
        },
    }


class ExternalProviderLoopIntegrationTest(unittest.TestCase):
    def test_vibe_research_packet_reuses_loop_market_data(self) -> None:
        packet = vibe_research.research_packet(_payload(), _pipeline())

        self.assertEqual(packet["status"], "ok")
        self.assertFalse(packet["state_mutation_allowed"])
        self.assertEqual(packet["coverage"][0]["symbol"], "688017")
        self.assertGreaterEqual(packet["coverage"][0]["history_rows"], 60)
        self.assertTrue(packet["claims"])

    def test_vibe_trading_packet_reuses_decision_engine_output(self) -> None:
        packet = vibe_trading.strategy_packet(_payload(), _pipeline())

        self.assertEqual(packet["status"], "ok")
        self.assertFalse(packet["state_mutation_allowed"])
        self.assertEqual(packet["risk_rows"][0]["symbol"], "688017")
        self.assertIn("local-cache", packet["risk_rows"][0]["source_priority"])
        self.assertIn("OPENAI_API_KEY", packet["routing_policy"]["key_gated"])

    def test_collect_provider_insights_is_nonblocking_on_adapter_failure(self) -> None:
        with mock.patch("scripts.run_full_loop.vibe_research.research_packet", side_effect=RuntimeError("adapter down")):
            insights = collect_provider_insights(_payload(), _pipeline(), {"portfolio_rating": "Hold", "trader_action": "Hold"})

        self.assertEqual(insights["status"], "warn")
        self.assertFalse(insights["blocking"])
        self.assertEqual(insights["providers"]["vibe_research"]["status"], "warn")
        self.assertEqual(insights["providers"]["vibe_trading"]["status"], "ok")
        self.assertEqual(insights["providers"]["tradingagents_astock"]["status"], "ok")

    def test_provider_insights_write_evidence_cards(self) -> None:
        payload = _payload()
        payload["provider_insights"] = collect_provider_insights(
            payload,
            _pipeline(),
            {"portfolio_rating": "Hold", "trader_action": "Hold", "schema_contract": "local_contract"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            evidence_ids = write_evidence(Path(tmp), 1, payload)

        provider_ids = [item for item in evidence_ids if item.startswith("ev-provider")]
        self.assertEqual(len(provider_ids), 3)

    def test_provider_rows_surface_in_theme_and_physical_reports(self) -> None:
        payload = _payload()
        payload["provider_insights"] = collect_provider_insights(
            payload,
            _pipeline(),
            {"portfolio_rating": "Underweight", "trader_action": "Hold", "schema_contract": "local_contract"},
        )

        generic_rows = theme_report.provider_insight_rows(payload)
        physical_rows = physical_report.provider_insight_rows(payload)

        self.assertEqual(len(generic_rows), 3)
        self.assertEqual(len(physical_rows), 3)
        self.assertTrue(any(row[0] == "投委会复核" for row in physical_rows))


if __name__ == "__main__":
    unittest.main()
