from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REQUIRED_STATE_KEYS = {
    "research_state",
    "catalysts_state",
    "watchlist_state",
    "portfolio_state",
    "health_state",
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9][A-Za-z0-9_.-]{16,}"),
    re.compile(r"(?i)authorization\s*[:=]\s*['\"]?bearer\s+[A-Za-z0-9_.-]{16,}"),
]


def run_precommit_state_harness(root: Path, draft: Any) -> list[str]:
    """Validate a state draft before it is committed to state/*.json."""
    errors: list[str] = []
    errors.extend(_check_policy(root))
    errors.extend(_check_draft_shape(draft))
    errors.extend(_check_no_secrets_in_draft(draft))
    return errors


def _check_policy(root: Path) -> list[str]:
    path = root / "config" / "policy.yaml"
    if not path.exists():
        return ["policy.yaml missing"]

    text = path.read_text(encoding="utf-8")
    if "allow_real_trading: false" not in text:
        return ["policy allow_real_trading must remain false"]
    if "require_evidence_for_state_change: true" not in text:
        return ["policy require_evidence_for_state_change must remain true"]
    return []


def _check_draft_shape(draft: Any) -> list[str]:
    states = getattr(draft, "states", None)
    if not isinstance(states, dict):
        return ["state transition draft missing states"]

    missing = sorted(REQUIRED_STATE_KEYS - set(states.keys()))
    errors = [f"state transition draft missing {key}" for key in missing]
    for key in sorted(REQUIRED_STATE_KEYS & set(states.keys())):
        state = states.get(key)
        if not isinstance(state, dict):
            errors.append(f"state transition draft {key} must be object")
            continue
        if not state.get("schema_version"):
            errors.append(f"state transition draft {key} missing schema_version")
    return errors


def _check_no_secrets_in_draft(draft: Any) -> list[str]:
    try:
        text = json.dumps(getattr(draft, "states", {}), ensure_ascii=False)
    except Exception as exc:
        return [f"state transition draft not JSON serializable: {exc!r}"]

    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return ["state transition draft contains possible secret"]
    return []

