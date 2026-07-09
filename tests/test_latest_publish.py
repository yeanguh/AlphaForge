import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import run_full_loop


class LatestPublishTest(unittest.TestCase):
    def test_error_cycle_does_not_overwrite_or_merge_into_latest_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest_json = root / "data" / "raw" / "latest-full-loop.json"
            observed_json = root / "data" / "raw" / "latest-observed-full-loop.json"
            latest_report = root / "reports" / "daily" / "latest-full-loop.md"
            latest_ops = root / "reports" / "daily" / "latest-ops.md"
            cycle_dir = root / "runs" / "2026-07-09" / "full-loop-test" / "cycle-001"
            latest_json.parent.mkdir(parents=True)
            latest_report.parent.mkdir(parents=True)
            cycle_dir.mkdir(parents=True)
            latest_json.write_text(json.dumps({"status": "ok", "marker": "good"}), encoding="utf-8")
            latest_report.write_text("# good report\n\n既有高质量内容。\n", encoding="utf-8")
            latest_ops.write_text("good ops\n", encoding="utf-8")
            (cycle_dir / "report.md").write_text("# bad cycle report\n\n本轮诊断内容。\n", encoding="utf-8")

            bad_payload = {
                "run_id": "full-loop-test",
                "cycle": 1,
                "status": "error",
                "errors": ["a_share_quotes: timeout"],
                "a_share_quotes": [],
                "global_charts": [],
                "news": {"headlines": []},
                "industry_reports": [],
                "research_pipeline": {},
                "agent_review": {},
                "harness": {"status": "error"},
                "theme_deep_report": {"returncode": 0},
            }

            with mock.patch.object(run_full_loop, "ROOT", root):
                published = run_full_loop.publish_latest_artifacts(bad_payload, cycle_dir)

            self.assertFalse(published)
            self.assertFalse(bad_payload["latest_publish"]["eligible"])
            self.assertEqual(json.loads(latest_json.read_text(encoding="utf-8"))["marker"], "good")
            self.assertEqual(json.loads(observed_json.read_text(encoding="utf-8"))["status"], "error")
            latest_text = latest_report.read_text(encoding="utf-8")
            self.assertIn("既有高质量内容。", latest_text)
            self.assertNotIn("## 滚动修订记录", latest_text)
            self.assertNotIn("本轮限制", latest_text)
            self.assertNotIn("runs/", latest_text)
            self.assertEqual(latest_ops.read_text(encoding="utf-8"), "good ops\n")

    def test_healthy_cycle_merges_increment_without_replacing_report_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest_report = root / "reports" / "daily" / "latest-full-loop.md"
            cycle_dir = root / "runs" / "2026-07-09" / "full-loop-test" / "cycle-001"
            latest_report.parent.mkdir(parents=True)
            cycle_dir.mkdir(parents=True)
            latest_report.write_text("# good report\n\n既有高质量内容。\n", encoding="utf-8")
            (cycle_dir / "report.md").write_text("# candidate report\n\n候选内容。\n", encoding="utf-8")

            healthy_payload = {
                "run_id": "full-loop-test",
                "cycle": 1,
                "status": "ok",
                "errors": [],
                "a_share_quotes": [{"symbol": "688017", "name": "绿的谐波", "change_pct": 1.2}],
                "global_charts": [{"symbol": "AAPL"}],
                "news": {"headlines": [{"source": "公开来源", "title": "AI产业进展"}]},
                "industry_reports": [{"org": "机构", "title": "人形机器人产业链研究"}],
                "research_pipeline": {
                    "hotspot_scoring": {"selected": {"theme": "ai_physical_ai"}},
                    "selected_industry_chain": {
                        "selected_theme": "ai_physical_ai",
                        "score": 42,
                        "company_mapping": [{"公司": "绿的谐波"}],
                    },
                    "stock_analyzer": [{"symbol": "688017"}],
                    "trade_decision_engine": {"decisions": [{"symbol": "688017"}]},
                },
                "agent_review": {"roles": {"bull": ["ok"]}, "reason": "证据增强"},
                "evidence_ids": ["ev-1"],
                "state_transition": {"validated": True, "committed": True},
                "harness": {"status": "ok"},
                "theme_deep_report": {"returncode": 0},
            }

            with mock.patch.object(run_full_loop, "ROOT", root):
                published = run_full_loop.publish_latest_artifacts(healthy_payload, cycle_dir)

            self.assertTrue(published)
            latest_text = latest_report.read_text(encoding="utf-8")
            self.assertIn("既有高质量内容。", latest_text)
            self.assertIn("## 滚动修订记录", latest_text)
            self.assertIn("主线判断更新", latest_text)
            self.assertNotIn("runs/", latest_text)


if __name__ == "__main__":
    unittest.main()
