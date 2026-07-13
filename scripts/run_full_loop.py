from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from loop_os.domain.agent_review import build_review
from loop_os.domain.capability_chain import build_research_pipeline
from loop_os.domain.evidence_service import write_evidence
from loop_os.domain.industry_chain import analyze_industry_reports
from loop_os.domain.report_review_agent import build_report_review
from loop_os.domain.state_update import apply_state_transition
from loop_os.report_router import resolve_theme_key, route_cycle_reports
from loop_os.reporting import write_json, write_markdown_report, write_ops_report
from providers.open_source import a_stock_data, global_stock_data, investment_news, tradingagents_astock, vibe_research, vibe_trading


KNOWN_A_SHARE_SYMBOLS = {
    "兴森科技": "002436",
    "安集科技": "688019",
    "通富微电": "002156",
    "寒武纪": "688256",
    "深南电路": "002916",
    "中际旭创": "300308",
    "新易盛": "300502",
    "英维克": "002837",
    "沪电股份": "002463",
    "胜宏科技": "300476",
    "工业富联": "601138",
    "华特气体": "688268",
    "彤程新材": "603650",
    "绿的谐波": "688017",
    "双环传动": "002472",
    "中大力德": "002896",
    "秦川机床": "000837",
    "贝斯特": "300580",
    "五洲新春": "603667",
    "鸣志电器": "603728",
    "汇川技术": "300124",
    "雷赛智能": "002979",
    "禾川科技": "688320",
    "埃斯顿": "002747",
    "机器人": "300024",
    "华中数控": "300161",
    "华辰装备": "300809",
    "日发精机": "002520",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def submodule_dirty_counts() -> dict[str, int]:
    proc = subprocess.run(
        ["git", "submodule", "foreach", "--quiet", "printf '%s ' \"$name\"; git status --short | wc -l"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    counts: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                counts[parts[0]] = int(parts[-1])
            except ValueError:
                counts[parts[0]] = -1
    return counts


def run_harness() -> dict[str, Any]:
    proc = subprocess.run([sys.executable, "scripts/run_harness.py"], cwd=ROOT, text=True, capture_output=True, timeout=120)
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"status": "error", "stdout": proc.stdout, "stderr": proc.stderr}
    payload["returncode"] = proc.returncode
    return payload


def run_physical_ai_deep_report(payload_file: Path | None = None) -> dict[str, Any]:
    cmd = ["uv", "run", "python", "scripts/generate_physical_ai_chain_report.py"]
    if shutil.which("uv") is None:
        cmd = [sys.executable, "scripts/generate_physical_ai_chain_report.py"]
    if payload_file is not None:
        cmd.extend(["--payload-file", rel_path(payload_file)])
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"status": "error", "stdout": proc.stdout, "stderr": proc.stderr}
    payload["returncode"] = proc.returncode
    return payload


def run_generic_theme_deep_report(payload_file: Path | None = None) -> dict[str, Any]:
    cmd = [sys.executable, "scripts/generate_theme_deep_report.py"]
    if payload_file is not None:
        cmd.extend(["--payload-file", rel_path(payload_file)])
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=300,
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"status": "error", "stdout": proc.stdout, "stderr": proc.stderr}
    payload["returncode"] = proc.returncode
    return payload


def run_report_review_agent(payload: dict[str, Any], cycle_dir: Path, theme_key: str | None) -> dict[str, Any]:
    theme_report = ROOT / "reports" / "themes" / (theme_key or "uncategorized") / "report.md"
    deep_report = payload.get("theme_deep_report", {})
    draft_path = None
    if isinstance(deep_report, dict) and isinstance(deep_report.get("draft"), str):
        draft_path = ROOT / deep_report["draft"]
    return build_report_review(
        root=ROOT,
        payload=payload,
        theme_key=theme_key,
        report_path=theme_report,
        draft_path=draft_path,
        artifacts_dir=cycle_dir / "report-review",
    )


