from __future__ import annotations

import tempfile
import unittest
from subprocess import TimeoutExpired
from pathlib import Path
from unittest.mock import patch

import loop_os.domain.capability_chain as capability_chain
from loop_os.domain.capability_chain import _loads_json_object_from_output, build_research_pipeline
from loop_os.reporting import write_markdown_report


class CapabilityChainTest(unittest.TestCase):
    def test_extracts_json_after_noisy_probe_logs(self) -> None:
        payload = _loads_json_object_from_output('login success!\\nlogout success!\\n{"status":"ok","adapters":{}}\\n')
        self.assertEqual(payload["status"], "ok")

    def test_skill_health_timeout_is_skipped_not_error(self) -> None:
        capability_chain._SKILL_HEALTH_CACHE = None
        root = Path(__file__).resolve().parents[1]
        with patch("loop_os.domain.capability_chain.subprocess.run", side_effect=TimeoutExpired(["probe"], 45)):
            health = capability_chain._run_skill_health_check(root, True, "600519")
        self.assertEqual(health["status"], "skipped")
        self.assertEqual(health["reason"], "check_data_sources.py timeout")
        capability_chain._SKILL_HEALTH_CACHE = None

    def test_selects_highest_weight_theme_and_decision_gate(self) -> None:
        root = Path(__file__).resolve().parents[1]
        payload = {
            "news": {
                "headlines": [
                    {"title": "AI算力带动半导体先进封装需求", "source": "public", "url": "https://example.com/a"},
                    {"title": "机器人产业链设备订单增长", "source": "public", "url": "https://example.com/b"},
                ]
            },
            "industry_reports": [
                {"title": "半导体设备国产替代深度报告", "industry_name": "半导体", "org": "机构A", "publish_date": "2026-07-08", "info_code": "1"},
                {"title": "半导体先进封装基板专题", "industry_name": "半导体", "org": "机构B", "publish_date": "2026-07-08", "info_code": "2"},
            ],
            "a_share_quotes": [
                {"symbol": "600519", "name": "样本A", "pe": 20, "pb": 5, "change_pct": 1.2, "valuation_band": "normal"},
                {"symbol": "300750", "name": "样本B", "pe": 120, "pb": 12, "change_pct": -6, "valuation_band": "high"},
            ],
        }
        pipeline = build_research_pipeline(
            root,
            payload,
            {"600519": {}, "300750": {}},
            {"cash": 1_000_000, "positions": [], "reviews": []},
            {"decision": "watchlist_candidate"},
        )
        self.assertEqual(pipeline["hotspot_scoring"]["selected"]["theme"], "semiconductor")
        self.assertTrue(pipeline["selected_industry_chain"]["skill_manifest"]["files_used"])
        decisions = {item["symbol"]: item for item in pipeline["trade_decision_engine"]["decisions"]}
        self.assertEqual(decisions["600519"]["action"], "paper_candidate")
        self.assertEqual(decisions["300750"]["action"], "reject_or_wait")

    def test_human_report_does_not_expose_internal_refs(self) -> None:
        root = Path(__file__).resolve().parents[1]
        payload = {
            "cycle": 1,
            "a_share_quotes": [{"symbol": "600519", "name": "样本A", "pe": 20, "pb": 5, "change_pct": 1.2, "valuation_band": "normal"}],
            "global_charts": [],
            "news": {"headlines": [{"title": "AI算力新闻", "source": "public", "url": "https://example.com/news"}]},
            "industry_reports": [],
            "industry_analysis": {"catalysts": [], "top_industries": []},
            "agent_review": {"roles": {}, "decision": "needs_more_evidence"},
            "committee_review": {"decision": "needs_more_evidence"},
            "tradingagents_review": {"portfolio_rating": "Hold", "trader_action": "Hold"},
        }
        payload["research_pipeline"] = build_research_pipeline(
            root,
            payload,
            {"600519": {}},
            {"cash": 1_000_000, "positions": [], "reviews": []},
            {"decision": "needs_more_evidence"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            write_markdown_report(path, payload)
            text = path.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", text)
        self.assertNotIn("ev-", text)
        self.assertNotIn("data/raw/", text)
        self.assertNotIn("a-stock-data", text)
        self.assertNotIn("决策门禁", text)
        self.assertNotIn("补充覆盖", text)
        self.assertNotIn("coverage", text.lower())
        self.assertNotIn("TradingAgents", text)
        self.assertNotIn("Underweight", text)
        self.assertNotIn("payload", text)
        self.assertNotIn("明天", text)
        self.assertIn("物理AI产业链深度", text)
        self.assertIn("市场不再无条件奖励所有 AI 暴露", text)
        self.assertIn("核心标的筛选", text)
        self.assertIn("买点框架", text)
        self.assertIn("公开来源", text)
        self.assertIn("https://example.com/news", text)


if __name__ == "__main__":
    unittest.main()
