import tempfile
import unittest
from pathlib import Path
from unittest import mock

from loop_os.harness.checks import (
    check_final_reports_no_operational_logs,
    check_industry_analysis_report,
    check_latest_loop_artifact,
    check_no_core_external_imports,
    check_loop_state_invariants,
    check_no_secret_leaks,
    check_provider_skill_files,
    check_retained_skill_files,
    check_retained_skills,
    check_state_files,
    check_submodules,
    check_theme_reports,
)


class HarnessTest(unittest.TestCase):
    def test_state_harness_passes(self) -> None:
        self.assertTrue(all(item["status"] == "ok" for item in check_state_files()))

    def test_submodule_harness_passes(self) -> None:
        self.assertTrue(all(item["status"] == "ok" for item in check_submodules()))

    def test_retained_skills_exist(self) -> None:
        self.assertTrue(all(item["status"] == "ok" for item in check_retained_skill_files()))

    def test_legacy_retained_skill_check_only_checks_retained_methodology(self) -> None:
        checks = check_retained_skills()
        self.assertEqual([item["check"] for item in checks], ["retained_skill_file:skills/industry-chain-analysis/SKILL.md"])

    def test_provider_skills_exist(self) -> None:
        self.assertNotIn("error", {item["status"] for item in check_provider_skill_files()})

    def test_loop_state_invariants_do_not_error(self) -> None:
        self.assertNotIn("error", {item["status"] for item in check_loop_state_invariants()})

    def test_openai_compatible_agent_review_is_harness_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "raw").mkdir(parents=True)
            (root / "reports" / "daily").mkdir(parents=True)
            (root / "reports" / "daily" / "latest-full-loop.md").write_text("clean report", encoding="utf-8")
            (root / "data" / "raw" / "latest-full-loop.json").write_text(
                """{
                  "agent_review": {"agent_provider": "openai_compatible", "roles": {"bull": ["ok"]}},
                  "research_pipeline": {},
                  "stock_supplements": {},
                  "evidence_ids": ["ev-1"],
                  "state_transition": {"validated": true}
                }""",
                encoding="utf-8",
            )
            with mock.patch("loop_os.harness.checks.ROOT", root):
                checks = check_latest_loop_artifact()
            llm = next(c for c in checks if c["check"] == "latest_loop:llm_agent_review")
            self.assertEqual(llm["status"], "ok")

    def test_core_does_not_import_external(self) -> None:
        self.assertEqual(check_no_core_external_imports()[0]["status"], "ok")

    def test_secret_scan_passes_current_outputs(self) -> None:
        self.assertEqual(check_no_secret_leaks()[0]["status"], "ok")

    def test_secret_scan_detects_token_like_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("reports").mkdir()
            root.joinpath("reports", "leak.md").write_text(
                "IWENCAI_API_KEY=sk-proj-testsecretvalue1234567890",
                encoding="utf-8",
            )

            with mock.patch("loop_os.harness.checks.ROOT", root), mock.patch(
                "loop_os.harness.checks.SECRET_SCAN_PATHS", ["reports"]
            ):
                result = check_no_secret_leaks()[0]

            self.assertEqual(result["status"], "error")
            self.assertEqual(result["offenders"][0]["path"], "reports/leak.md")

    def test_theme_reports_passes_current_outputs(self) -> None:
        # 真实仓库: canonical physical-ai 报告存在且图片不断链。
        statuses = {item["status"] for item in check_theme_reports()}
        self.assertNotIn("error", statuses)

    def test_theme_canonical_gate_errors_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports" / "themes").mkdir(parents=True)
            with mock.patch("loop_os.harness.checks.ROOT", root), mock.patch(
                "loop_os.harness.checks.get_theme_canonical_required", return_value=["physical-ai"]
            ):
                checks = check_theme_reports()
            gate = next(c for c in checks if c["check"] == "theme_report:canonical:physical-ai")
            self.assertEqual(gate["status"], "error")

    def test_theme_broken_image_link_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdir = root / "reports" / "themes" / "physical-ai"
            tdir.mkdir(parents=True)
            (tdir / "report.md").write_text(
                "# t\n\n![map](assets/missing.png)\n", encoding="utf-8"
            )
            with mock.patch("loop_os.harness.checks.ROOT", root), mock.patch(
                "loop_os.harness.checks.get_theme_canonical_required", return_value=["physical-ai"]
            ):
                checks = check_theme_reports()
            links = next(c for c in checks if c["check"] == "theme_report:image_links")
            self.assertEqual(links["status"], "error")
            self.assertTrue(any("missing.png" in b for b in links["broken"]))

    def test_theme_quality_uses_clean_report_when_loop_log_is_separate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdir = root / "reports" / "themes" / "ai-compute-infra"
            (tdir / "assets").mkdir(parents=True)
            for name in ("a.svg", "b.svg", "c.svg"):
                (tdir / "assets" / name).write_text("<svg></svg>", encoding="utf-8")
            body = "\n\n".join(
                [
                    "# AI 算力基础设施主题最终报告",
                    "![a](assets/a.svg)\n![b](assets/b.svg)\n![c](assets/c.svg)",
                    "## 研究课题\n" + "正文 " * 700,
                    "## 一句话结论\n强命题 置信度 瓶颈战斗地图 龙头分层 硬事实台账 证据密度 PDF正文级 订单 产能 客户认证 瓶颈 卡口 估值 营收同比 归母净利同比 毛利率 预测PE 失效条件 反证 证据id",
                    "## 市场盘点\n正文",
                    "## 核心逻辑\n正文",
                    "## 关键数据\n正文",
                    "## 产业链跟踪\n正文",
                    "## 投资机会挖掘\n正文",
                    "## A股可交易标的估值对比\n正文",
                    "## 产业链 / 竞争格局\n正文",
                    "## 标的分层与入场条件\n正文",
                    "## 风险、反证与退出条件\n正文",
                    "## 数据来源与证据强度\n正文",
                ]
            )
            (tdir / "report.md").write_text(body, encoding="utf-8")
            (tdir / "report_change_log.md").write_text(
                "## 附录 · Loop 证据增量日志\n- 待补验证\n- 待补验证\n- 待补验证",
                encoding="utf-8",
            )
            with mock.patch("loop_os.harness.checks.ROOT", root), mock.patch(
                "loop_os.harness.checks.get_theme_canonical_required", return_value=["ai-compute-infra"]
            ):
                checks = check_theme_reports()
            quality = next(c for c in checks if c["check"] == "theme_report:quality:ai-compute-infra")
            self.assertEqual(quality["status"], "ok")
            self.assertEqual(quality["todo_count"], 0)

    def test_final_report_operational_log_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdir = root / "reports" / "themes" / "physical-ai"
            tdir.mkdir(parents=True)
            (tdir / "report.md").write_text(
                "# t\n\n## 附录 · Loop 证据增量日志\n<!-- research-os-curation:x -->\n",
                encoding="utf-8",
            )
            with mock.patch("loop_os.harness.checks.ROOT", root):
                result = check_final_reports_no_operational_logs()[0]

            self.assertEqual(result["status"], "error")
            self.assertEqual(result["offenders"], ["reports/themes/physical-ai/report.md"])

    def test_theme_quality_allows_physical_ai_deep_legacy_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdir = root / "reports" / "themes" / "physical-ai"
            (tdir / "assets").mkdir(parents=True)
            for name in ("a.svg", "b.svg", "c.svg", "d.svg"):
                (tdir / "assets" / name).write_text("<svg></svg>", encoding="utf-8")
            body = "\n\n".join(
                [
                    "# 物理AI报告",
                    "![a](assets/a.svg)\n![b](assets/b.svg)\n![c](assets/c.svg)\n![d](assets/d.svg)",
                    "## 0. 核心结论\n" + "强命题 置信度 瓶颈战斗地图 龙头分层 硬事实台账 证据密度 PDF正文级 瓶颈 卡口 估值 营收同比 归母净利同比 毛利率 目标价 风险 数据来源 " * 180,
                    "## 1. 研究对象、边界与口径\n正文",
                    "## 3. 产业链全景图谱\n正文",
                    "## 5. 产业链核心环节价值分布\n正文",
                    "## 7. A股公司映射与核心地位判断\n正文",
                    "## 8. 投资线索、交易跟踪与目标价情景\n正文",
                    "## 10. 风险提示\n正文",
                    "## 11. 数据来源、证据强度与待核验事项\n正文",
                ]
            )
            (tdir / "report.md").write_text(body, encoding="utf-8")
            with mock.patch("loop_os.harness.checks.ROOT", root), mock.patch(
                "loop_os.harness.checks.get_theme_canonical_required", return_value=["physical-ai"]
            ):
                checks = check_theme_reports()
            quality = next(c for c in checks if c["check"] == "theme_report:quality:physical-ai")
            self.assertEqual(quality["status"], "ok")

    def test_theme_structure_review_warns_on_missing_skill_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdir = root / "reports" / "themes" / "physical-ai"
            (tdir / "assets").mkdir(parents=True)
            for name in ("a.svg", "b.svg", "c.svg", "d.svg"):
                (tdir / "assets" / name).write_text("<svg></svg>", encoding="utf-8")
            body = "\n\n".join(
                [
                    "# 物理AI报告",
                    "![a](assets/a.svg)\n![b](assets/b.svg)\n![c](assets/c.svg)\n![d](assets/d.svg)",
                    "## 0. 核心结论\n" + "强命题 置信度 瓶颈战斗地图 龙头分层 硬事实台账 证据密度 PDF正文级 瓶颈 卡口 估值 营收同比 归母净利同比 毛利率 目标价 风险 数据来源 " * 180,
                    "## 1. 研究对象、边界与口径\n正文",
                    "## 3. 产业链全景图谱\n正文",
                    "## 5. 产业链核心环节价值分布\n正文",
                    "## 7. A股公司映射与核心地位判断\n正文",
                    "## 8. 投资线索、交易跟踪与目标价情景\n正文",
                    "## 10. 风险提示\n正文",
                    "## 11. 数据来源、证据强度与待核验事项\n正文",
                ]
            )
            (tdir / "report.md").write_text(body, encoding="utf-8")
            with mock.patch("loop_os.harness.checks.ROOT", root), mock.patch(
                "loop_os.harness.checks.get_theme_canonical_required", return_value=["physical-ai"]
            ):
                checks = check_theme_reports()
            structure = next(c for c in checks if c["check"] == "theme_report:structure:physical-ai")
            self.assertEqual(structure["status"], "warn")
            self.assertIn("缺少A股九列公司映射表", structure["findings"])

    def test_theme_structure_review_ok_when_skill_tables_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdir = root / "reports" / "themes" / "physical-ai"
            (tdir / "assets").mkdir(parents=True)
            for name in ("a.svg", "b.svg", "c.svg", "d.svg"):
                (tdir / "assets" / name).write_text("<svg></svg>", encoding="utf-8")
            body = "\n\n".join(
                [
                    "# 物理AI报告",
                    "![a](assets/a.svg)\n![b](assets/b.svg)\n![c](assets/c.svg)\n![d](assets/d.svg)",
                    "## 0. 核心结论\n" + "强命题 置信度 瓶颈战斗地图 龙头分层 硬事实台账 证据密度 PDF正文级 瓶颈 卡口 不可替代 供给刚性 寡头垄断 机构低配 估值 营收同比 归母净利同比 毛利率 目标价 风险 数据来源 " * 180,
                    "## 1. 研究对象、边界与口径\n正文",
                    "## 3. 产业链全景图谱\n正文",
                    "## 5. 产业链核心环节价值分布\n\n"
                    "| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                    "| 上游 | 关键材料 | 高 | 工艺 | 高 | 示例公司 | 龙头 | 年报 |",
                    "## 7. A股公司映射与核心地位判断\n\n"
                    "| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                    "| 示例公司 | 000001 | 上游 | 材料 | 未披露 | 材料 | High | 龙头 | 年报 |",
                    "## 8. 投资线索、交易跟踪与目标价情景\n反证条件: 替代技术成熟。",
                    "## 10. 风险提示\n正文",
                    "## 11. 数据来源、证据强度与待核验事项\n\n"
                    "| 结论/数据 | 来源 | 日期 | 置信度 |\n"
                    "| --- | --- | --- | --- |\n"
                    "| 示例 | 年报 | 2026 | High |",
                ]
            )
            (tdir / "report.md").write_text(body, encoding="utf-8")
            with mock.patch("loop_os.harness.checks.ROOT", root), mock.patch(
                "loop_os.harness.checks.get_theme_canonical_required", return_value=["physical-ai"]
            ):
                checks = check_theme_reports()
            structure = next(c for c in checks if c["check"] == "theme_report:structure:physical-ai")
            self.assertEqual(structure["status"], "ok")

    def test_industry_check_is_legacy_optional(self) -> None:
        # F2: reports/industry 缺失时只 warn(skip), 不再 error 阻塞 loop。
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch("loop_os.harness.checks.ROOT", root):
                checks = check_industry_analysis_report()
            statuses = {c["status"] for c in checks}
            self.assertNotIn("error", statuses)
            self.assertIn("warn", statuses)
