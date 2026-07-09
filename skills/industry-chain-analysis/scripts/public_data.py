#!/usr/bin/env python3
"""Low-frequency public-data adapters and source-trail helper for industry-chain analysis.

This module turns the adapter patterns described in `references/data-sourcing.md`
into reusable functions so report generators do not re-implement safe imports,
baostock login/logout, or source-trail bookkeeping per output directory.

Design rules (see references/insight-design-constraints.md):
- Every adapter returns ``(payload, error)`` and never raises for network/runtime
  failures; the caller decides whether to fall back.
- All calls are low frequency: query the smallest candidate set, retry a cheap
  transient failure at most once, then switch adapter or local cache.
- Public board/concept constituents are discovery signals only, never proof of
  industrial exposure.
"""
from __future__ import annotations

import gzip
import json
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

Result = tuple[Any | None, str | None]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def bs_code(code: str) -> str:
    """Normalize a 6-digit A-share code to baostock ``sh.``/``sz.`` form."""
    normalized = code.strip().lower().replace("sh", "").replace("sz", "").replace(".", "")
    prefix = "sh" if normalized.startswith(("6", "9")) else "sz"
    return f"{prefix}.{normalized}"


def _retry_once(call: Callable[[], Result], *, backoff_seconds: float = 1.0) -> Result:
    payload, error = call()
    if payload is not None or error is None:
        return payload, error
    time.sleep(backoff_seconds)
    return call()


# --- akshare -----------------------------------------------------------------

def try_akshare_main_business(code: str) -> Result:
    """Main-business / product text via akshare THS endpoint."""

    def _call() -> Result:
        try:
            import akshare as ak

            frame = ak.stock_zyjs_ths(symbol=code)
            return frame.to_dict(orient="records"), None
        except Exception as exc:  # noqa: BLE001 - adapters must not raise
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


def try_akshare_board_cons(board_name: str) -> Result:
    """Industry-board constituents (discovery candidates only, not exposure proof)."""

    def _call() -> Result:
        try:
            import akshare as ak

            frame = ak.stock_board_industry_cons_em(symbol=board_name)
            return frame.to_dict(orient="records"), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


def try_akshare_concept_cons(concept_name: str) -> Result:
    """Concept-board constituents (discovery candidates only, not exposure proof).

    Many thematic chains (创新药、AI、算力、机器人等) are concept boards rather than
    industry boards. Use this when the user's theme does not match a clean industry
    vertical; never treat concept constituents as proof of industrial exposure.
    """

    def _call() -> Result:
        try:
            import akshare as ak

            frame = ak.stock_board_concept_cons_em(symbol=concept_name)
            return frame.to_dict(orient="records"), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


def try_akshare_board_fund_flow(board_name: str, *, is_concept: bool = False) -> Result:
    """Board-level fund-flow snapshot (heat signal, not exposure proof).

    Returns the fund-flow data for an industry or concept board. Useful for gauging
    market heat around a chain theme but says nothing about company-level exposure.
    """

    def _call() -> Result:
        try:
            import akshare as ak

            if is_concept:
                frame = ak.stock_board_concept_name_em()
            else:
                frame = ak.stock_board_industry_name_em()
            row = frame[frame["板块名称"].astype(str).str.contains(board_name, na=False)]
            return row.to_dict(orient="records"), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


def try_akshare_cninfo_disclosure(
    code: str,
    *,
    keyword: str = "",
    category: str = "",
    start_date: str,
    end_date: str,
) -> Result:
    """CNINFO announcement search via AkShare.

    Use this for low-frequency evidence discovery from 巨潮资讯公告, such as annual
    reports, capacity announcements, order announcements, and investor-facing
    disclosures. Dates use ``YYYYMMDD``.
    """

    def _call() -> Result:
        try:
            import akshare as ak

            frame = ak.stock_zh_a_disclosure_report_cninfo(
                symbol=code,
                market="沪深京",
                keyword=keyword,
                category=category,
                start_date=start_date,
                end_date=end_date,
            )
            return frame.to_dict(orient="records"), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


