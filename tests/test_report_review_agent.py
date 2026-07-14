import tempfile
import unittest
from pathlib import Path

from loop_os.domain.report_review_agent import build_report_review, review_report_text


class ReportReviewAgentTest(unittest.TestCase):
    def test_architecture_review_flags_final_report_quality_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "report_policy.json").write_text(
                """{
                  "theme_report": {
                    "quality": {
                      "min_chars": 100,
                      "min_images": 1,
                      "max_todo_count": 0,
                      "required_sections": ["## 研究课题"],
                      "required_terms": ["买入条件"]
                    }
                  }
                }""",
                encoding="utf-8",
            )
            report = root / "reports" / "themes" / "demo" / "report.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Demo\n\n"
                "## 研究课题\n\n"
                "![坏图](assets/missing.png)\n\n"
                "![核心标的K线结构](assets/trade.png)\n\n"
                "## 附录 · Loop 证据增量日志\n\n过程日志。\n",
                encoding="utf-8",
            )

            review = build_report_review(
                root=root,
                payload={"run_id": "run-A", "cycle": 1},
                theme_key="demo",
                report_path=report,
                draft_path=None,
                artifacts_dir=root / "runs" / "run-A" / "cycle-001" / "report-review",
            )

            titles = {finding["title"] for finding in review["findings"]}
            self.assertEqual(review["status"], "needs_improvement")
            self.assertIn("报告存在坏图链", titles)
            self.assertIn("最终报告混入 Loop 证据日志", titles)
            self.assertIn("K线分析仍按核心/龙头口径呈现", titles)
            self.assertTrue((root / "runs" / "run-A" / "cycle-001" / "report-review" / "report-review.json").exists())

    def test_architecture_review_flags_missing_industry_chain_quality_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "report_policy.json").write_text(
                """{
                  "theme_report": {
                    "quality": {
                      "min_chars": 10,
                      "min_images": 0,
                      "max_todo_count": 99,
                      "required_sections": [],
                      "required_terms": []
                    }
                  }
                }""",
                encoding="utf-8",
            )
            report = root / "reports" / "themes" / "demo" / "report.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Demo\n\n"
                "## 产业链核心环节价值分布\n\n"
                "这里讨论瓶颈、卡口、卡脖子和投资机会，但没有结构化价值分布表。\n\n"
                "## A股公司映射与核心地位判断\n\n"
                "这里讨论A股可交易标的，但没有九列表。\n\n"
                "## 数据来源与证据强度\n\n"
                "来源比较强。\n\n"
                "公共数据适配器留痕: endpoint failure row count。\n",
                encoding="utf-8",
            )

            review = build_report_review(
                root=root,
                payload={"run_id": "run-B", "cycle": 2},
                theme_key="demo",
                report_path=report,
                draft_path=None,
                artifacts_dir=root / "runs" / "run-B" / "cycle-002" / "report-review",
            )

            titles = {finding["title"] for finding in review["findings"]}
            self.assertEqual(review["status"], "needs_improvement")
            self.assertIn("缺少A股九列公司映射表", titles)
            self.assertIn("缺少核心环节价值分布表", titles)
            self.assertIn("瓶颈判断缺少四标准校验", titles)
            self.assertIn("缺少反证退出条件", titles)
            self.assertIn("证据强度缺少 claim-level 来源表", titles)
            self.assertIn("读者报告混入数据适配器日志", titles)

    def test_architecture_review_accepts_required_industry_chain_quality_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "report_policy.json").write_text(
                """{
                  "theme_report": {
                    "quality": {
                      "min_chars": 10,
                      "min_images": 0,
                      "max_todo_count": 99,
                      "required_sections": [],
                      "required_terms": []
                    }
                  }
                }""",
                encoding="utf-8",
            )
            report = root / "reports" / "themes" / "demo" / "report.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Demo\n\n"
                "## 产业链核心环节价值分布\n\n"
                "| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| 上游 | 关键材料 | 高 | 不可替代、供给刚性、寡头垄断、机构低配 | 高 | 示例公司 | 核心环节龙头 | 年报 |\n\n"
                "## A股公司映射与核心地位判断\n\n"
                "| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| 示例公司 | 000001 | 上游 | 材料 | 未披露 | 材料 | High | 核心环节龙头 | 年报 |\n\n"
                "## 投资机会挖掘\n\n"
                "反证条件: 替代技术成熟、客户切换或毛利率压缩。\n\n"
                "## 数据来源与证据强度\n\n"
                "| 结论/数据 | 来源 | 日期 | 置信度 |\n"
                "| --- | --- | --- | --- |\n"
                "| 示例结论 | 年报 | 2026 | High |\n",
                encoding="utf-8",
            )

            review = build_report_review(
                root=root,
                payload={"run_id": "run-C", "cycle": 3},
                theme_key="demo",
                report_path=report,
                draft_path=None,
                artifacts_dir=root / "runs" / "run-C" / "cycle-003" / "report-review",
            )

            titles = {finding["title"] for finding in review["findings"]}
            self.assertNotIn("缺少A股九列公司映射表", titles)
            self.assertNotIn("缺少核心环节价值分布表", titles)
            self.assertNotIn("瓶颈判断缺少四标准校验", titles)
            self.assertNotIn("缺少反证退出条件", titles)
            self.assertNotIn("证据强度缺少 claim-level 来源表", titles)

    def test_review_flags_repeated_candidate_company_pool(self) -> None:
        text = (
            "# Demo\n\n"
            "### 核心节点三公司校验\n\n"
            "| 产业链节点 | 核心公司1 | 核心公司2 | 核心公司3 | 升级催化 | 失效条件 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| AI制药 | 药明康德 | 迈瑞医疗 | 联影医疗 | 订单 | 反证 |\n"
            "| 医疗影像 | 药明康德 | 迈瑞医疗 | 联影医疗 | 订单 | 反证 |\n"
        )

        review = review_report_text(root=Path("/tmp"), text=text, report_path=None, theme_key="demo", policy={})

        titles = {finding["title"] for finding in review["findings"]}
        self.assertIn("多个产业链节点重复使用同一候选公司池", titles)

    def test_review_flags_non_theme_counterexample_in_mapping(self) -> None:
        text = (
            "# Demo\n\n"
            "## 产业链 / 竞争格局\n\n"
            "### A股公司映射与核心地位判断\n\n"
            "| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 贵州茅台 | 600519 | 非主线 | 消费品 | 未披露 | 白酒 | None | 反例/非产业链样本 | 不应进入正文 |\n"
        )

        review = review_report_text(root=Path("/tmp"), text=text, report_path=None, theme_key="demo", policy={})

        titles = {finding["title"] for finding in review["findings"]}
        self.assertIn("A股映射表混入非主线反例样本", titles)


if __name__ == "__main__":
    unittest.main()
