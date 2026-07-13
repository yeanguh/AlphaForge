import tempfile
import unittest
from pathlib import Path
from unittest import mock

from loop_os.domain.report_review_agent import review_report_text
from scripts import generate_theme_deep_report as gen


class GenericThemeDeepReportTest(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "run_id": "run-A",
            "cycle": 1,
            "finished_at": "2026-07-09T00:05:00+00:00",
            "evidence_ids": ["ev-chain-abc", "ev-market-cn-abc", "ev-report-abc", "ev-review-abc"],
            "a_share_quotes": [{"symbol": "688017", "name": "绿的谐波", "price": 100, "change_pct": 2.3}],
            "industry_reports": [{"title": "电子行业深度：AI算力链跟踪", "org": "券商A"}],
            "news": {"headlines": [{"title": "AI infrastructure demand expands", "source": "公开资讯"}]},
            "research_pipeline": {
                "selected_industry_chain": {
                    "selected_theme": "ai-compute-infra",
                    "score": 30,
                    "chain_map": {
                        "upstream": ["高端基板材料", "先进封装设备", "高速连接"],
                        "midstream": ["IC封装基板", "芯片设计", "AI服务器部件"],
                        "downstream": ["AI服务器", "数据中心", "云厂商资本开支"],
                    },
                    "bottleneck_candidates": [
                        {
                            "link": "先进封装材料与设备",
                            "companies": "兴森科技、安集科技",
                            "catalyst": "订单/公告验证",
                            "invalidation": "收入暴露不足",
                        }
                    ],
                    "core_value_distribution": [
                        {
                            "产业链环节": "上游",
                            "细分领域/关键产品": "先进封装材料与设备",
                            "核心技术壁垒": "认证/良率",
                            "卡脖子程度": "High",
                            "代表A股公司": "兴森科技、安集科技",
                        }
                    ],
                    "company_mapping": [
                        {
                            "公司": "兴森科技",
                            "代码": "002436",
                            "环节": "上游",
                            "细分领域": "封装基板",
                            "产业占比/暴露度": "待公告验证",
                            "核心技术/产品": "IC封装基板",
                            "卡脖子相关性": "High/待验证",
                            "环节地位": "卡口候选",
                        }
                    ],
                },
                "stock_analyzer": [
                    {
                        "symbol": "688017",
                        "name": "绿的谐波",
                        "business_model": "精密传动样本",
                        "valuation": {"pe": 120, "pb": 10},
                    }
                ],
                "trade_decision_engine": {"decisions": [{"symbol": "688017", "action": "watch", "passed_conditions": 4, "min_risk_reward": 2.0}]},
            },
        }

    def test_build_report_has_benchmark_sections_and_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "reports" / "themes" / "ai-compute-infra"
            with mock.patch("scripts.generate_theme_deep_report.ROOT", root):
                report = gen.build_report(self._payload(), "ai-compute-infra", out)

            self.assertIn("## 一句话结论", report)
            self.assertIn("## 投资机会挖掘", report)
            self.assertIn("### 核心节点三公司校验", report)
            self.assertIn("| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |", report)
            self.assertIn("| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |", report)
            self.assertIn("| 候选环节 | 不可替代 | 供给刚性 | 寡头垄断 | 机构低配 | 反证条件 |", report)
            self.assertIn("等待买入触发", report)
            self.assertIn("![产业链图谱](assets/theme-chain-map.png)", report)
            self.assertIn("![卡口优先级](assets/theme-bottleneck-priority.png)", report)
            self.assertIn("本轮没有通过交易决策与风险收益比门槛", report)
            self.assertNotIn("![核心标的K线结构](assets/theme-trade-map.png)", report)
            self.assertNotIn("![现阶段买入候选K线结构](assets/theme-trade-map.png)", report)
            self.assertTrue((out / "assets" / "theme-chain-map.png").exists())
            self.assertTrue(gen.png_has_chart_content(out / "assets" / "theme-chain-map.png"))
            q = gen.quality(report)
            self.assertFalse(q["missing_sections"])
            self.assertGreaterEqual(q["image_count"], 3)
            review = review_report_text(
                root=root,
                text=report,
                report_path=out / "report.md",
                theme_key="ai-compute-infra",
                policy={},
            )
            titles = {finding["title"] for finding in review["findings"]}
            self.assertNotIn("缺少A股九列公司映射表", titles)
            self.assertNotIn("缺少核心环节价值分布表", titles)
            self.assertNotIn("瓶颈判断缺少四标准校验", titles)

    def test_generic_theme_company_mapping_prefers_theme_candidates(self) -> None:
        payload = self._payload()
        payload["a_share_quotes"] = [
            {"symbol": "600519", "name": "贵州茅台", "price": 1000, "change_pct": 1.0},
        ]
        payload["research_pipeline"]["stock_analyzer"] = [
            {
                "symbol": "600519",
                "name": "贵州茅台",
                "business_model": "非本主题样本",
                "valuation": {"pe": 20, "pb": 8},
            }
        ]
        payload["research_pipeline"]["selected_industry_chain"] = {
            "selected_theme": "datacenter-power",
            "score": 17,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "reports" / "themes" / "datacenter-power"
            with mock.patch("scripts.generate_theme_deep_report.ROOT", root):
                report = gen.build_report(payload, "datacenter-power", out)

        mapping_section = report.split("### A股公司映射与核心地位判断", 1)[1].split("### 竞争格局与反证条件", 1)[0]
        self.assertIn("英维克", mapping_section)
        self.assertIn("申菱环境", mapping_section)
        self.assertNotIn("贵州茅台", mapping_section)

    def test_trade_kline_png_has_candle_content(self) -> None:
        history = []
        for idx in range(90):
            close = 30 + idx * 0.1
            history.append(
                {
                    "date": f"2026-04-{(idx % 28) + 1:02d}",
                    "open": close - 0.08,
                    "close": close,
                    "high": close + 0.35,
                    "low": close - 0.32,
                }
            )
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "trade-map.png"
            gen.write_trade_kline_png(
                png,
                "AI算力基础设施",
                [
                    {
                        "name": name,
                        "symbol": symbol,
                        "supplement": {"price_history": {"rows": history}},
                        "technical": {"support": 31.2, "pressure": 39.8},
                    }
                    for name, symbol in [
                        ("中际旭创", "300308"),
                        ("新易盛", "300502"),
                        ("天孚通信", "300394"),
                        ("沪电股份", "002463"),
                        ("胜宏科技", "300476"),
                        ("寒武纪", "688256"),
                    ]
                ],
            )

            self.assertTrue(gen.png_has_chart_content(png))

    def test_current_buy_candidate_requires_explicit_buy_action_when_decisions_exist(self) -> None:
        base = {
            "technical": {
                "price": 10.0,
                "support": 9.0,
                "pressure": 13.0,
                "risk_reward": 3.0,
                "history_points": 80,
                "trend": "多头趋势",
            },
            "decision_scope_present": True,
        }

        watch = {**base, "decision": {"action": "watch", "min_risk_reward": 2.0}, "has_trade_decision": True}
        candidate = {**base, "decision": {"action": "candidate", "min_risk_reward": 2.0}, "has_trade_decision": True}
        paper = {**base, "decision": {"action": "paper_candidate", "min_risk_reward": 2.0}, "has_trade_decision": True}
        missing = {**base, "decision": {}, "has_trade_decision": False}

        self.assertFalse(gen.current_buy_candidate(watch))
        self.assertFalse(gen.current_buy_candidate(candidate))
        self.assertTrue(gen.current_buy_candidate(paper))
        self.assertFalse(gen.current_buy_candidate(missing))

    def test_write_outputs_never_overwrites_existing_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / "reports" / "themes" / "ai-compute-infra" / "report.md"
            canonical.parent.mkdir(parents=True)
            canonical.write_text("# GOOD\n\n人工正文。\n", encoding="utf-8")
            payload_file = root / "runs" / "2026-07-09" / "full-loop-1" / "cycle-001" / "result.json"
            payload_file.parent.mkdir(parents=True)

            with mock.patch("scripts.generate_theme_deep_report.ROOT", root):
                written, draft, seeded = gen.write_theme_outputs("# NEW\n\n新正文。\n", payload_file, "ai-compute-infra")

            self.assertFalse(seeded)
            self.assertEqual(written.read_text(encoding="utf-8"), "# GOOD\n\n人工正文。\n")
            self.assertIn("新正文", draft.read_text(encoding="utf-8"))

    def test_write_outputs_does_not_create_missing_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload_file = root / "runs" / "2026-07-09" / "full-loop-1" / "cycle-001" / "result.json"
            payload_file.parent.mkdir(parents=True)

            with mock.patch("scripts.generate_theme_deep_report.ROOT", root):
                written, draft, seeded = gen.write_theme_outputs("# NEW\n\n新正文。\n", payload_file, "ai-compute-infra")

            self.assertFalse(seeded)
            self.assertFalse(written.exists())
            self.assertIn("新正文", draft.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