def try_akshare_individual_notice(
    code: str,
    *,
    notice_type: str = "全部",
    begin_date: str | None = None,
    end_date: str | None = None,
) -> Result:
    """Eastmoney single-stock announcement list via AkShare.

    Use as a backup when CNINFO search is unavailable. Dates use the endpoint's
    expected ``YYYYMMDD`` string when provided.
    """

    def _call() -> Result:
        try:
            import akshare as ak

            frame = ak.stock_individual_notice_report(
                security=code,
                symbol=notice_type,
                begin_date=begin_date,
                end_date=end_date,
            )
            return frame.to_dict(orient="records"), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


def try_akshare_cninfo_profile(code: str) -> Result:
    """CNINFO company profile via AkShare."""

    def _call() -> Result:
        try:
            import akshare as ak

            frame = ak.stock_profile_cninfo(symbol=code)
            return frame.to_dict(orient="records"), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


# --- unified entry points ----------------------------------------------------

def try_main_business(code: str) -> tuple[Result, str]:
    """Fetch main-business / product text for a single A-share stock.

    Uses akshare THS endpoint as the primary source. Returns
    ``((payload, error), source)`` so the caller can record the source in the
    trail. ``source`` is always ``"akshare"`` when data is available, and
    ``"none"`` when the call fails.
    """
    payload, error = try_akshare_main_business(code)
    if error is None and payload is not None:
        return (payload, None), "akshare"
    return (None, error), "none"


# --- baostock ----------------------------------------------------------------

def try_baostock_daily(code: str, start: str, end: str) -> Result:
    """Daily K-line backup via baostock. Logs in/out once per call."""
    try:
        import baostock as bs
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"

    try:
        login = bs.login()
        if login.error_code != "0":
            return None, f"login failed: {login.error_msg}"
        rs = bs.query_history_k_data_plus(
            bs_code(code),
            "date,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag="2",
        )
        rows: list[list[str]] = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        if rs.error_code != "0":
            return None, rs.error_msg
        return rows, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    finally:
        try:
            bs.logout()
        except Exception:  # noqa: BLE001 - cleanup must not raise
            pass


# --- efinance ----------------------------------------------------------------

def try_efinance_quote_snapshot(code: str) -> Result:
    """Single-stock quote snapshot via efinance/Eastmoney."""

    def _call() -> Result:
        try:
            import efinance as ef

            series = ef.stock.get_quote_snapshot(code)
            return series.to_dict(), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


def try_efinance_base_info(code: str) -> Result:
    """Single-stock base information via efinance/Eastmoney."""

    def _call() -> Result:
        try:
            import efinance as ef

            series = ef.stock.get_base_info(code)
            return series.to_dict(), None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


# --- SEC EDGAR ---------------------------------------------------------------

def try_sec_submissions(cik: str, *, user_agent: str = "stock-analysis/0.1 research@example.com") -> Result:
    """Fetch SEC EDGAR company submissions JSON for overseas suppliers.

    Use only for global supply-chain companies such as NVIDIA, Marvell, Broadcom,
    Coherent, Lumentum, etc. The SEC requires a descriptive User-Agent; callers
    may override the default with a team/contact string when available.
    """

    normalized = cik.strip().lstrip("0").zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{normalized}.json"

    def _call() -> Result:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - public SEC endpoint
                raw = response.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))
            recent = data.get("filings", {}).get("recent", {})
            return {
                "cik": data.get("cik"),
                "name": data.get("name"),
                "tickers": data.get("tickers"),
                "forms": recent.get("form", [])[:20],
                "filing_dates": recent.get("filingDate", [])[:20],
                "accession_numbers": recent.get("accessionNumber", [])[:20],
            }, None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


# --- adata -------------------------------------------------------------------

