"""方案 A 核心不变量回归测试:physical-ai 生成器绝不整篇覆盖 canonical report.md。

覆盖 scripts.generate_physical_ai_chain_report 里两个已抽成纯函数的写入策略:
- draft_slug_from_payload: 同一天多轮 loop 的草稿文件名互不覆盖;
- write_report_outputs: 已存在的 canonical report.md 原样保留(只 seed 首轮)。
"""

import tempfile
import unittest
from pathlib import Path

from scripts import generate_physical_ai_chain_report as gen


class DraftSlugTest(unittest.TestCase):
    def test_slug_from_full_loop_layout_is_run_plus_cycle(self) -> None:
        payload = Path("runs/2026-07-09/full-loop-181606/cycle-001/result.json")
        self.assertEqual(
            gen.draft_slug_from_payload(payload),
            "full-loop-181606-cycle-001",
        )

    def test_two_cycles_same_day_get_distinct_slugs(self) -> None:
        p1 = Path("runs/2026-07-09/full-loop-090000/cycle-001/result.json")
        p2 = Path("runs/2026-07-09/full-loop-153000/cycle-002/result.json")
        self.assertNotEqual(
            gen.draft_slug_from_payload(p1),
            gen.draft_slug_from_payload(p2),
        )

    def test_non_standard_path_falls_back_to_unique_manual_slug(self) -> None:
        slug = gen.draft_slug_from_payload(Path("data/raw/latest-full-loop.json"))
        self.assertTrue(slug.startswith("manual-"))


class WriteReportOutputsTest(unittest.TestCase):
    def _dirs(self, root: Path) -> tuple[Path, Path]:
        out_dir = root / "reports" / "themes" / "physical-ai"
        drafts_dir = out_dir / "drafts"
        return out_dir, drafts_dir

    def test_seeds_canonical_only_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir, drafts_dir = self._dirs(root)
            payload = root / "runs" / "d" / "full-loop-1" / "cycle-001" / "result.json"

            canonical, draft, seeded = gen.write_report_outputs(
                "# seed body\n\n首轮正文。",
                payload,
                out_dir=out_dir,
                drafts_dir=drafts_dir,
            )
            self.assertTrue(seeded)
            self.assertTrue(canonical.exists())
            self.assertIn("首轮正文", canonical.read_text(encoding="utf-8"))
            self.assertTrue(draft.exists())
            self.assertTrue((drafts_dir / "full-loop-1-cycle-001.md").exists())

    def test_existing_canonical_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir, drafts_dir = self._dirs(root)
            out_dir.mkdir(parents=True)
            canonical_path = out_dir / "report.md"
            good = "# GOOD canonical\n\n人工累积的高质量正文,不应被任何一轮覆盖。\n"
            canonical_path.write_text(good, encoding="utf-8")

            payload = root / "runs" / "d" / "full-loop-2" / "cycle-005" / "result.json"
            canonical, draft, seeded = gen.write_report_outputs(
                "# BAD cycle body\n\n本轮取数质量差的正文。",
                payload,
                out_dir=out_dir,
                drafts_dir=drafts_dir,
            )
            # 核心不变量:canonical 内容一字未改,且没有被标记为 seed。
            self.assertFalse(seeded)
            self.assertEqual(canonical.read_text(encoding="utf-8"), good)
            # 本轮正文只落在 draft / drafts 归档里,不进 canonical。
            self.assertIn("BAD cycle body", draft.read_text(encoding="utf-8"))
            self.assertNotIn("BAD cycle body", canonical.read_text(encoding="utf-8"))

    def test_second_run_same_day_does_not_clobber_first_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir, drafts_dir = self._dirs(root)

            p1 = root / "runs" / "d" / "full-loop-0900" / "cycle-001" / "result.json"
            p2 = root / "runs" / "d" / "full-loop-1500" / "cycle-001" / "result.json"
            _, draft1, _ = gen.write_report_outputs(
                "# body A\n\nA 正文。", p1, out_dir=out_dir, drafts_dir=drafts_dir
            )
            _, draft2, _ = gen.write_report_outputs(
                "# body B\n\nB 正文。", p2, out_dir=out_dir, drafts_dir=drafts_dir
            )
            self.assertNotEqual(draft1, draft2)
            self.assertTrue(draft1.exists())
            self.assertTrue(draft2.exists())
            self.assertIn("A 正文", draft1.read_text(encoding="utf-8"))
            self.assertIn("B 正文", draft2.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
