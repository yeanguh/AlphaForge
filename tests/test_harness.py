import tempfile
import unittest
from pathlib import Path
from unittest import mock

from loop_os.harness.checks import (
    check_industry_analysis_report,
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

    def test_industry_check_is_legacy_optional(self) -> None:
        # F2: reports/industry 缺失时只 warn(skip), 不再 error 阻塞 loop。
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch("loop_os.harness.checks.ROOT", root):
                checks = check_industry_analysis_report()
            statuses = {c["status"] for c in checks}
            self.assertNotIn("error", statuses)
            self.assertIn("warn", statuses)