def try_adata_probe() -> Result:
    """Inspect adata's available top-level functions once per run (API varies by version)."""

    def _call() -> Result:
        try:
            import adata

            available = [name for name in dir(adata) if not name.startswith("_")]
            return {"available": available[:30]}, None
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"

    return _retry_once(_call)


# --- source trail ------------------------------------------------------------

@dataclass
class SourceEntry:
    tool: str  # akshare | baostock | adata | efinance | sec-edgar | local-cache | filing | news
    function_or_path: str
    subject: str
    status: str  # ok | fallback | failed | partial
    queried_at: str = field(default_factory=_now_iso)
    rows: int | None = None
    error: str | None = None
    confidence: str = "Medium"  # High | Medium | Low


class SourceTrail:
    """Accumulate adapter outcomes and write a compact ``source_data.json``."""

    def __init__(self) -> None:
        self._entries: list[SourceEntry] = []

    def record(
        self,
        *,
        tool: str,
        function_or_path: str,
        subject: str,
        payload: Any | None,
        error: str | None,
        confidence: str = "Medium",
        fallback: bool = False,
    ) -> SourceEntry:
        if error is not None:
            status = "failed"
        elif fallback:
            status = "fallback"
        else:
            status = "ok"
        rows: int | None = None
        if isinstance(payload, list):
            rows = len(payload)
        elif hasattr(payload, "__len__") and not isinstance(payload, (str, bytes, dict)):
            try:
                rows = len(payload)  # type: ignore[arg-type]
            except TypeError:
                rows = None
        entry = SourceEntry(
            tool=tool,
            function_or_path=function_or_path,
            subject=subject,
            status=status,
            rows=rows,
            error=error,
            confidence=confidence,
        )
        self._entries.append(entry)
        return entry

    def to_list(self) -> list[dict[str, Any]]:
        return [asdict(entry) for entry in self._entries]

    def write(self, output_path: str | Path, extra: dict[str, Any] | None = None) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        document: dict[str, Any] = {"generated_at": _now_iso(), "sources": self.to_list()}
        if extra:
            document.update(extra)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    @classmethod
    def from_health_check(cls, health_report: dict[str, Any]) -> "SourceTrail":
        """Build a SourceTrail pre-filled with a health-check report.

        The health-check JSON comes from ``check_data_sources.check()`` or
        ``scripts/check_data_sources.py``. Each adapter becomes a pre-recorded
        entry so the report generator does not need to re-probe adapters that
        are already known to be unreachable.
        """
        trail = cls()
        adapters = health_report.get("adapters", {})
        fn_map = {
            "akshare_main_business": ("akshare", "stock_zyjs_ths"),
            "akshare_concept_cons": ("akshare", "stock_board_concept_cons_em"),
            "akshare_board_fund_flow": ("akshare", "stock_board_concept_name_em"),
            "akshare_cninfo_disclosure": ("akshare", "stock_zh_a_disclosure_report_cninfo"),
            "akshare_cninfo_profile": ("akshare", "stock_profile_cninfo"),
            "baostock_daily": ("baostock", "query_history_k_data_plus"),
            "efinance_quote_snapshot": ("efinance", "get_quote_snapshot"),
            "efinance_base_info": ("efinance", "get_base_info"),
            "adata_probe": ("adata", "probe"),
            "sec_submissions": ("sec-edgar", "submissions"),
        }
        probe_code = health_report.get("probe_code", "unknown")
        for key, info in adapters.items():
            tool, fn = fn_map.get(key, (key.split("_", 1)[0], key))
            status = info.get("status", "failed")
            detail = info.get("detail", "")
            trail.record(
                tool=tool,
                function_or_path=f"{fn} (health-check)",
                subject=probe_code,
                payload=[] if status == "available" else None,
                error=None if status == "available" else detail,
                confidence="Low",
            )
        return trail


# --- markdown table rendering ------------------------------------------------

