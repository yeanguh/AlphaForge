import unittest

from loop_os.domain.agent_review import _extract_json, _normalize_review, build_deterministic_review


class AgentReviewTest(unittest.TestCase):
    def test_extract_json_from_wrapped_output(self) -> None:
        payload = _extract_json('result:\n{"decision":"needs_more_evidence","roles":{}}\n')
        self.assertEqual(payload["decision"], "needs_more_evidence")

    def test_normalize_review_fills_required_roles(self) -> None:
        review = _normalize_review({"roles": {"bull": "ok"}, "decision": "bad"}, "codex")
        self.assertEqual(review["agent_provider"], "codex")
        self.assertEqual(review["decision"], "needs_more_evidence")
        self.assertEqual(review["roles"]["bull"], ["ok"])
        self.assertIn("risk", review["roles"])

    def test_deterministic_review_declares_provider(self) -> None:
        review = build_deterministic_review({"a_share_quotes": [], "global_charts": [], "industry_analysis": {}, "news": {}})
        self.assertEqual(review["agent_provider"], "deterministic")


if __name__ == "__main__":
    unittest.main()
