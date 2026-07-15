from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _load_request() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        return {"errors": [f"invalid_json: {exc}"]}
    return value if isinstance(value, dict) else {"errors": ["request must be a JSON object"]}


def _symbol_rows(payload: dict[str, Any], pipeline: dict[str, Any]) -> list[dict[str, Any]]:
    supplements = _as_dict(payload.get("stock_supplements"))
    stocks = [x for x in _as_list(pipeline.get("stock_analyzer")) if isinstance(x, dict)]
    decisions = _as_dict(pipeline.get("trade_decision_engine")).get("decisions", [])
    decisions = [x for x in _as_list(decisions) if isinstance(x, dict)]
    by_symbol = {str(x.get("symbol") or ""): x for x in stocks}
    rows: list[dict[str, Any]] = []
    for decision in decisions[:12]:
        symbol = str(decision.get("symbol") or "")
        stock = by_symbol.get(symbol, {})
        supplement = _as_dict(supplements.get(symbol))
        price_history = _as_dict(supplement.get("price_history"))
        financials = _as_dict(_as_dict(supplement.get("financials")).get("statements"))
        rows.append(
            {
                "symbol": symbol,
                "name": decision.get("name") or stock.get("name"),
                "action": decision.get("action"),
                "valuation": _as_dict(stock.get("valuation")),
                "technical": _as_dict(stock.get("technical")),
                "history_rows": len(_as_list(price_history.get("rows"))),
                "financial_periods": len(_as_list(financials.get("indicators"))),
                "research_report_rows": len(_as_list(_as_dict(supplement.get("research_reports")).get("rows"))),
            }
        )
    return rows


def _matching_skill_names(all_names: list[str]) -> list[str]:
    wanted = (
        "alpha-zoo",
        "asset-allocation",
        "backtest",
        "factor",
        "risk",
        "technical",
        "shadow",
        "candlestick",
        "behavioral",
    )
    matches = []
    for name in all_names:
        lower = name.lower()
        if any(token in lower for token in wanted):
            matches.append(name)
    return matches[:24]


def _build_packet(request: dict[str, Any]) -> dict[str, Any]:
    payload = _as_dict(request.get("payload"))
    pipeline = _as_dict(request.get("pipeline"))
    errors = [str(item) for item in _as_list(request.get("errors"))]

    from src.agent.skills import SkillsLoader
    import api_server
    import mcp_server

    loader = SkillsLoader()
    skill_names = [str(skill.name) for skill in loader.skills]
    symbol_rows = _symbol_rows(payload, pipeline)
    thin_coverage = [
        row["symbol"]
        for row in symbol_rows
        if row.get("history_rows", 0) < 60 or row.get("financial_periods", 0) == 0
    ]
    candidate_count = sum(1 for row in symbol_rows if row.get("action") == "paper_candidate")
    wait_count = sum(1 for row in symbol_rows if row.get("action") == "reject_or_wait")
    chain = _as_dict(pipeline.get("selected_industry_chain"))
    claims = [
        f"Vibe-Trading runtime loaded {len(skill_names)} finance skills.",
        f"Vibe-Trading API app import verified: {api_server.app.title} {api_server.app.version}.",
        f"Vibe-Trading MCP module import verified: {mcp_server.APP_VERSION}.",
        f"Runtime reviewed {len(symbol_rows)} loop decision rows: paper_candidate={candidate_count}, reject_or_wait={wait_count}.",
    ]
    if thin_coverage:
        claims.append(f"Symbols needing richer history/fundamental coverage before backtest: {','.join(thin_coverage[:8])}.")
    if chain.get("selected_theme"):
        claims.append(f"Runtime context theme={chain.get('selected_theme')}.")

    return {
        "provider": "Vibe-Trading Agent",
        "status": "ok" if not errors else "warn",
        "source_submodule": "external/Vibe-Trading",
        "adapter": "scripts/run_vibe_trading_agent.py",
        "runtime": {
            "api_app": api_server.app.title,
            "api_version": api_server.app.version,
            "mcp_version": mcp_server.APP_VERSION,
            "skill_count": len(skill_names),
            "loaded_at": _utc_now(),
        },
        "capabilities_verified": [
            "skills_loader",
            "api_app_import",
            "mcp_module_import",
            "loop_decision_review",
        ],
        "skill_probe": {
            "matched_finance_skills": _matching_skill_names(skill_names),
            "all_skill_count": len(skill_names),
        },
        "symbol_rows": symbol_rows,
        "claims": claims,
        "errors": errors,
        "state_mutation_allowed": False,
    }


def main() -> None:
    request = _load_request()
    try:
        packet = _build_packet(request)
    except Exception as exc:  # noqa: BLE001
        packet = {
            "provider": "Vibe-Trading Agent",
            "status": "warn",
            "source_submodule": "external/Vibe-Trading",
            "adapter": "scripts/run_vibe_trading_agent.py",
            "claims": [f"Vibe-Trading runtime one-shot failed: {exc!r}"],
            "errors": [repr(exc)],
            "state_mutation_allowed": False,
        }
    print(json.dumps(packet, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