COMPANY_MAPPING_COLUMNS: list[str] = [
    "公司", "代码", "环节", "细分领域", "产业占比/暴露度",
    "核心技术/产品", "卡脖子相关性", "环节地位", "证据与备注",
]

CHAIN_OVERVIEW_COLUMNS: list[str] = ["环节", "细分领域", "关键价值/壁垒", "代表A股公司"]

UPSTREAM_MATERIAL_COLUMNS: list[str] = [
    "上游层级", "细分材料/部件", "对目标产业的作用",
    "价值/稀缺性", "卡脖子程度", "A股候选", "纳入主线判断",
]

CORE_VALUE_DISTRIBUTION_COLUMNS: list[str] = [
    "产业链环节", "细分领域/关键产品", "BOM成本占比/价值占比",
    "核心技术壁垒", "卡脖子程度", "代表A股公司", "公司环节地位", "证据口径/备注",
]


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([head, sep, *body])


def render_company_mapping_table(rows: list[dict[str, str]]) -> str:
    """Render the canonical 9-column company-mapping table from dicts.

    Each dict uses the keys from ``COMPANY_MAPPING_COLUMNS``. Missing keys
    render as empty cells so the table always has 9 columns.
    """
    data = [[row.get(col, "") for col in COMPANY_MAPPING_COLUMNS] for row in rows]
    return _md_table(COMPANY_MAPPING_COLUMNS, data)


def render_chain_overview_table(rows: list[dict[str, str]]) -> str:
    """Render the 4-column chain overview table used in Light mode."""
    data = [[row.get(col, "") for col in CHAIN_OVERVIEW_COLUMNS] for row in rows]
    return _md_table(CHAIN_OVERVIEW_COLUMNS, data)


def render_upstream_material_table(rows: list[dict[str, str]]) -> str:
    """Render the 7-column upstream-material discovery table."""
    data = [[row.get(col, "") for col in UPSTREAM_MATERIAL_COLUMNS] for row in rows]
    return _md_table(UPSTREAM_MATERIAL_COLUMNS, data)


def render_core_value_distribution_table(rows: list[dict[str, str]]) -> str:
    """Render the core chain-link value distribution table.

    This table is different from the company-mapping table: it starts from
    industry-chain links and cost/value distribution, then lists representative
    A-share companies. Use it before the detailed 9-column company mapping in
    Standard and Report outputs.
    """
    data = [[row.get(col, "") for col in CORE_VALUE_DISTRIBUTION_COLUMNS] for row in rows]
    return _md_table(CORE_VALUE_DISTRIBUTION_COLUMNS, data)


SOURCE_TRAIL_COLUMNS: list[str] = [
    "数据项", "工具", "接口/函数", "状态", "记录数", "置信度", "错误/备注",
]


def render_source_trail_table(entries: list[dict[str, Any]] | list[SourceEntry]) -> str:
    """Render the source-trail diagnostic table from SourceEntry dicts.

    Use for run logs, debugging, or internal review only. Reader-facing reports
    should use a compact claim-level source summary instead of exposing raw
    adapter names, functions, retries, or failures. Accepts either a list of
    ``SourceEntry`` objects or the dict list from ``SourceTrail.to_list()``.
    """
    rows: list[list[str]] = []
    for entry in entries:
        if isinstance(entry, SourceEntry):
            d = asdict(entry)
        else:
            d = entry
        status_map = {"ok": "可用", "failed": "失败", "fallback": "降级", "partial": "部分"}
        status_cn = status_map.get(d.get("status", ""), d.get("status", ""))
        rows_val = str(d.get("rows", "")) if d.get("rows") is not None else "-"
        error = d.get("error") or ""
        rows.append([
            d.get("subject", ""),
            d.get("tool", ""),
            d.get("function_or_path", ""),
            status_cn,
            rows_val,
            d.get("confidence", ""),
            error,
        ])
    return _md_table(SOURCE_TRAIL_COLUMNS, rows)
