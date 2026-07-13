import tempfile
import unittest
from pathlib import Path

from loop_os.domain.report_review_agent import review_report_text
from scripts.backfill_theme_report_quality_structure import backfill_report


class BackfillThemeReportQualityStructureTest(unittest.TestCase):
    def _root(self) -> tempfile.TemporaryDirectory:
        return tempfile.TemporaryDirectory()

    def _write_policy(self, root: Path) -> None:
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

    def test_backfill_inserts_missing_structures_without_rewriting_prose(self) -> None:
        with self._root() as tmp:
            root = Path(tmp)
            self._write_policy(root)
            report = root / "reports" / "themes" / "demo" / "report.md"
            report.parent.mkdir(parents=True)
            original = (
                "# Demo\n\n"
                "## 产业链跟踪\n\n"
                "这段人工正文必须保留。\n\n"
                "| 环节 | 事实映射 | 供需变化方向 | 瓶颈/卡口 | A股映射 |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| 上游 | 关键材料 | 上行 | 认证周期/良率爬坡 | 示例公司 |\n\n"
                "## 投资机会挖掘\n\n"
                "瓶颈和卡口需要反证退出条件。\n\n"
                "### 瓶颈战斗地图\n\n"
                "| 瓶颈节点 | 当前三家核心公司 | 为什么卡 | 升级信号 | 反证信号 | 节点结论 |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| 关键材料 | 示例公司、第二公司、第三公司 | 供给刚性/认证周期/良率爬坡 | 订单增加 | 替代技术成熟 | 绝对核心 |\n\n"
                "## A股可交易标的估值对比\n\n"
                "| 公司 | 代码 | 产业链位置 | 当前估值 | 财务/订单信号 | 催化 | 买点条件 | 失效条件 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| 示例公司 | 000001 | 关键材料 | PE 20 | 财报披露产品收入 | 订单增加 | 等待买入触发 | 替代技术成熟 |\n\n"
                "## 核心个股交易跟踪\n\n"
                "交易正文。\n\n"
                "## 数据来源与证据强度\n\n"
                "| 事实类型 | 硬事实/线索 | 涉及节点 | 涉及公司 | 数值/时间 | 来源 | 证据强度 | 交易含义 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| 订单/客户 | 示例公司产品收入 | 关键材料 | 示例公司 | 2026 | 年报 | High | 验证暴露 |\n"
            )
            report.write_text(original, encoding="utf-8")

            before = review_report_text(root=root, text=original, report_path=report, theme_key="demo", policy={})
            before_titles = {finding["title"] for finding in before["findings"]}
            self.assertIn("缺少A股九列公司映射表", before_titles)
            self.assertIn("缺少核心环节价值分布表", before_titles)
            self.assertIn("瓶颈判断缺少四标准校验", before_titles)

            result = backfill_report(report, root=root)
            updated = report.read_text(encoding="utf-8")

            self.assertTrue(result.changed)
            self.assertIn("这段人工正文必须保留。", updated)
            self.assertIn("| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |", updated)
            self.assertIn("| 候选环节 | 不可替代 | 供给刚性 | 寡头垄断 | 机构低配 | 反证条件 |", updated)
            self.assertIn("| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |", updated)
            self.assertIn("| 结论/数据 | 来源 | 日期 | 置信度 |", updated)

            after = review_report_text(root=root, text=updated, report_path=report, theme_key="demo", policy={})
            after_titles = {finding["title"] for finding in after["findings"]}
            self.assertNotIn("缺少A股九列公司映射表", after_titles)
            self.assertNotIn("缺少核心环节价值分布表", after_titles)
            self.assertNotIn("瓶颈判断缺少四标准校验", after_titles)
            self.assertNotIn("证据强度缺少 claim-level 来源表", after_titles)

    def test_backfill_is_idempotent(self) -> None:
        with self._root() as tmp:
            root = Path(tmp)
            self._write_policy(root)
            report = root / "reports" / "themes" / "demo" / "report.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Demo\n\n"
                "## 产业链跟踪\n\n"
                "| 环节 | 事实映射 | 供需变化方向 | 瓶颈/卡口 | A股映射 |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| 上游 | 关键材料 | 上行 | 供给刚性 | 示例公司 |\n\n"
                "## 投资机会挖掘\n\n"
                "反证条件明确。\n\n"
                "| 瓶颈节点 | 当前三家核心公司 | 为什么卡 | 升级信号 | 反证信号 | 节点结论 |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| 关键材料 | 示例公司 | 供给刚性 | 订单 | 替代路线 | 绝对核心 |\n\n"
                "| 公司 | 代码 | 产业链位置 | 当前估值 | 财务/订单信号 | 催化 | 买点条件 | 失效条件 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| 示例公司 | 000001 | 关键材料 | PE 20 | 财报 | 订单 | 等待买入触发 | 替代路线 |\n",
                encoding="utf-8",
            )

            first = backfill_report(report, root=root)
            first_text = report.read_text(encoding="utf-8")
            second = backfill_report(report, root=root)
            second_text = report.read_text(encoding="utf-8")

            self.assertTrue(first.changed)
            self.assertFalse(second.changed)
            self.assertEqual(first_text, second_text)

    def test_backfill_accepts_battle_map_without_node_conclusion(self) -> None:
        with self._root() as tmp:
            root = Path(tmp)
            self._write_policy(root)
            report = root / "reports" / "themes" / "demo" / "report.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Demo\n\n"
                "## 投资机会挖掘\n\n"
                "瓶颈和卡口需要反证条件。\n\n"
                "| 瓶颈节点 | 当前三家核心公司 | 为什么卡 | 当前主研究位 | 升级信号 | 反证信号 |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| 关键材料 | 示例公司、第二公司、第三公司 | 认证周期/良率爬坡 | 示例公司 | 订单 | 替代路线 |\n",
                encoding="utf-8",
            )

            result = backfill_report(report, root=root)
            updated = report.read_text(encoding="utf-8")

            self.assertTrue(result.changed)
            self.assertIn("bottleneck_standards", result.inserted)
            self.assertIn("| 候选环节 | 不可替代 | 供给刚性 | 寡头垄断 | 机构低配 | 反证条件 |", updated)


if __name__ == "__main__":
    unittest.main()
