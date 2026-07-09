from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop_os.state_machine.catalyst_state import can_transition


STATE_FILES = {
    "research_state": "research-state.json",
    "catalysts_state": "catalysts.json",
    "watchlist_state": "watchlist.json",
    "portfolio_state": "paper-portfolio.json",
    "health_state": "system-health.json",
}

ALLOWED_NEW_CATALYST_STATUSES = {"discovered", "validating", "rejected"}
ALLOWED_WATCHLIST_STATUSES = {"candidate", "watching", "paper_candidate", "rejected"}
PRESERVE_CATALYST_STATUSES = {"validating", "confirmed", "priced_in", "expired", "rejected"}


@dataclass
class StateTransitionDraft:
    states: dict[str, dict[str, Any]]
    summary: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha1(value.encode('utf-8')).hexdigest()[:12]}"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_states(root: Path) -> dict[str, dict[str, Any]]:
    state_dir = root / "state"
    return {name: _read_json(state_dir / filename) for name, filename in STATE_FILES.items()}


def _upsert_by_id(items: list[dict[str, Any]], item: dict[str, Any]) -> None:
    for idx, existing in enumerate(items):
        if existing.get("id") == item.get("id"):
            merged = {**existing, **item}
            history = existing.get("history", [])
            if item.get("history_event"):
                history = history + [item["history_event"]]
            merged.pop("history_event", None)
            merged["history"] = history[-20:]
            items[idx] = merged
            return
    history_event = item.pop("history_event", None)
    item["history"] = [history_event] if history_event else []
    items.append(item)


def _select_evidence_ids(evidence_ids: list[str], limit: int) -> list[str]:
    return [item for item in evidence_ids if item][:limit]


