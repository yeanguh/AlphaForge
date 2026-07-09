import tempfile
import unittest
from pathlib import Path

from loop_os.report_router import (
    LOOP_LOG_HEADER,
    WATCH_POOL_HEADER,
    REVISION_HEADER,
    STRENGTH_MAIN_THRESHOLD,
    resolve_theme_key,
    theme_tier,
    route_cycle_reports,
)


def _strong_payload(**overrides):
    """A cycle payload whose candidate strength clears STRENGTH_MAIN_THRESHOLD."""
    payload = {
        "run_id": "run-A",
        "cycle": 1,
        "status": "ok",
        "started_at": "2026-07-09T00:00:00+00:00",
        "finished_at": "2026-07-09T00:05:00+00:00",
        "errors": [],
        "evidence_ids": [f"ev-{i}" for i in range(8)],
        "industry_reports": [
            {"org": "券商A", "title": "机器人减速器深度"},
            {"org": "券商B", "title": "丝杠国产替代"},
        ],
        "news": {"headlines": [{"source": "S1", "title": "人形机器人量产提速"}]},
        "agent_review": {
            "roles": ["bull", "bear"],
            "reason": "产业链进入订单验证期",
            "next_actions": ["核验收入占比", "补估值分位"],
        },
        "stock_supplements": {
            "600519": {
                "symbol": "600519",
                "fundamental": {},
                "fund_flow": {},
                "dragon_tiger": {"rows": []},
                "catalysts": ["Q1营收+43%"],
                "risks": ["估值偏高"],
            }
        },
        "research_pipeline": {
            "selected_industry_chain": {
                "selected_theme": "ai_physical_ai",
                "score": 34,
                "stage": "industry-chain-mapper",
                "next_verifications": ["验证订单来源"],
                "bottleneck_screen": {
                    "candidates": [
                        {"link": "精密传动", "companies": "绿的谐波", "invalidation": "订单不及预期"}
                    ]
                },
            },
            "stock_analyzer": [
                {
                    "symbol": "600519",
                    "name": "贵州茅台",
                    "business_model": "白酒龙头",
                    "valuation": {"pe": 18.1, "pb": 6.4, "band": "normal", "score": 4, "method": "PE/PB snapshot"},
                    "catalyst": [],
                    "risk": [],
                }
            ],
            "trade_decision_engine": {
                "decisions": [
                    {"symbol": "600519", "action": "watch", "passed_conditions": 5, "min_risk_reward": 2.0}
                ]
            },
            "company_mapping": {"600519": "sample"},
        },
    }
    payload.update(overrides)
    return payload


class ReportRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        # 方案 A:themes 统一取代 industry。预置一份已迁移的人工正文主题报告,
        # loop 应在其正文之上追加证据日志 / 观察池 / 判断修正,而永不覆盖人工正文。
        self.theme_report = self.root / "reports" / "themes" / "physical-ai" / "report.md"
        self.theme_report.parent.mkdir(parents=True)
        self.theme_report.write_text(
            "# Physical AI 主题最终报告\n\n## 0. 核心结论\n\n人工撰写的正文结论。\n",
            encoding="utf-8",
        )
        # 遗留 industry 报告:方案 A 下已迁移为来源,日常 loop 绝不触碰它(验证 loop 不写 industry)
        ind = self.root / "reports" / "industry" / "physical-ai-chain-analysis-2026-07-09"
        ind.mkdir(parents=True)
        (ind / "report.md").write_text(
            "# 物理AI产业链报告(人工深度版)\n\n## 0. 核心结论\n\n产业链人工正文。\n",
            encoding="utf-8",
        )
        self.legacy_industry_report = ind / "report.md"
        # cycle dir must live under root for update_rolling_report's relative_to()
        self.cycle_dir = self.root / "runs" / "run-A" / "cycle-001"
        self.cycle_dir.mkdir(parents=True)
        (self.cycle_dir / "report.md").write_text("# 单轮候选报告\n\n过程内容。\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- 主题解析:alias / tier --
    def test_theme_resolution_and_tier(self) -> None:
        self.assertEqual(resolve_theme_key("ai_physical_ai"), "physical-ai")
        self.assertEqual(theme_tier("physical-ai"), "core")
        self.assertEqual(theme_tier("quantum-computing"), "emerging")
        self.assertEqual(theme_tier("edge-ai"), "watch")
        self.assertIsNone(resolve_theme_key(""))

    # -- 失败轮次只留在 runs/ --
    def test_failed_cycle_writes_no_final_report(self) -> None:
        payload = _strong_payload(status="error", errors=["boom"])
        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=["status=error"])
        self.assertEqual(res["routed"], [])
        self.assertTrue(res["skipped"])
        self.assertEqual(res["skipped"][0]["reason"], "failed_cycle_stays_in_runs")
        # 主题报告仍是人工正文,失败轮次不得追加证据日志
        body = self.theme_report.read_text(encoding="utf-8")
        self.assertIn("人工撰写的正文结论", body)
        self.assertNotIn(LOOP_LOG_HEADER, body)
        self.assertFalse((self.root / "reports" / "stocks").exists() and any((self.root / "reports" / "stocks").iterdir()))

    def test_blocking_issue_treated_as_failed(self) -> None:
        payload = _strong_payload()
        res = route_cycle_reports(
            root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=["agent_review_not_usable"]
        )
        self.assertEqual(res["routed"], [])

    # -- 强证据 -> themes 主题报告 + 个股 + 周报,均带正文日志 --
    def test_strong_cycle_routes_to_final_reports(self) -> None:
        payload = _strong_payload()
        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        self.assertGreaterEqual(res["strength"], STRENGTH_MAIN_THRESHOLD)
        self.assertFalse(res["to_watch_pool"])
        self.assertEqual(res["theme_key"], "physical-ai")
        self.assertEqual(res["tier"], "core")
        scopes = {r.get("scope") for r in res["routed"]}
        self.assertIn("theme:physical-ai", scopes)
        self.assertIn("stock:600519", scopes)
        self.assertIn("weekly", scopes)

        # theme: 人工正文保留 + loop 日志追加,不进观察池
        th = self.theme_report.read_text(encoding="utf-8")
        self.assertIn("人工撰写的正文结论", th)  # 人工正文被保留,不被覆盖
        self.assertIn(LOOP_LOG_HEADER, th)
        self.assertNotIn(WATCH_POOL_HEADER, th)
        self.assertIn("ai_physical_ai", th)

        # 方案 A:遗留 reports/industry/ 已迁移,日常 loop 绝不再触碰(人工深度版原样保留)
        legacy = self.legacy_industry_report.read_text(encoding="utf-8")
        self.assertIn("产业链人工正文", legacy)
        self.assertNotIn(LOOP_LOG_HEADER, legacy)

        # 个股最终报告
        stock = self.root / "reports" / "stocks" / "600519" / "report.md"
        self.assertTrue(stock.exists())
        stext = stock.read_text(encoding="utf-8")
        self.assertIn("贵州茅台", stext)
        self.assertIn("PE 18.1", stext)

        # 周报累积文件
        weekly = self.root / "reports" / "weekly" / "2026-W28.md"
        self.assertTrue(weekly.exists())

        # daily 降级为增量 inbox
        inbox = self.root / "reports" / "daily" / "latest-full-loop.md"
        self.assertTrue(inbox.exists())

    # -- emerging 主题即使 strength 达标也默认进观察池(需事件才升正文) --
    def test_emerging_theme_defaults_to_watch_pool(self) -> None:
        payload = _strong_payload()
        payload["research_pipeline"]["selected_industry_chain"]["selected_theme"] = "quantum"
        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        self.assertEqual(res["theme_key"], "quantum-computing")
        self.assertEqual(res["tier"], "emerging")
        theme_report = self.root / "reports" / "themes" / "quantum-computing" / "report.md"
        self.assertTrue(theme_report.exists())
        txt = theme_report.read_text(encoding="utf-8")
        self.assertIn(WATCH_POOL_HEADER, txt)  # emerging 默认观察池

    # -- 低质量线索 -> 观察池,不进正文 --
    def test_weak_cycle_goes_to_watch_pool(self) -> None:
        weak = {
            "run_id": "run-W",
            "cycle": 2,
            "status": "ok",
            "started_at": "2026-07-09T00:00:00+00:00",
            "finished_at": "2026-07-09T00:05:00+00:00",
            "errors": [],
            "evidence_ids": [],
            "industry_reports": [],
            "news": {"headlines": [{"source": "S", "title": "边缘线索"}]},
            "agent_review": {},
            "stock_supplements": {},
            "research_pipeline": {"selected_industry_chain": {"selected_theme": "ai_physical_ai"}},
        }
        res = route_cycle_reports(root=self.root, payload=weak, cycle_dir=self.cycle_dir, issues=["missing_evidence_ids"])
        self.assertLess(res["strength"], STRENGTH_MAIN_THRESHOLD)
        self.assertTrue(res["to_watch_pool"])
        th = self.theme_report.read_text(encoding="utf-8")
        self.assertIn("人工撰写的正文结论", th)  # 正文结论不被覆盖
        self.assertIn(WATCH_POOL_HEADER, th)
        self.assertIn("边缘线索", th)

    # -- 修正旧判断:软标记(删除线)沉淀,人工正文保留 --
    def test_revision_soft_marks_old_claim(self) -> None:
        payload = _strong_payload()
        payload["agent_review"]["invalidations"] = [
            {"claim": "减速器国产化率已达60%", "reason": "最新调研显示不足40%"}
        ]
        res = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        theme_outcome = next(r for r in res["routed"] if r.get("scope") == "theme:physical-ai")
        self.assertEqual(theme_outcome["revisions"], 1)
        th = self.theme_report.read_text(encoding="utf-8")
        self.assertIn(REVISION_HEADER, th)
        self.assertIn("~~减速器国产化率已达60%~~", th)
        self.assertIn("人工撰写的正文结论", th)  # 正文永不物理删除

    # -- 幂等:同一轮重复路由不重复追加 --
    def test_idempotent(self) -> None:
        payload = _strong_payload()
        route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        res2 = route_cycle_reports(root=self.root, payload=payload, cycle_dir=self.cycle_dir, issues=[])
        self.assertTrue(all(r.get("status") == "skipped" for r in res2["routed"]))
        th = self.theme_report.read_text(encoding="utf-8")
        self.assertEqual(th.count("research-os-curation:theme:physical-ai:run-A:1"), 1)


if __name__ == "__main__":
    unittest.main()
