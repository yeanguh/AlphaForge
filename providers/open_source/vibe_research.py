from __future__ import annotations

from pathlib import Path
from typing import Any

from loop_os.schemas.provider import ProviderResult


ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = ROOT / "external" / "Vibe-Research"
ASTOCK_SKILL = SUBMODULE / "a-stock-data" / "SKILL.md"
BACKEND_ASTOCK = SUBMODULE / "backend" / "astock.py"


def _display_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def smoke(live: bool = False) -> ProviderResult:
    readme = SUBMODULE / "README.md"
    if not readme.exists():
        return ProviderResult("Vibe-Research", "error", "README missing", errors=[_display_path(readme)])
    capabilities = []
    if ASTOCK_SKILL.exists():
        capabilities.append("a-stock-data skill snapshot")
    if BACKEND_ASTOCK.exists():
        capabilities.append("backend astock data layer")
    return ProviderResult("Vibe-Research", "ok", "runtime adapter readable; data workbench capabilities available", {"path": _display_path(SUBMODULE), "capabilities": capabilities})


def _rows(section: Any) -> list[dict[str, Any]]:
    if isinstance(section, dict) and isinstance(section.get("rows"), list):
        return [x for x in section["rows"] if isinstance(x, dict)]
    return []


def _coverage(symbol: str, supplement: dict[str, Any]) -> dict[str, Any]:
    financials = supplement.get("financials", {}) if isinstance(supplement, dict) else {}
    statements = financials.get("statements", {}) if isinstance(financials, dict) else {}
    indicators = statements.get("indicators", []) if isinstance(statements, dict) else []
    history_rows = _rows(supplement.get("price_history", {}))
    return {
        "symbol": symbol,
        "history_rows": len(history_rows),
        "financial_periods": len(indicators) if isinstance(indicators, list) else 0,
        "announcements": len(_rows(supplement.get("announcements", {}))),
        "research_reports": len(_rows(supplement.get("research_reports", {}))),
        "fund_flow_rows": len(_rows(supplement.get("fund_flow", {}))),
        "dragon_tiger_rows": len(_rows(supplement.get("dragon_tiger", {}))),
    }


def research_packet(payload: dict[str, Any], pipeline: dict[str, Any]) -> dict[str, Any]:
    """Return Vibe-Research style data workbench insight without mutating state.

    The external project is kept behind this provider adapter. We reuse the
    current loop's normalized public data/cache instead of importing UI/runtime
    modules directly, so a missing optional dependency cannot block the loop.
    """
    supplements = payload.get("stock_supplements", {})
    supplements = supplements if isinstance(supplements, dict) else {}
    coverage = [_coverage(str(symbol), supp) for symbol, supp in supplements.items() if isinstance(supp, dict)]
    rich = [row for row in coverage if row["history_rows"] >= 60 and row["financial_periods"] > 0]
    weak = [
        row["symbol"]
        for row in coverage
        if row["history_rows"] < 60 or row["financial_periods"] == 0 or row["research_reports"] == 0
    ][:10]
    chain = pipeline.get("selected_industry_chain", {}) if isinstance(pipeline, dict) else {}
    stock_reports = pipeline.get("stock_analyzer", []) if isinstance(pipeline, dict) else []
    stock_reports = [x for x in stock_reports if isinstance(x, dict)]
    sample_notes = []
    for item in stock_reports[:6]:
        coverage_row = next((row for row in coverage if row["symbol"] == str(item.get("symbol"))), {})
        sample_notes.append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "valuation": item.get("valuation", {}),
                "coverage": coverage_row,
                "evidence_note": "财务、研报、公告、K线均可用于工作台交叉验证" if coverage_row and coverage_row.get("financial_periods") else "仍需补齐财务/公告/研报缓存",
            }
        )
    status = "ok" if rich else "warn"
    claims = [
        f"Vibe-Research workbench reused normalized A-share data for {len(coverage)} symbols.",
        f"Symbols with usable K-line+financial coverage: {len(rich)}.",
        f"Selected theme for workbench context: {chain.get('selected_theme')}.",
    ]
    if weak:
        claims.append(f"Weak coverage symbols requiring fallback or later enrichment: {','.join(weak)}.")
    return {
        "provider": "Vibe-Research",
        "status": status,
        "source_submodule": "external/Vibe-Research",
        "adapter": "providers.open_source.vibe_research.research_packet",
        "capabilities_reused": ["a-stock-data", "backend/astock.py data workbench pattern", "report/dashboard evidence organization"],
        "claims": claims,
        "coverage": coverage,
        "sample_notes": sample_notes,
        "errors": [] if status == "ok" else ["some symbols have incomplete local/public data coverage"],
        "state_mutation_allowed": False,
    }
