#!/usr/bin/env python3
"""Probe industry-chain public-data adapters before deciding online vs. cache.

Run this first so the analysis knows which adapters are reachable in the current
network, instead of discovering failures mid-report. Mirrors the health-check
pattern used by the daily-a-share-news-impact skill.

Examples:
    /usr/local/bin/uv run python check_data_sources.py
    /usr/local/bin/uv run python check_data_sources.py --probe-code 600276 --output ../../tmp/icc_sources.json
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from public_data import (  # noqa: E402
    try_adata_probe,
    try_akshare_board_fund_flow,
    try_akshare_cninfo_disclosure,
    try_akshare_cninfo_profile,
    try_akshare_concept_cons,
    try_akshare_main_business,
    try_baostock_daily,
    try_efinance_base_info,
    try_efinance_quote_snapshot,
    try_sec_submissions,
)


def _dependency(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _status(payload: object | None, error: str | None) -> dict[str, object]:
    if error is not None:
        return {"status": "failed", "detail": error}
    return {"status": "available", "detail": "ok"}


def check(
    probe_code: str,
    history_start: str,
    history_end: str,
    *,
    probe_concept: str = "创新药",
) -> dict[str, object]:
    deps = {
        name: _dependency(name) or "not_installed"
        for name in ("akshare", "baostock", "adata", "efinance")
    }

    ak_payload, ak_error = try_akshare_main_business(probe_code)
    bs_payload, bs_error = try_baostock_daily(probe_code, history_start, history_end)
    ad_payload, ad_error = try_adata_probe()
    concept_payload, concept_error = try_akshare_concept_cons(probe_concept)
    fund_payload, fund_error = try_akshare_board_fund_flow(probe_concept, is_concept=True)
    cninfo_payload, cninfo_error = try_akshare_cninfo_disclosure(
        probe_code,
        keyword="年报",
        start_date="20250101",
        end_date="20261231",
    )
    profile_payload, profile_error = try_akshare_cninfo_profile(probe_code)
    ef_quote_payload, ef_quote_error = try_efinance_quote_snapshot(probe_code)
    ef_base_payload, ef_base_error = try_efinance_base_info(probe_code)
    sec_payload, sec_error = try_sec_submissions("1045810")  # NVIDIA

    return {
        "probe_code": probe_code,
        "probe_concept": probe_concept,
        "dependencies": deps,
        "adapters": {
            "akshare_main_business": _status(ak_payload, ak_error),
            "akshare_concept_cons": _status(concept_payload, concept_error),
            "akshare_board_fund_flow": _status(fund_payload, fund_error),
            "akshare_cninfo_disclosure": _status(cninfo_payload, cninfo_error),
            "akshare_cninfo_profile": _status(profile_payload, profile_error),
            "baostock_daily": _status(bs_payload, bs_error),
            "efinance_quote_snapshot": _status(ef_quote_payload, ef_quote_error),
            "efinance_base_info": _status(ef_base_payload, ef_base_error),
            "adata_probe": _status(ad_payload, ad_error),
            "sec_submissions": _status(sec_payload, sec_error),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe industry-chain public-data adapters.")
    parser.add_argument("--probe-code", default="600276", help="A-share code used to probe adapters.")
    parser.add_argument("--history-start", default="2026-01-01", help="baostock probe start date (YYYY-MM-DD).")
    parser.add_argument("--history-end", default="2026-01-10", help="baostock probe end date (YYYY-MM-DD).")
    parser.add_argument("--output", help="Optional path to also write the JSON report.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = check(args.probe_code, args.history_start, args.history_end)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    sys.stdout.write(text + "\n")
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
