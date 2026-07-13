import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import run_full_loop


class LatestPublishTest(unittest.TestCase):
    def test_selected_theme_key_resolves_configured_theme(self) -> None:
        payload = {
            "research_pipeline": {
                "selected_industry_chain": {"selected_theme": "ai_compute_infra"}
            }
        }

        self.assertEqual(run_full_loop.selected_theme_key(payload), "ai-compute-infra")

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

    def test_cleanup_theme_drafts_removes_only_current_run_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            theme = root / "reports" / "themes" / "ai-compute-infra"
            drafts = theme / "drafts"
            run_report = root / "runs" / "2026-07-10" / "full-loop-abc" / "cycle-001" / "report.md"
            drafts.mkdir(parents=True)
            run_report.parent.mkdir(parents=True)
            current_peer = theme / "report.cycle-draft-full-loop-abc-cycle-001.md"
            current_archive = drafts / "full-loop-abc-cycle-001.md"
            other_peer = theme / "report.cycle-draft-full-loop-other-cycle-001.md"
            canonical = theme / "report.md"
            change_log = theme / "report_change_log.md"
            for path in (current_peer, current_archive, other_peer, canonical, change_log, run_report):
                path.write_text(path.name, encoding="utf-8")

            with mock.patch.object(run_full_loop, "ROOT", root):
                cleanup = run_full_loop.cleanup_theme_drafts(root, "full-loop-abc")

            self.assertEqual(cleanup["removed"], 2)
            self.assertFalse(current_peer.exists())
            self.assertFalse(current_archive.exists())
            self.assertTrue(other_peer.exists())
            self.assertTrue(canonical.exists())
            self.assertTrue(change_log.exists())
            self.assertTrue(run_report.exists())


if __name__ == "__main__":
    unittest.main()
