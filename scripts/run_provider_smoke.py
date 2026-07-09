from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from providers.open_source import (
    a_stock_data,
    global_stock_data,
    investment_news,
    tradingagents_astock,
    vibe_research,
    vibe_trading,
    wen_cai,
)
from loop_os.schemas.provider import ProviderResult


def run(live: bool = False) -> dict:
    providers: list[tuple[str, Callable[[bool], ProviderResult]]] = [
        ("a-stock-data", a_stock_data.smoke),
        ("investment-news", investment_news.smoke),
        ("global-stock-data", global_stock_data.smoke),
        ("TradingAgents-astock", tradingagents_astock.smoke),
        ("Vibe-Research", vibe_research.smoke),
        ("Vibe-Trading", vibe_trading.smoke),
        ("wen-cai", wen_cai.smoke),
    ]
    results = [fn(live).to_dict() for _, fn in providers]
    status = "ok" if all(item["status"] in {"ok", "warn"} for item in results) else "error"
    payload = {"status": status, "live": live, "results": results}
    run_dir = ROOT / "runs" / datetime.now().strftime("%Y-%m-%d")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "provider-smoke.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="perform live network checks for active data providers")
    args = parser.parse_args()
    payload = run(live=args.live)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