def _load_known_evidence_ids(root: Path) -> set[str]:
    evidence_root = root / "evidence"
    if not evidence_root.exists():
        return set()

    known: set[str] = set()
    for raw_index_path in evidence_root.glob("*/raw-index.json"):
        try:
            index = json.loads(raw_index_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        known.update(str(item) for item in index.get("evidence_ids", []) if item)

    for claim_index_path in evidence_root.glob("*/claim-index.json"):
        try:
            index = json.loads(claim_index_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        claims = index.get("claims", {})
        if isinstance(claims, dict):
            known.update(str(item.get("evidence_id")) for item in claims.values() if isinstance(item, dict) and item.get("evidence_id"))

    known.update(path.stem for path in evidence_root.glob("*/ev-*.json"))
    return known


def build_state_transition_draft(
    root: Path,
    run_id: str,
    cycle: int,
    payload: dict[str, Any],
    evidence_ids: list[str],
) -> StateTransitionDraft:
    now = _utc_now()
    states = copy.deepcopy(_read_states(root))

    research_state = states["research_state"]
    catalysts_state = states["catalysts_state"]
    watchlist_state = states["watchlist_state"]
    portfolio_state = states["portfolio_state"]
    health_state = states["health_state"]

    pipeline = payload.get("research_pipeline", {})
    selected_chain = pipeline.get("selected_industry_chain", {}) if isinstance(pipeline, dict) else {}
    scoring = pipeline.get("hotspot_scoring", {}) if isinstance(pipeline, dict) else {}
    decisions = pipeline.get("trade_decision_engine", {}).get("decisions", []) if isinstance(pipeline, dict) else []

    top_buckets = [(item.get("theme"), item.get("score", 0)) for item in scoring.get("ranked_themes", [])]
    if selected_chain:
        selected_theme = selected_chain.get("selected_theme") or "unknown"
        selected_score = selected_chain.get("score", 0)
        top_buckets = [(selected_theme, selected_score)] + [item for item in top_buckets if item[0] != selected_theme]
    if not top_buckets:
        top_buckets = payload.get("industry_analysis", {}).get("top_theme_buckets", [])

    themes = research_state.setdefault("themes", [])
    for bucket, count in top_buckets[:5]:
        theme_id = _id("theme", str(bucket))
        _upsert_by_id(
            themes,
            {
                "id": theme_id,
                "name": str(bucket),
                "status": "tracking" if count >= 2 else "discovered",
                "last_seen_at": now,
                "signal_count": count,
                "evidence_ids": _select_evidence_ids(evidence_ids, 8),
                "next_action": "run_industry_chain_validation",
                "history_event": {"at": now, "cycle": cycle, "signal_count": count},
            },
        )

    catalysts = catalysts_state.setdefault("catalysts", [])
    chain_items = selected_chain.get("supporting_public_items", []) if selected_chain else []
    for item in chain_items[:8]:
        _upsert_catalyst(catalysts, item, selected_chain, evidence_ids, now, cycle)

    for catalyst in payload.get("industry_analysis", {}).get("catalysts", [])[:8]:
        _upsert_catalyst(catalysts, catalyst, catalyst, evidence_ids, now, cycle)

    watchlist = watchlist_state.setdefault("watchlist", [])
    decision_by_symbol = {str(item.get("symbol")): item for item in decisions if item.get("symbol")}
    for quote in payload.get("a_share_quotes", []):
        _upsert_watchlist_item(watchlist, quote, decision_by_symbol, evidence_ids, now, cycle)

    if portfolio_state.get("cash") is None:
        portfolio_state["cash"] = 1_000_000.0
    portfolio_state.setdefault("positions", [])
    reviews = portfolio_state.setdefault("reviews", [])
    reviews.append(
        {
            "at": now,
            "run_id": run_id,
            "cycle": cycle,
            "decision": payload.get("agent_review", {}).get("decision"),
            "committee_rating": payload.get("tradingagents_review", {}).get("portfolio_rating"),
            "committee_action": payload.get("tradingagents_review", {}).get("trader_action"),
            "selected_theme": selected_chain.get("selected_theme"),
            "position_count": len(portfolio_state["positions"]),
            "cash": portfolio_state["cash"],
            "evidence_ids": _select_evidence_ids(list(reversed(evidence_ids)), 3),
            "note": "paper portfolio review only; no automatic real trading",
        }
    )
    portfolio_state["reviews"] = reviews[-100:]

    research_state["updated_at"] = now
    research_state.setdefault("loops", {})["full_loop"] = {
        "status": payload.get("status"),
        "last_run_id": run_id,
        "last_cycle": cycle,
        "last_run_at": now,
        "next_action": "continue_loop",
        "evidence_count": len(evidence_ids),
    }
    catalysts_state["updated_at"] = now
    watchlist_state["updated_at"] = now
    portfolio_state["updated_at"] = now
    health_state["updated_at"] = now
    health_state["last_full_loop"] = {
        "run_id": run_id,
        "cycle": cycle,
        "status": payload.get("status"),
        "errors": payload.get("errors", []),
        "finished_at": payload.get("finished_at"),
    }

    summary = {
        "themes": len(themes),
        "catalysts": len(catalysts),
        "watchlist": len(watchlist),
        "portfolio_reviews": len(portfolio_state["reviews"]),
        "validated": False,
        "committed": False,
    }
    return StateTransitionDraft(states=states, summary=summary)


def _upsert_catalyst(
    catalysts: list[dict[str, Any]],
    item: dict[str, Any],
    selected_chain: dict[str, Any],
    evidence_ids: list[str],
    now: str,
    cycle: int,
) -> None:
    title = str(item.get("title") or "")
    if not title:
        return
    catalyst_id = _id("cat", title)
    existing = next((candidate for candidate in catalysts if candidate.get("id") == catalyst_id), {})
    existing_status = str(existing.get("status") or "")
    status = existing_status if existing_status in PRESERVE_CATALYST_STATUSES else "validating"
    theme = selected_chain.get("selected_theme") or item.get("industry") or "unknown"
    _upsert_by_id(
        catalysts,
        {
            "id": catalyst_id,
            "theme_id": _id("theme", str(theme)),
            "status": status,
            "title": title,
            "source": item.get("source"),
            "industry": item.get("industry") or selected_chain.get("selected_theme"),
            "publish_date": item.get("published_at") or item.get("publish_date"),
            "hypothesis": item.get("hypothesis") or "公开新闻/研报标题形成产业链线索，需验证终端需求、卡口和A股收入暴露。",
            "evidence_ids": _select_evidence_ids(evidence_ids, 12),
            "next_action": existing.get("next_action") or "verify_primary_sources_and_a_share_exposure",
            "last_seen_at": now,
            "history_event": {"at": now, "cycle": cycle, "status": status},
        },
    )


def _upsert_watchlist_item(
    watchlist: list[dict[str, Any]],
    quote: dict[str, Any],
    decision_by_symbol: dict[str, dict[str, Any]],
    evidence_ids: list[str],
    now: str,
    cycle: int,
) -> None:
    symbol = str(quote.get("symbol") or "")
    decision = decision_by_symbol.get(symbol, {})
    action = decision.get("action")
    status = "candidate"
    next_action = "collect_fundamental_and_catalyst_evidence"
    if action == "paper_candidate":
        status = "paper_candidate"
        next_action = "paper_trade_only_after_manual_challenge"
    elif action == "reject_or_wait" or quote.get("valuation_band") == "high":
        status = "rejected"
        next_action = "wait_for_valuation_or_fundamental_confirmation"
    elif action == "watch" or (quote.get("change_pct") is not None and quote["change_pct"] > 0):
        status = "watching"

    _upsert_by_id(
        watchlist,
        {
            "id": _id("watch", symbol),
            "symbol": symbol,
            "name": quote.get("name"),
            "status": status,
            "last_price": quote.get("price"),
            "valuation_band": quote.get("valuation_band"),
            "decision_gate": decision,
            "evidence_ids": _select_evidence_ids(evidence_ids, 8),
            "next_action": next_action,
            "last_seen_at": now,
            "history_event": {"at": now, "cycle": cycle, "status": status, "price": quote.get("price")},
        },
    )


def validate_state_transition(root: Path, draft: StateTransitionDraft) -> list[str]:
    errors: list[str] = []
    current = _read_states(root)
    known_evidence_ids = _load_known_evidence_ids(root)
    current_catalysts = {
        item.get("id"): item.get("status")
        for item in current["catalysts_state"].get("catalysts", [])
        if isinstance(item, dict) and item.get("id")
    }

    for item in draft.states["catalysts_state"].get("catalysts", []):
        status = item.get("status")
        source = current_catalysts.get(item.get("id"))
        if not item.get("evidence_ids"):
            errors.append(f"catalyst {item.get('id')} missing evidence_ids")
        errors.extend(_missing_evidence_errors("catalyst", item.get("id"), item.get("evidence_ids", []), known_evidence_ids))
        if source is None and status not in ALLOWED_NEW_CATALYST_STATUSES:
            errors.append(f"catalyst {item.get('id')} has invalid initial status {status}")
        if source is not None and status != source and not can_transition(str(source), str(status)):
            errors.append(f"catalyst {item.get('id')} invalid transition {source}->{status}")

    for item in draft.states["watchlist_state"].get("watchlist", []):
        status = item.get("status")
        if status not in ALLOWED_WATCHLIST_STATUSES:
            errors.append(f"watchlist {item.get('id')} invalid status {status}")
        if not item.get("evidence_ids"):
            errors.append(f"watchlist {item.get('id')} missing evidence_ids")
        errors.extend(_missing_evidence_errors("watchlist", item.get("id"), item.get("evidence_ids", []), known_evidence_ids))

    latest_review = draft.states["portfolio_state"].get("reviews", [])[-1:]
    for review in latest_review:
        if not review.get("evidence_ids"):
            errors.append("portfolio review missing evidence_ids")
        errors.extend(_missing_evidence_errors("portfolio review", review.get("run_id"), review.get("evidence_ids", []), known_evidence_ids))

    loop_state = draft.states["research_state"].get("loops", {}).get("full_loop", {})
    if not loop_state.get("evidence_count"):
        errors.append("full_loop state missing evidence_count")

    return errors


def _missing_evidence_errors(kind: str, item_id: Any, evidence_ids: list[str], known_evidence_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(evidence_ids, list):
        return errors
    for evidence_id in evidence_ids:
        if evidence_id not in known_evidence_ids:
            errors.append(f"{kind} {item_id} references missing evidence_id {evidence_id}")
    return errors


def commit_state_transition(root: Path, draft: StateTransitionDraft) -> dict[str, Any]:
    state_dir = root / "state"
    for key, filename in STATE_FILES.items():
        _write_json(state_dir / filename, draft.states[key])
    return {**draft.summary, "validated": True, "committed": True}


def apply_state_transition(root: Path, run_id: str, cycle: int, payload: dict[str, Any], evidence_ids: list[str]) -> dict[str, Any]:
    draft = build_state_transition_draft(root, run_id, cycle, payload, evidence_ids)
    errors = validate_state_transition(root, draft)
    if errors:
        raise ValueError(f"state transition validation failed: {errors}")
    return commit_state_transition(root, draft)
