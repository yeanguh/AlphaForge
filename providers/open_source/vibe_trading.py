from __future__ import annotations

from pathlib import Path
from typing import Any

from loop_os.schemas.provider import ProviderResult


ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = ROOT / "external" / "Vibe-Trading"
DATA_ROUTING_SKILL = SUBMODULE / "agent" / "src" / "skills" / "data-routing" / "SKILL.md"
EASTMONEY_SKILL = SUBMODULE / "agent" / "src" / "skills" / "eastmoney" / "SKILL.md"


def _display_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def smoke(live: bool = False) -> ProviderResult:
    readme = SUBMODULE / "README.md"
    if not readme.exists():
        return ProviderResult("Vibe-Trading", "error", "README missing", errors=[_display_path(readme)])
    capabilities = []
    if DATA_ROUTING_SKILL.exists():
        capabilities.append("data-routing fallback contract")
    if EASTMONEY_SKILL.exists():
        capabilities.append("eastmoney public data contract")
    return ProviderResult("Vibe-Trading", "ok", "runtime adapter readable; strategy/data-routing capabilities available", {"path": _display_path(SUBMODULE), "capabilities": capabilities})


def _float(value: Any) -> float | None:
    try:
        if value in (None, "", "--", "-"):
            return None
        return float(value)
    except Exception:
        return None


def strategy_packet(payload: dict[str, Any], pipeline: dict[str, Any]) -> dict[str, Any]:
    """Return Vibe-Trading style routing/risk insight for the current loop.

    This adapter mirrors Vibe-Trading's data-routing discipline: free resilient
    sources first, key-gated providers only when configured, and per-provider
    failure represented inside the packet instead of raising into the loop.
    """
    decisions = pipeline.get("trade_decision_engine", {}).get("decisions", []) if isinstance(pipeline, dict) else []
    decisions = [x for x in decisions if isinstance(x, dict)]
    stocks = pipeline.get("stock_analyzer", []) if isinstance(pipeline, dict) else []
    stocks = [x for x in stocks if isinstance(x, dict)]
    by_symbol = {str(x.get("symbol")): x for x in stocks}
    risk_rows = []
    for decision in decisions[:12]:
        symbol = str(decision.get("symbol") or "")
        stock = by_symbol.get(symbol, {})
        valuation = stock.get("valuation", {}) if isinstance(stock.get("valuation"), dict) else {}
        technical = stock.get("technical", {}) if isinstance(stock.get("technical"), dict) else {}
        pe = _float(valuation.get("pe"))
        pb = _float(valuation.get("pb"))
        tech_score = _float(technical.get("score"))
        risk_flags = []
        if pe is not None and (pe < 0 or pe > 120):
            risk_flags.append("valuation_pressure")
        if pb is not None and pb > 20:
            risk_flags.append("high_pb")
        if tech_score is not None and tech_score < 2:
            risk_flags.append("technical_weakness")
        if decision.get("action") == "reject_or_wait":
            risk_flags.append("decision_wait")
        risk_rows.append(
            {
                "symbol": symbol,
                "name": decision.get("name") or stock.get("name"),
                "action": decision.get("action"),
                "passed_conditions": decision.get("passed_conditions"),
                "risk_flags": risk_flags or ["watch_with_evidence"],
                "source_priority": ["tencent", "eastmoney", "efinance", "baostock", "local-cache"],
            }
        )
    candidates = [row for row in risk_rows if row.get("action") == "paper_candidate"]
    waits = [row for row in risk_rows if row.get("action") == "reject_or_wait"]
    claims = [
        f"Vibe-Trading strategy adapter evaluated {len(risk_rows)} decision rows.",
        f"Paper candidates={len(candidates)}, reject_or_wait={len(waits)}.",
        "A-share routing priority uses free resilient sources before local cache fallback.",
    ]
    return {
        "provider": "Vibe-Trading",
        "status": "ok",
        "source_submodule": "external/Vibe-Trading",
        "adapter": "providers.open_source.vibe_trading.strategy_packet",
        "capabilities_reused": ["data-routing source priority", "eastmoney disclosure/fundamental contract", "strategy risk gating"],
        "claims": claims,
        "risk_rows": risk_rows,
        "routing_policy": {
            "a_share_ohlcv": ["tencent", "mootdx_if_available", "efinance", "baostock", "eastmoney_throttled", "local-cache"],
            "disclosure_fundamental": ["eastmoney_throttled", "local supplement cache"],
            "key_gated": ["OPENAI_BASE_URL", "OPENAI_API_KEY", "IWENCAI_BASE_URL", "IWENCAI_API_KEY"],
        },
        "errors": [],
        "state_mutation_allowed": False,
    }
