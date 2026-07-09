from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from loop_os.schemas.state import REQUIRED_STATE_FILES, load_state_file


ROOT = Path(__file__).resolve().parents[2]


EXPECTED_SUBMODULES = {
    "external/investment-news",
    "external/TradingAgents-astock",
    "external/Vibe-Research",
    "external/Vibe-Trading",
    "skills/a-stock-data",
    "skills/global-stock-data",
}

EXPECTED_RETAINED_SKILL_FILES = {
    "skills/industry-chain-analysis/SKILL.md",
}

EXPECTED_PROVIDER_SKILL_FILES = {
    "skills/a-stock-data/SKILL.md",
    "skills/global-stock-data/SKILL.md",
}


def check_state_files() -> list[dict[str, Any]]:
    results = []
    for name in REQUIRED_STATE_FILES:
        path = ROOT / "state" / name
        try:
            load_state_file(path)
            results.append({"check": f"state:{name}", "status": "ok"})
        except Exception as exc:
            results.append({"check": f"state:{name}", "status": "error", "error": repr(exc)})
    return results


def check_submodules() -> list[dict[str, Any]]:
    results = []
    gitmodules = ROOT / ".gitmodules"
    locks = ROOT / "external" / "LOCKS.md"
    if not gitmodules.exists():
        results.append({"check": ".gitmodules", "status": "error", "error": "missing"})
        return results
    text = gitmodules.read_text(encoding="utf-8")
    lock_text = locks.read_text(encoding="utf-8") if locks.exists() else ""
    for rel in sorted(EXPECTED_SUBMODULES):
        path = ROOT / rel
        ok = path.exists() and (path / ".git").exists() and rel in text and rel in lock_text
        results.append({"check": f"submodule:{rel}", "status": "ok" if ok else "error"})
    return results


def check_no_core_external_imports() -> list[dict[str, Any]]:
    offenders: list[str] = []
    direct_import_pattern = re.compile(r"^\s*(from\s+external\b|import\s+external\b)", re.MULTILINE)
    for path in (ROOT / "loop_os").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if direct_import_pattern.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    return [{"check": "core:no_external_imports", "status": "ok" if not offenders else "error", "offenders": offenders}]


def _check_skill_files(kind: str, files: set[str]) -> list[dict[str, Any]]:
    results = []
    for rel in sorted(files):
        path = ROOT / rel
        ok = path.exists() and path.read_text(encoding="utf-8").strip()
        results.append({"check": f"{kind}_skill_file:{rel}", "status": "ok" if ok else "error"})
    return results


def check_retained_skill_files() -> list[dict[str, Any]]:
    return _check_skill_files("retained", EXPECTED_RETAINED_SKILL_FILES)


def check_provider_skill_files() -> list[dict[str, Any]]:
    results = _check_skill_files("provider", EXPECTED_PROVIDER_SKILL_FILES)
    wen_cai_files = sorted((ROOT / "skills").glob("wen-cai*/SKILL.md"))
    ok = bool(wen_cai_files) and all(path.read_text(encoding="utf-8").strip() for path in wen_cai_files)
    results.append({"check": "provider_skill_file:skills/wen-cai*/SKILL.md", "status": "ok" if ok else "warn"})
    return results


def check_retained_skills() -> list[dict[str, Any]]:
    return check_retained_skill_files()


