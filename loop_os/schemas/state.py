from __future__ import annotations

import json
from pathlib import Path


REQUIRED_STATE_FILES = [
    "research-state.json",
    "catalysts.json",
    "watchlist.json",
    "paper-portfolio.json",
    "system-health.json",
]


def load_state_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain one root object")
    if "schema_version" not in data:
        raise ValueError(f"{path} missing schema_version")
    return data
