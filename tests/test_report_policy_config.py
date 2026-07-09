import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from loop_os.harness import checks


class ReportPolicyConfigTest(unittest.TestCase):
    """Report theme / forbidden terms must be loadable from config/report_policy.json,
    with hardcoded fallbacks when the file is missing or malformed."""

    def test_config_file_present_and_valid(self) -> None:
        path = checks.ROOT / "config" / "report_policy.json"
        self.assertTrue(path.exists(), "config/report_policy.json should exist")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("industry_report", data)
        self.assertIn("latest_report", data)

    def test_getters_read_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "report_policy.json").write_text(
                json.dumps(
                    {
                        "industry_report": {
                            "dir_glob": "custom-theme-*",
                            "required_terms": ["A", "B"],
                        },
                        "latest_report": {"forbidden_terms": ["FOO", "BAR"]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with mock.patch.object(checks, "ROOT", root):
                self.assertEqual(checks.get_industry_dir_glob(), "custom-theme-*")
                self.assertEqual(checks.get_industry_required_terms(), ["A", "B"])
                self.assertEqual(checks.get_forbidden_report_terms(), ["FOO", "BAR"])

    def test_fallback_when_config_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)  # no config/ dir at all
            with mock.patch.object(checks, "ROOT", root):
                self.assertEqual(checks.get_industry_dir_glob(), checks._DEFAULT_INDUSTRY_DIR_GLOB)
                self.assertEqual(
                    checks.get_industry_required_terms(), checks._DEFAULT_INDUSTRY_REQUIRED_TERMS
                )
                self.assertEqual(
                    checks.get_forbidden_report_terms(), checks._DEFAULT_FORBIDDEN_REPORT_TERMS
                )

    def test_fallback_when_config_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "report_policy.json").write_text("{ not json", encoding="utf-8")
            with mock.patch.object(checks, "ROOT", root):
                self.assertEqual(checks.get_industry_dir_glob(), checks._DEFAULT_INDUSTRY_DIR_GLOB)

    def test_empty_lists_fall_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "report_policy.json").write_text(
                json.dumps({"industry_report": {"required_terms": []}}), encoding="utf-8"
            )
            with mock.patch.object(checks, "ROOT", root):
                self.assertEqual(
                    checks.get_industry_required_terms(), checks._DEFAULT_INDUSTRY_REQUIRED_TERMS
                )


if __name__ == "__main__":
    unittest.main()
