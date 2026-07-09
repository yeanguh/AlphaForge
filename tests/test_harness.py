import unittest

from loop_os.harness.checks import (
    check_no_core_external_imports,
    check_loop_state_invariants,
    check_provider_skill_files,
    check_retained_skill_files,
    check_retained_skills,
    check_state_files,
    check_submodules,
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
