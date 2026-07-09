import json
from io import BytesIO
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from loop_os.domain.agent_review import _extract_json, _normalize_review, _run_openai_compatible, build_deterministic_review


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

    def test_openai_compatible_review_uses_env_config(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return (
                    b'{"choices":[{"message":{"content":"{\\"roles\\":{\\"bull\\":[\\"ok\\"]},'
                    b'\\"decision\\":\\"needs_more_evidence\\",\\"reason\\":\\"checked\\",\\"next_actions\\":[\\"verify\\"]}"}}]}'
                )

        with TemporaryDirectory() as tmp, mock.patch.dict(
            "os.environ",
            {"BASE_URL": "https://example.test/v1", "API_KEY": "test-key", "MODEL_NAME": "test-model"},
            clear=True,
        ), mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            review = _run_openai_compatible("prompt", Path(tmp), Path(tmp), 5)

        request = urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://example.test/v1/chat/completions")
        self.assertEqual(body["max_tokens"], 4096)
        self.assertEqual(review["agent_provider"], "openai_compatible")
        self.assertEqual(review["roles"]["bull"], ["ok"])

    def test_openai_compatible_review_accepts_openai_env_names(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return b'{"choices":[{"message":{"content":"{\\"roles\\":{},\\"decision\\":\\"needs_more_evidence\\"}"}}]}'

        with TemporaryDirectory() as tmp, mock.patch.dict(
            "os.environ",
            {
                "OPENAI_BASE_URL": "https://example.test/v1",
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "test-model",
                "OPENAI_MAX_TOKENS": "512",
            },
            clear=True,
        ), mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            review = _run_openai_compatible("prompt", Path(tmp), Path(tmp), 5)

        request = urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["max_tokens"], 512)
        self.assertEqual(review["agent_provider"], "openai_compatible")

    def test_openai_compatible_retries_transient_http_errors(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return b'{"choices":[{"message":{"content":"{\\"roles\\":{},\\"decision\\":\\"needs_more_evidence\\"}"}}]}'

        transient = urllib.error.HTTPError(
            "https://example.test/v1/chat/completions",
            502,
            "Bad Gateway",
            {},
            BytesIO(b"temporary gateway error"),
        )
        with TemporaryDirectory() as tmp, mock.patch.dict(
            "os.environ",
            {"BASE_URL": "https://example.test/v1", "API_KEY": "test-key", "MODEL_NAME": "test-model"},
            clear=True,
        ), mock.patch("urllib.request.urlopen", side_effect=[transient, FakeResponse()]) as urlopen, mock.patch("time.sleep"):
            review = _run_openai_compatible("prompt", Path(tmp), Path(tmp), 5)

        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(review["agent_provider"], "openai_compatible")


if __name__ == "__main__":
    unittest.main()
