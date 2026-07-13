import unittest
from unittest import mock

from providers.open_source import tushare_provider


class FakeFrame:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def __len__(self) -> int:
        return len(self._rows)

    def to_dict(self, orient: str) -> list[dict]:
        if orient != "records":
            raise ValueError(orient)
        return list(self._rows)


class TushareProviderTest(unittest.TestCase):
    def test_normalize_ts_code(self) -> None:
        self.assertEqual(tushare_provider.normalize_ts_code("002837"), "002837.SZ")
        self.assertEqual(tushare_provider.normalize_ts_code("600519"), "600519.SH")
        self.assertEqual(tushare_provider.normalize_ts_code("688017"), "688017.SH")
        self.assertEqual(tushare_provider.normalize_ts_code("430047"), "430047.BJ")
        self.assertEqual(tushare_provider.normalize_ts_code("000300.SH"), "000300.SH")

    def test_query_success_returns_portable_payload(self) -> None:
        rows = [{"ts_code": "002837.SZ", "trade_date": "20260710", "close": 10.5}]
        with mock.patch.object(tushare_provider, "_call", return_value=FakeFrame(rows)):
            result = tushare_provider.query("daily", {"ts_code": "002837.SZ"}, limit=1)

        self.assertEqual(result["provider"], "tushare")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["rows"], rows)
        self.assertIn("close", result["fields"])

    def test_query_classifies_permission_denied(self) -> None:
        with mock.patch.object(tushare_provider, "_call", side_effect=RuntimeError("没有接口访问权限")):
            result = tushare_provider.query("income_vip", {"ts_code": "002837.SZ"})

        self.assertEqual(result["status"], "permission_denied")
        self.assertEqual(result["rows"], [])

    def test_query_classifies_ip_limited(self) -> None:
        with mock.patch.object(tushare_provider, "_call", side_effect=RuntimeError("40204 IP数量超限")):
            result = tushare_provider.query("income", {"ts_code": "002837.SZ"})

        self.assertEqual(result["status"], "ip_limited")

    def test_financial_bundle_contains_report_sections(self) -> None:
        def fake_query(api_name: str, params: dict | None = None, fields: str | None = None, **kwargs) -> dict:
            return {"provider": "tushare", "api": api_name, "status": "ok_empty", "row_count": 0, "rows": []}

        with mock.patch.object(tushare_provider, "query", side_effect=fake_query):
            result = tushare_provider.fetch_financial_bundle("002837", period="20260331")

        self.assertEqual(result["status"], "ok")
        self.assertIn("income", result["results"])
        self.assertIn("balancesheet", result["results"])
        self.assertIn("cashflow", result["results"])
        self.assertIn("fina_indicator", result["results"])

    def test_capabilities_do_not_require_token(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            result = tushare_provider.capabilities()

        self.assertFalse(result["configured"])
        self.assertIn("financial", result["api_catalog"])
        self.assertIn("income", result["api_catalog"]["financial"])

    def test_smoke_warns_without_token(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            result = tushare_provider.smoke(live=False)

        self.assertEqual(result.status, "warn")
        self.assertIn("TUSHARE_TOKEN", result.summary)


if __name__ == "__main__":
    unittest.main()