def check_loop_state_invariants() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    try:
        research_state = load_state_file(ROOT / "state" / "research-state.json")
        catalysts_state = load_state_file(ROOT / "state" / "catalysts.json")
        watchlist_state = load_state_file(ROOT / "state" / "watchlist.json")
        portfolio_state = load_state_file(ROOT / "state" / "paper-portfolio.json")
        health_state = load_state_file(ROOT / "state" / "system-health.json")
        full_loop = research_state.get("loops", {}).get("full_loop")
        supervisor = health_state.get("supervisor", {})
        results.append({"check": "loop_state:full_loop_present", "status": "ok" if full_loop else "warn"})
        results.append({"check": "loop_state:catalysts_array", "status": "ok" if isinstance(catalysts_state.get("catalysts"), list) else "error"})
        results.append({"check": "loop_state:watchlist_array", "status": "ok" if isinstance(watchlist_state.get("watchlist"), list) else "error"})
        results.append({"check": "loop_state:portfolio_reviews", "status": "ok" if isinstance(portfolio_state.get("reviews", []), list) else "error"})
        cash = portfolio_state.get("cash")
        results.append({"check": "loop_state:paper_cash_numeric", "status": "ok" if cash is None or isinstance(cash, int | float) else "error"})
        if supervisor:
            results.append({"check": "supervisor:heartbeat", "status": "ok" if supervisor.get("last_heartbeat_at") else "error"})
            results.append({"check": "supervisor:run_dir", "status": "ok" if supervisor.get("run_dir") else "error"})
        else:
            results.append({"check": "supervisor:heartbeat", "status": "warn"})
    except Exception as exc:
        results.append({"check": "loop_state:load", "status": "error", "error": repr(exc)})

    evidence_root = ROOT / "evidence"
    evidence_indexes = list(evidence_root.glob("*/raw-index.json")) if evidence_root.exists() else []
    results.append({"check": "evidence:index_present", "status": "ok" if evidence_indexes else "warn"})
    return results


def check_latest_loop_artifact() -> list[dict[str, Any]]:
    path = ROOT / "data" / "raw" / "latest-full-loop.json"
    if not path.exists():
        return [{"check": "latest_loop:artifact", "status": "warn"}]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [{"check": "latest_loop:artifact", "status": "error", "error": repr(exc)}]
    review = payload.get("agent_review", {})
    pipeline = payload.get("research_pipeline", {})
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    chain = pipeline.get("selected_industry_chain", {})
    report_path = ROOT / "reports" / "daily" / "latest-full-loop.md"
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    supplements = payload.get("stock_supplements", {})
    required_supplement_keys = {"fundamental", "announcements", "fund_flow", "dragon_tiger", "financials", "research_reports"}
    supplement_key_ok = bool(supplements) and all(
        required_supplement_keys.issubset(set(item.keys())) for item in supplements.values() if isinstance(item, dict)
    )
    supplement_data_ok = bool(supplements) and all(
        isinstance(item, dict)
        and isinstance(item.get("announcements"), dict)
        and isinstance(item.get("financials"), dict)
        and isinstance(item.get("research_reports"), dict)
        for item in supplements.values()
    )
    forbidden_report_terms = [
        "/Users/",
        "ev-",
        "data/raw/",
        "a-stock-data",
        "决策门禁",
        "补充覆盖",
        "coverage",
        "TradingAgents",
        "Underweight",
        "综合复核",
        "payload",
        "明天",
    ]
    checks = [
        {"check": "latest_loop:artifact", "status": "ok"},
        {"check": "latest_loop:agent_review_present", "status": "ok" if isinstance(review, dict) and review.get("roles") else "error"},
        {"check": "latest_loop:agent_provider_present", "status": "ok" if review.get("agent_provider") else "warn"},
        {"check": "latest_loop:evidence_ids", "status": "ok" if payload.get("evidence_ids") else "error"},
        {"check": "latest_loop:state_transition", "status": "ok" if payload.get("state_transition") else "error"},
        {"check": "latest_loop:news_scanner", "status": "ok" if pipeline.get("news_scanner", {}).get("item_count", 0) > 0 else "error"},
        {"check": "latest_loop:article_reader", "status": "ok" if pipeline.get("article_reader", {}).get("digest_count", 0) > 0 else "error"},
        {"check": "latest_loop:hotspot_selected", "status": "ok" if pipeline.get("hotspot_scoring", {}).get("selected", {}).get("theme") else "error"},
        {"check": "latest_loop:industry_chain_skill", "status": "ok" if chain.get("skill_manifest", {}).get("files_used") else "error"},
        {"check": "latest_loop:industry_chain_methodology", "status": "ok" if chain.get("methodology_applied") and chain.get("upstream_material_discovery") and chain.get("core_value_distribution") and chain.get("company_mapping") else "error"},
        {"check": "latest_loop:industry_chain_health_check", "status": "ok" if chain.get("skill_health_check", {}).get("status") in {"ok", "skipped"} else "error"},
        {"check": "latest_loop:stock_analyzer", "status": "ok" if pipeline.get("stock_analyzer") else "error"},
        {"check": "latest_loop:stock_supplements", "status": "ok" if payload.get("stock_supplements") else "error"},
        {"check": "latest_loop:a_stock_data_required_keys", "status": "ok" if supplement_key_ok else "error"},
        {"check": "latest_loop:a_stock_data_required_sections", "status": "ok" if supplement_data_ok else "error"},
        {"check": "latest_loop:tradingagents_review", "status": "ok" if payload.get("tradingagents_review", {}).get("portfolio_rating") else "error"},
        {"check": "latest_loop:trade_decision_engine", "status": "ok" if pipeline.get("trade_decision_engine", {}).get("decisions") else "error"},
        {"check": "latest_loop:portfolio_analytics", "status": "ok" if pipeline.get("portfolio_analytics") else "error"},
        {
            "check": "latest_report:no_internal_refs",
            "status": "ok" if report_text and not any(term in report_text for term in forbidden_report_terms) else "error",
        },
    ]
    if review.get("agent_provider") in {"codex", "claude"}:
        checks.append({"check": "latest_loop:llm_agent_review", "status": "ok"})
    else:
        checks.append({"check": "latest_loop:llm_agent_review", "status": "warn", "provider": review.get("agent_provider")})
    return checks


