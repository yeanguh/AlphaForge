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
from loop_os.domain.state_update import apply_state_transition
from loop_os.report_router import route_cycle_reports
from loop_os.reporting import write_json, write_markdown_report, write_ops_report
from providers.open_source import a_stock_data, global_stock_data, investment_news, tradingagents_astock


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


def run_theme_deep_report(payload_file: Path | None = None) -> dict[str, Any]:
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
    if not isinstance(review, dict) or not review.get("roles") or review.get("agent_errors"):
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
            supplements[symbol] = a_stock_data.fetch_stock_supplement(symbol)
        except Exception as exc:
            supplements[symbol] = {"symbol": symbol, "errors": [repr(exc)]}
            errors.append(f"stock_supplement:{symbol}: {exc!r}")
    return supplements


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
    if agent_review.get("agent_errors"):
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
        theme_deep_report = run_theme_deep_report(cycle_dir / "result.json")
    payload["theme_deep_report"] = theme_deep_report
    if theme_deep_report.get("returncode") != 0:
        payload["errors"].append(f"theme_deep_report: {theme_deep_report}")
        payload["status"] = "error"
    write_cycle_artifacts(cycle_dir, payload)
    harness = run_harness()
    after_dirty = submodule_dirty_counts()
    if harness.get("status") != "ok" or any(v != 0 for v in after_dirty.values()):
        payload["status"] = "error"
    payload["harness"] = harness
    payload["submodule_dirty_after"] = after_dirty
    payload["finished_at"] = utc_now()
    publish_latest_artifacts(payload, cycle_dir)
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
