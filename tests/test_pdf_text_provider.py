import tempfile
import unittest
from pathlib import Path
from unittest import mock

from providers.open_source import pdf_text


class PdfTextProviderTest(unittest.TestCase):
    def test_extract_hard_fact_snippets_prefers_numbered_facts(self) -> None:
        text = """
        公司产品已进入客户认证阶段。
        800G 光模块订单同比增长 120%，高端产品出货占比提升至 65%。
        产能爬坡仍受良率影响。
        """

        snippets = pdf_text.extract_hard_fact_snippets(text, limit=2)

        self.assertTrue(snippets)
        self.assertIn("120%", snippets[0])
        self.assertIn("订单", snippets[0])

    def test_cached_text_is_used_without_live_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            url = "https://pdf.dfcfw.com/pdf/H3_TEST_1.pdf"
            text_path = cache_dir / f"{pdf_text._cache_key(url)}.txt"  # noqa: SLF001 - cache contract regression
            text_path.write_text("AI服务器订单同比增长 80%，产能利用率提升。", encoding="utf-8")

            with mock.patch("providers.open_source.pdf_text.CACHE_DIR", cache_dir):
                text, status = pdf_text.cached_or_extract_text(url, live=False)

        self.assertEqual(status, "cached")
        self.assertIn("产能利用率", text)

    def test_enrich_pdf_facts_filters_titles_by_terms(self) -> None:
        rows = [
            {"title": "证券行业周报", "pdf_url": "https://pdf.dfcfw.com/pdf/H3_A_1.pdf", "org": "A"},
            {"title": "AI服务器PCB深度", "pdf_url": "https://pdf.dfcfw.com/pdf/H3_B_1.pdf", "org": "B"},
        ]

        with mock.patch(
            "providers.open_source.pdf_text.cached_or_extract_text",
            return_value=("AI服务器PCB订单同比增长 90%，产能爬坡顺利。", "cached"),
        ):
            facts = pdf_text.enrich_pdf_facts(rows, include_terms=("AI服务器",), live=False)

        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["source"], "B")
        self.assertIn("90%", facts[0]["snippet"])


if __name__ == "__main__":
    unittest.main()