def run_final_report_review_agent(payload: dict[str, Any], cycle_dir: Path, theme_key: str | None) -> dict[str, Any]:
    theme_report = ROOT / "reports" / "themes" / (theme_key or "uncategorized") / "report.md"
    return build_report_review(
        root=ROOT,
        payload=payload,
        theme_key=theme_key,
        report_path=theme_report,
        draft_path=None,
        artifacts_dir=cycle_dir / "report-review-final",
    )


def selected_theme_key(payload: dict[str, Any]) -> str | None:
    pipeline = payload.get("research_pipeline", {})
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    chain = pipeline.get("selected_industry_chain", {})
    chain = chain if isinstance(chain, dict) else {}
    return resolve_theme_key(str(chain.get("selected_theme") or ""), ROOT)


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return data if isinstance(data, dict) else default


def rel_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def _has_items(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def _input_quality_issues(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("status") != "ok":
        issues.append(f"status={payload.get('status')}")
    if payload.get("errors"):
        issues.append("cycle_errors_present")
    if not _has_items(payload.get("a_share_quotes")):
        issues.append("missing_a_share_quotes")
    if not _has_items(payload.get("global_charts")):
        issues.append("missing_global_charts")
    news = payload.get("news", {})
    if not isinstance(news, dict) or not _has_items(news.get("headlines")):
        issues.append("missing_news_headlines")
    if not _has_items(payload.get("industry_reports")):
        issues.append("missing_industry_reports")
    pipeline = payload.get("research_pipeline", {})
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    if not pipeline.get("hotspot_scoring", {}).get("selected", {}).get("theme"):
        issues.append("missing_hotspot_selection")
    if not _has_items(pipeline.get("stock_analyzer")):
        issues.append("missing_stock_analyzer")
    if not pipeline.get("trade_decision_engine", {}).get("decisions"):
        issues.append("missing_trade_decisions")
    review = payload.get("agent_review", {})
    if not isinstance(review, dict) or not review.get("roles"):
        issues.append("agent_review_not_usable")
    return issues


def _latest_publish_issues(payload: dict[str, Any]) -> list[str]:
    issues = _input_quality_issues(payload)
    if not payload.get("evidence_ids"):
        issues.append("missing_evidence_ids")
    transition = payload.get("state_transition", {})
    if not isinstance(transition, dict) or not transition.get("validated") or not transition.get("committed"):
        issues.append("state_transition_not_committed")
    if payload.get("harness", {}).get("status") != "ok":
        issues.append("harness_not_ok")
    return issues


def write_cycle_artifacts(cycle_dir: Path, payload: dict[str, Any]) -> None:
    write_json(cycle_dir / "result.json", payload)
    write_markdown_report(cycle_dir / "report.md", payload)
    write_ops_report(cycle_dir / "ops-report.md", payload)


def cleanup_theme_drafts(root: Path, run_id: str) -> dict[str, Any]:
    """Remove per-cycle theme draft copies after a loop finishes.

    The durable audit copy stays under runs/<date>/<run_id>/cycle-*/. Theme
    draft files are only a handoff format for report curation and should not
    accumulate next to canonical reports.
    """
    themes_root = root / "reports" / "themes"
    if not themes_root.exists():
        return {"removed": 0, "files": []}
    patterns = [
        f"*/report.cycle-draft-{run_id}-cycle-*.md",
        f"*/drafts/{run_id}-cycle-*.md",
    ]
    removed: list[str] = []
    for pattern in patterns:
        for path in sorted(themes_root.glob(pattern)):
            if not path.is_file():
                continue
            try:
                rel = rel_path(path)
            except ValueError:
                rel = str(path)
            path.unlink()
            removed.append(rel)
    return {"removed": len(removed), "files": removed}


def publish_latest_artifacts(payload: dict[str, Any], cycle_dir: Path) -> bool:
    issues = _latest_publish_issues(payload)
    write_json(ROOT / "data" / "raw" / "latest-observed-full-loop.json", payload)
    # 内容类型路由:把本轮 loop 证据沉淀到对应最终报告(产业链/个股/周报),
    # 同时降级维护 daily 增量 inbox。失败轮次由 route_cycle_reports 内部拦截,只留在 runs/。
    curation = route_cycle_reports(
        root=ROOT,
        payload=payload,
        cycle_dir=cycle_dir,
        issues=issues,
    )
    payload["latest_publish"] = {
        "eligible": not issues,
        "issues": issues,
        "curation": curation,
        "checked_at": utc_now(),
    }
    if issues:
        return False
    write_json(ROOT / "data" / "raw" / "latest-full-loop.json", payload)
    write_ops_report(ROOT / "reports" / "daily" / "latest-ops.md", payload)
    return True


def fetch_stock_supplements(quotes: list[dict[str, Any]], errors: list[str]) -> dict[str, dict[str, Any]]:
    supplements: dict[str, dict[str, Any]] = {}
    for quote in quotes:
        symbol = str(quote.get("symbol") or "")
        if not symbol:
            continue
        try:
            supplements[symbol] = a_stock_data.fetch_stock_supplement_resilient(symbol)
        except Exception as exc:
            supplements[symbol] = {"symbol": symbol, "errors": [repr(exc)]}
            errors.append(f"stock_supplement:{symbol}: {exc!r}")
    return supplements


def candidate_symbols_from_pipeline(pipeline: dict[str, Any]) -> list[str]:
    chain = pipeline.get("selected_industry_chain", {}) if isinstance(pipeline, dict) else {}
    if not isinstance(chain, dict):
        return []
    candidates = chain.get("bottleneck_candidates", [])
    candidates = candidates if isinstance(candidates, list) else []
    symbols: list[str] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        companies = str(item.get("companies") or "")
        for raw_name in companies.replace("、", ",").replace("，", ",").split(","):
            name = raw_name.strip()
            symbol = KNOWN_A_SHARE_SYMBOLS.get(name)
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    return symbols


def merge_candidate_market_data(
    *,
    quotes: list[dict[str, Any]],
    stock_supplements: dict[str, dict[str, Any]],
    pipeline: dict[str, Any],
    errors: list[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Add selected bottleneck-company market data before evidence/state writes."""
    symbols = candidate_symbols_from_pipeline(pipeline)
    if not symbols:
        return quotes, stock_supplements
    by_symbol = {str(item.get("symbol")): item for item in quotes if isinstance(item, dict)}
    for symbol in symbols:
        if symbol not in by_symbol:
            try:
                quote = a_stock_data.fetch_quote(symbol)
                quotes.append(quote)
                by_symbol[symbol] = quote
            except Exception as exc:  # noqa: BLE001
                errors.append(f"candidate_quote:{symbol}: {exc!r}")
        if symbol not in stock_supplements:
            try:
                stock_supplements[symbol] = a_stock_data.fetch_stock_supplement_resilient(symbol)
            except Exception as exc:  # noqa: BLE001
                stock_supplements[symbol] = {"symbol": symbol, "errors": [repr(exc)]}
                errors.append(f"candidate_stock_supplement:{symbol}: {exc!r}")
    return quotes, stock_supplements


def build_committee_review(agent_review: dict[str, Any], trading_review: dict[str, Any]) -> dict[str, Any]:
    combined = dict(agent_review)
    combined["tradingagents_review"] = trading_review
    rating = trading_review.get("portfolio_rating")
    if rating == "Underweight":
        combined["decision"] = "hold_or_reject"
    elif rating == "Overweight" and combined.get("decision") == "watchlist_candidate":
        combined["decision"] = "watchlist_candidate"
    else:
        combined["decision"] = combined.get("decision") or "needs_more_evidence"
    return combined


def collect_provider_insights(payload_base: dict[str, Any], pipeline: dict[str, Any], trading_review: dict[str, Any]) -> dict[str, Any]:
    """Collect optional external-provider insights without blocking the cycle."""
    insights: dict[str, Any] = {}
    providers = (
        ("vibe_research", lambda: vibe_research.research_packet(payload_base, pipeline)),
        ("vibe_trading", lambda: vibe_trading.strategy_packet(payload_base, pipeline)),
        (
            "tradingagents_astock",
            lambda: {
                "provider": "TradingAgents-astock",
                "status": "ok" if not trading_review.get("error") else "warn",
                "source_submodule": "external/TradingAgents-astock",
                "adapter": "providers.open_source.tradingagents_astock.review_packet",
                "claims": [
                    f"TradingAgents-astock portfolio_rating={trading_review.get('portfolio_rating')}",
                    f"TradingAgents-astock trader_action={trading_review.get('trader_action')}",
                    f"TradingAgents-astock schema_contract={trading_review.get('schema_contract')}",
                ],
                "review": trading_review,
                "errors": [trading_review.get("error")] if trading_review.get("error") else [],
                "state_mutation_allowed": False,
            },
        ),
    )
    for key, factory in providers:
        try:
            packet = factory()
            if not isinstance(packet, dict):
                packet = {"provider": key, "status": "warn", "errors": ["adapter returned non-dict packet"]}
        except Exception as exc:  # noqa: BLE001
            packet = {
                "provider": key,
                "status": "warn",
                "errors": [repr(exc)],
                "state_mutation_allowed": False,
            }
        insights[key] = packet
    return {
        "stage": "external-provider-insights",
        "status": "ok" if all(item.get("status") == "ok" for item in insights.values() if isinstance(item, dict)) else "warn",
        "providers": insights,
        "blocking": False,
        "generated_at": utc_now(),
    }


def write_supervisor_health(
    *,
    run_id: str,
    cycle: int,
    mode: str,
    status: str,
    consecutive_errors: int,
    run_dir: Path,
    next_wake_at: str | None = None,
    last_error: str | None = None,
) -> None:
    path = ROOT / "state" / "system-health.json"
    health = read_json(path, {"schema_version": "1.0"})
    now = utc_now()
    health["updated_at"] = now
    health["supervisor"] = {
        "mode": mode,
        "status": status,
        "run_id": run_id,
        "current_cycle": cycle,
        "last_heartbeat_at": now,
        "consecutive_errors": consecutive_errors,
        "next_wake_at": next_wake_at,
        "last_error": last_error,
        "run_dir": rel_path(run_dir),
    }
    write_json(path, health)


def build_cycle_exception_payload(cycle: int, run_dir: Path, exc: Exception) -> dict[str, Any]:
    now = utc_now()
    return {
        "cycle": cycle,
        "status": "error",
        "run_id": run_dir.name,
        "started_at": now,
        "finished_at": now,
        "errors": [f"cycle_exception: {exc!r}"],
        "a_share_quotes": [],
        "global_charts": [],
        "news": {"source_count": 0, "headlines": [], "errors": [repr(exc)], "generated_at": now},
        "industry_reports": [],
        "industry_analysis": {},
        "agent_review": {},
        "harness": None,
        "evidence_ids": [],
        "state_transition": None,
        "submodule_dirty_before": submodule_dirty_counts(),
        "submodule_dirty_after": submodule_dirty_counts(),
    }


def run_cycle(cycle: int, run_dir: Path, *, agent_mode: str, agent_timeout_seconds: int) -> dict[str, Any]:
    started = utc_now()
    run_id = run_dir.name
    cycle_dir = run_dir / f"cycle-{cycle:03d}"
    before_dirty = submodule_dirty_counts()
    errors: list[str] = []

    try:
        quotes = a_stock_data.fetch_quotes()
    except Exception as exc:
        quotes = []
        errors.append(f"a_share_quotes: {exc!r}")

    try:
        global_charts = global_stock_data.fetch_charts()
    except Exception as exc:
        global_charts = []
        errors.append(f"global_charts: {exc!r}")

    try:
        news = investment_news.fetch_headlines(max_sources=24, max_items=24)
    except Exception as exc:
        news = {"source_count": 0, "headlines": [], "errors": [repr(exc)], "generated_at": utc_now()}
        errors.append(f"investment_news: {exc!r}")

    try:
        industry_reports = a_stock_data.fetch_industry_reports(max_pages=1)
    except Exception as exc:
        industry_reports = []
        errors.append(f"industry_reports: {exc!r}")

    industry_analysis = analyze_industry_reports(industry_reports, news.get("headlines", []))
    stock_supplements = fetch_stock_supplements(quotes, errors)
    portfolio_state = read_json(ROOT / "state" / "paper-portfolio.json", {"cash": 1_000_000.0, "positions": [], "reviews": []})
    payload_base = {
        "a_share_quotes": quotes,
        "global_charts": global_charts,
        "news": news,
        "industry_reports": industry_reports[:20],
        "industry_analysis": industry_analysis,
        "stock_supplements": stock_supplements,
        "enable_skill_health_check": True,
    }
    preliminary_pipeline = build_research_pipeline(ROOT, payload_base, stock_supplements, portfolio_state, {})
    quotes, stock_supplements = merge_candidate_market_data(
        quotes=quotes,
        stock_supplements=stock_supplements,
        pipeline=preliminary_pipeline,
        errors=errors,
    )
    payload_base = {
        "a_share_quotes": quotes,
        "global_charts": global_charts,
        "news": news,
        "industry_reports": industry_reports[:20],
        "industry_analysis": industry_analysis,
        "stock_supplements": stock_supplements,
        "enable_skill_health_check": True,
    }
    preliminary_pipeline = build_research_pipeline(ROOT, payload_base, stock_supplements, portfolio_state, {})
    review_input = {
        "a_share_quotes": quotes,
        "global_charts": global_charts,
        "news": news,
        "industry_reports": industry_reports,
        "industry_analysis": industry_analysis,
        "research_pipeline": preliminary_pipeline,
    }
    agent_review = build_review(
        review_input,
        mode=agent_mode,
        root=ROOT,
        artifacts_dir=cycle_dir / "agent-review",
        timeout_seconds=agent_timeout_seconds,
    )
    if agent_review.get("agent_errors") and agent_review.get("agent_provider") != "deterministic_fallback":
        errors.extend(f"agent_review:{item}" for item in agent_review["agent_errors"])
    pipeline_after_agent = build_research_pipeline(ROOT, payload_base, stock_supplements, portfolio_state, agent_review)
    try:
        tradingagents_review = tradingagents_astock.review_packet(pipeline_after_agent)
    except Exception as exc:
        tradingagents_review = {
            "review_type": "tradingagents_astock",
            "provider": "TradingAgents-astock",
            "error": repr(exc),
            "portfolio_rating": "Hold",
            "trader_action": "Hold",
            "state_mutation_allowed": False,
        }
        errors.append(f"tradingagents_astock: {exc!r}")
    committee_review = build_committee_review(agent_review, tradingagents_review)
    research_pipeline = build_research_pipeline(ROOT, payload_base, stock_supplements, portfolio_state, committee_review)
    research_pipeline["tradingagents_review"] = tradingagents_review
    provider_insights = collect_provider_insights(payload_base, research_pipeline, tradingagents_review)
    research_pipeline["provider_insights"] = provider_insights
    payload = {
        "cycle": cycle,
        "status": "ok" if not errors else "error",
        "run_id": run_id,
        "agent_mode": agent_mode,
        "started_at": started,
        "finished_at": utc_now(),
        "errors": errors,
        "a_share_quotes": quotes,
        "global_charts": global_charts,
        "news": news,
        "industry_reports": industry_reports[:20],
        "industry_analysis": industry_analysis,
        "stock_supplements": stock_supplements,
        "research_pipeline": research_pipeline,
        "provider_insights": provider_insights,
        "tradingagents_review": tradingagents_review,
        "agent_review": agent_review,
        "committee_review": committee_review,
        "harness": None,
        "submodule_dirty_before": before_dirty,
        "submodule_dirty_after": None,
    }
    input_quality_issues = _input_quality_issues(payload)
    if input_quality_issues:
        evidence_ids = []
        state_transition = {
            "validated": False,
            "committed": False,
            "reason": "cycle input quality gate failed; state update skipped",
            "issues": input_quality_issues,
        }
    else:
        evidence_ids = write_evidence(ROOT, cycle, payload)
        state_transition = apply_state_transition(ROOT, run_id, cycle, payload, evidence_ids)
    payload["evidence_ids"] = evidence_ids
    payload["state_transition"] = state_transition
    payload["finished_at"] = utc_now()
    write_cycle_artifacts(cycle_dir, payload)
    theme_report_input_issues = _input_quality_issues(payload)
    if theme_report_input_issues:
        theme_deep_report = {
            "status": "skipped",
            "returncode": 0,
            "reason": "cycle input quality gate failed; preserving previous canonical theme report",
            "issues": theme_report_input_issues,
        }
    else:
        theme_key = selected_theme_key(payload)
        if theme_key == "physical-ai":
            theme_deep_report = run_physical_ai_deep_report(cycle_dir / "result.json")
        else:
            theme_deep_report = run_generic_theme_deep_report(cycle_dir / "result.json")
    payload["theme_deep_report"] = theme_deep_report
    if theme_deep_report.get("returncode") != 0:
        payload["errors"].append(f"theme_deep_report: {theme_deep_report}")
        payload["status"] = "error"
    if theme_deep_report.get("status") != "skipped":
        try:
            payload["report_review_agent"] = run_report_review_agent(payload, cycle_dir, selected_theme_key(payload))
        except Exception as exc:  # noqa: BLE001
            payload["report_review_agent"] = {
                "review_type": "architecture_aware_report_review",
                "agent_provider": "deterministic_report_review_agent",
                "status": "error",
                "error": repr(exc),
                "state_mutation_allowed": False,
            }
    write_cycle_artifacts(cycle_dir, payload)
    harness = run_harness()
    after_dirty = submodule_dirty_counts()
    if harness.get("status") != "ok" or any(v != 0 for v in after_dirty.values()):
        payload["status"] = "error"
    payload["harness"] = harness
    payload["submodule_dirty_after"] = after_dirty
    payload["finished_at"] = utc_now()
    publish_latest_artifacts(payload, cycle_dir)
    if theme_deep_report.get("status") != "skipped":
        try:
            payload["final_report_review_agent"] = run_final_report_review_agent(payload, cycle_dir, selected_theme_key(payload))
        except Exception as exc:  # noqa: BLE001
            payload["final_report_review_agent"] = {
                "review_type": "architecture_aware_report_review",
                "agent_provider": "deterministic_report_review_agent",
                "status": "error",
                "error": repr(exc),
                "state_mutation_allowed": False,
            }
    write_cycle_artifacts(cycle_dir, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-seconds", type=int, default=3600)
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--min-cycles", type=int, default=1)
    parser.add_argument("--forever", action="store_true", help="run continuously until interrupted")
    parser.add_argument("--max-cycles", type=int, default=None, help="optional cap, useful for daemon smoke tests")
    parser.add_argument("--continue-on-error", action="store_true", help="continue after a failed cycle with backoff")
    parser.add_argument("--error-backoff-seconds", type=int, default=60)
    parser.add_argument("--agent-mode", choices=["deterministic", "codex", "claude", "openai_compatible", "auto"], default="deterministic")
    parser.add_argument("--agent-timeout-seconds", type=int, default=180)
    parser.add_argument("--keep-theme-drafts", action="store_true", help="keep reports/themes/* cycle draft copies for debugging")
    args = parser.parse_args()

    run_dir = ROOT / "runs" / datetime.now().strftime("%Y-%m-%d") / f"full-loop-{datetime.now().strftime('%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    deadline = None if args.forever else time.monotonic() + args.duration_seconds
    cycle = 0
    mode = "forever" if args.forever else "bounded"
    keep_going_on_error = args.continue_on_error or args.forever
    consecutive_errors = 0
    summary: dict[str, Any] = {
        "status": "running",
        "mode": mode,
        "run_dir": rel_path(run_dir),
        "cycles": [],
        "continue_on_error": keep_going_on_error,
    }
    print(f"[full-loop] run_dir={rel_path(run_dir)}", flush=True)
    if args.forever:
        print(f"[full-loop] mode=forever interval={args.interval_seconds}s", flush=True)
    else:
        print(f"[full-loop] duration={args.duration_seconds}s interval={args.interval_seconds}s", flush=True)
    write_supervisor_health(
        run_id=run_dir.name,
        cycle=cycle,
        mode=mode,
        status="running",
        consecutive_errors=consecutive_errors,
        run_dir=run_dir,
    )

    interrupted = False
    while True:
        if args.max_cycles is not None and cycle >= args.max_cycles:
            break
        if cycle >= args.min_cycles and deadline is not None and time.monotonic() >= deadline:
            break
        cycle += 1
        cycle_started = time.monotonic()
        write_supervisor_health(
            run_id=run_dir.name,
            cycle=cycle,
            mode=mode,
            status="cycle_running",
            consecutive_errors=consecutive_errors,
            run_dir=run_dir,
        )
        try:
            payload = run_cycle(
                cycle,
                run_dir,
                agent_mode=args.agent_mode,
                agent_timeout_seconds=args.agent_timeout_seconds,
            )
        except KeyboardInterrupt:
            interrupted = True
            break
        except Exception as exc:
            payload = build_cycle_exception_payload(cycle, run_dir, exc)
            cycle_dir = run_dir / f"cycle-{cycle:03d}"
            write_json(cycle_dir / "result.json", payload)
            write_markdown_report(cycle_dir / "report.md", payload)
        summary["cycles"].append(
            {
                "cycle": cycle,
                "status": payload["status"],
                "errors": payload["errors"],
                "report": rel_path(run_dir / f"cycle-{cycle:03d}" / "report.md"),
            }
        )
        write_json(run_dir / "summary.json", summary)
        if payload["status"] == "ok":
            consecutive_errors = 0
        else:
            consecutive_errors += 1
        print(
            f"[full-loop] cycle={cycle} status={payload['status']} "
            f"errors={len(payload['errors'])} report={rel_path(run_dir / f'cycle-{cycle:03d}' / 'report.md')}",
            flush=True,
        )
        if payload["status"] != "ok" and not keep_going_on_error:
            break
        if args.max_cycles is not None and cycle >= args.max_cycles:
            break
        remaining = None if deadline is None else deadline - time.monotonic()
        if cycle >= args.min_cycles and remaining is not None and remaining <= 0:
            break
        base_sleep = args.error_backoff_seconds if payload["status"] != "ok" else args.interval_seconds
        sleep_for = min(
            base_sleep,
            max(0, remaining) if remaining is not None else base_sleep,
            max(0, base_sleep - (time.monotonic() - cycle_started)),
        )
        next_wake_at = None
        if sleep_for > 0:
            next_wake_at = datetime.fromtimestamp(time.time() + sleep_for, tz=timezone.utc).isoformat()
            write_supervisor_health(
                run_id=run_dir.name,
                cycle=cycle,
                mode=mode,
                status="sleeping",
                consecutive_errors=consecutive_errors,
                run_dir=run_dir,
                next_wake_at=next_wake_at,
                last_error="; ".join(payload.get("errors", [])) if payload["status"] != "ok" else None,
            )
            time.sleep(sleep_for)

    if interrupted:
        summary["status"] = "interrupted"
    elif summary["cycles"] and all(c["status"] == "ok" for c in summary["cycles"]):
        summary["status"] = "ok"
    elif keep_going_on_error and summary["cycles"]:
        summary["status"] = "degraded"
    else:
        summary["status"] = "error"
    summary["finished_at"] = utc_now()
    summary["consecutive_errors"] = consecutive_errors
    if args.keep_theme_drafts:
        summary["theme_draft_cleanup"] = {"skipped": True, "reason": "--keep-theme-drafts"}
    else:
        summary["theme_draft_cleanup"] = cleanup_theme_drafts(ROOT, run_dir.name)
    write_json(run_dir / "summary.json", summary)
    write_supervisor_health(
        run_id=run_dir.name,
        cycle=cycle,
        mode=mode,
        status=summary["status"],
        consecutive_errors=consecutive_errors,
        run_dir=run_dir,
        last_error="interrupted" if interrupted else None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    raise SystemExit(0 if summary["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