def check_industry_analysis_report() -> list[dict[str, Any]]:
    root = ROOT / "reports" / "industry"
    dirs = sorted(root.glob("physical-ai-chain-analysis-*")) if root.exists() else []
    if not dirs:
        return [{"check": "industry_report:artifact", "status": "error", "error": "missing reports/industry/physical-ai-chain-analysis report"}]
    report_dir = dirs[-1]
    report = report_dir / "report.md"
    quality_path = report_dir / "quality_report.json"
    source_path = report_dir / "source_data.json"
    assets_dir = report_dir / "assets"
    checks: list[dict[str, Any]] = [
        {"check": "industry_report:artifact", "status": "ok" if report.exists() else "error", "path": str(report.relative_to(ROOT))},
        {"check": "industry_report:source_data", "status": "ok" if source_path.exists() else "error"},
        {"check": "industry_report:assets", "status": "ok" if assets_dir.exists() and any(assets_dir.glob("*.png")) else "error"},
    ]
    try:
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
    except Exception as exc:
        checks.append({"check": "industry_report:quality", "status": "error", "error": repr(exc)})
        return checks
    checks.append({"check": "industry_report:quality", "status": "ok" if quality.get("passed") is True else "error", "score": quality.get("score"), "total": quality.get("total")})
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    required_terms = ["核心结论", "产业链全景图谱", "A股公司映射", "买点区间", "目标价/空间", "数据来源"]
    checks.append(
        {
            "check": "industry_report:deep_report_terms",
            "status": "ok" if all(term in text for term in required_terms) else "error",
        }
    )
    return checks


def run_provider_smoke(live: bool = False) -> dict[str, Any]:
    cmd = [sys.executable, "scripts/run_provider_smoke.py"]
    if live:
        cmd.append("--live")
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"status": "error", "stdout": proc.stdout, "stderr": proc.stderr}
    payload["returncode"] = proc.returncode
    return payload


def run_all(live: bool = False) -> dict[str, Any]:
    checks = []
    checks.extend(check_state_files())
    checks.extend(check_submodules())
    checks.extend(check_retained_skill_files())
    checks.extend(check_provider_skill_files())
    checks.extend(check_loop_state_invariants())
    checks.extend(check_latest_loop_artifact())
    checks.extend(check_industry_analysis_report())
    checks.extend(check_no_core_external_imports())
    provider_payload = run_provider_smoke(live=live)
    provider_ok = provider_payload.get("status") == "ok" and provider_payload.get("returncode") == 0
    checks.append({"check": "providers:smoke", "status": "ok" if provider_ok else "error", "details": provider_payload})
    status = "ok" if all(item.get("status") in {"ok", "warn"} for item in checks) else "error"
    return {"status": status, "checks": checks}
