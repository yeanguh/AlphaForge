from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_os.domain.report_review_agent import build_report_review  # noqa: E402
from loop_os.report_router import route_cycle_reports  # noqa: E402
from scripts import generate_theme_deep_report as generic_report  # noqa: E402
from scripts.run_full_loop import cleanup_theme_drafts, rel_path  # noqa: E402


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def theme_keys() -> list[str]:
    pool = read_json(ROOT / "config" / "theme_pool.json")
    themes = pool.get("themes", {}) if isinstance(pool.get("themes"), dict) else {}
    return [str(key) for key in themes.keys()]


def cleanup_paths(paths: list[str]) -> dict[str, Any]:
    removed: list[str] = []
    for raw in paths:
        if not raw:
            continue
        path = ROOT / raw
        try:
            resolved = path.resolve()
        except Exception:
            continue
        if not resolved.is_file() or ROOT.resolve() not in resolved.parents:
            continue
        if "reports/themes" not in str(resolved) or resolved.name == "report.md":
            continue
        resolved.unlink()
        try:
            removed.append(rel_path(resolved))
        except ValueError:
            removed.append(str(resolved))
    return {"removed": len(removed), "files": removed}


def payload_for_theme(base_payload: dict[str, Any], theme_key: str, *, run_id: str, cycle: int) -> dict[str, Any]:
    payload = copy.deepcopy(base_payload)
    payload["run_id"] = run_id
    payload["cycle"] = cycle
    payload.setdefault("status", "ok")
    payload.setdefault("errors", [])
    pipeline = payload.setdefault("research_pipeline", {})
    if not isinstance(pipeline, dict):
        pipeline = {}
        payload["research_pipeline"] = pipeline
    selected = pipeline.setdefault("selected_industry_chain", {})
    if not isinstance(selected, dict):
        selected = {}
        pipeline["selected_industry_chain"] = selected
    selected["selected_theme"] = theme_key
    selected.setdefault("score", 0)
    selected.setdefault("stage", "theme-pool-full-scan")
    return payload


def generate_generic_theme(payload: dict[str, Any], payload_file: Path, theme_key: str) -> dict[str, Any]:
    out_dir = ROOT / "reports" / "themes" / theme_key
    report = generic_report.build_report(payload, theme_key, out_dir)
    canonical_path, draft_path, seeded = generic_report.write_theme_outputs(report, payload_file, theme_key)
    quality = generic_report.quality(report)
    agent_report_path = out_dir / "agent_report.md"
    agent_report_path.write_text(generic_report.build_agent_report(report, payload, theme_key, payload_file, quality), encoding="utf-8")
    source_data = {
        "generated_at": datetime.now().isoformat(),
        "payload_file": rel_path(payload_file),
        "theme_key": theme_key,
        "selected_theme": theme_key,
        "evidence_ids": payload.get("evidence_ids", []),
        "quality": quality,
    }
    (out_dir / "source_data.json").write_text(json.dumps(source_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report": rel_path(canonical_path),
        "agent_report": rel_path(agent_report_path),
        "draft": rel_path(draft_path),
        "draft_archive": rel_path(draft_path.parent / "drafts" / (draft_path.name.removeprefix("report.cycle-draft-"))),
        "theme_key": theme_key,
        "seeded_canonical": seeded,
        "quality": quality,
        "returncode": 0 if quality.get("passed") else 1,
    }


def generate_physical_theme(payload_file: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "scripts/generate_physical_ai_chain_report.py", "--payload-file", rel_path(payload_file)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=240,
    )
    try:
        result = json.loads(proc.stdout)
    except Exception:
        result = {"status": "error", "stdout": proc.stdout, "stderr": proc.stderr}
    result["returncode"] = proc.returncode
    return result


def run_theme(theme_key: str, base_payload: dict[str, Any], cycle_dir: Path, *, cycle: int, run_id: str) -> dict[str, Any]:
    theme_dir = cycle_dir / "themes" / theme_key
    payload = payload_for_theme(base_payload, theme_key, run_id=run_id, cycle=cycle)
    payload_file = theme_dir / "result.json"
    write_json(payload_file, payload)

    if theme_key == "physical-ai":
        deep_report = generate_physical_theme(payload_file)
    else:
        deep_report = generate_generic_theme(payload, payload_file, theme_key)
    payload["theme_deep_report"] = deep_report
    write_json(payload_file, payload)
    agent_report_path = ROOT / "reports" / "themes" / theme_key / "agent_report.md"
    agent_report_path.write_text(
        generic_report.build_agent_report("", payload, theme_key, payload_file, deep_report.get("quality", {}) if isinstance(deep_report, dict) else {}),
        encoding="utf-8",
    )

    draft_path = ROOT / str(deep_report.get("draft", ""))
    review = build_report_review(
        root=ROOT,
        payload=payload,
        theme_key=theme_key,
        report_path=ROOT / "reports" / "themes" / theme_key / "report.md",
        draft_path=draft_path if draft_path.exists() else None,
        artifacts_dir=theme_dir / "report-review",
    )
    payload["report_review_agent"] = review

    routing = route_cycle_reports(root=ROOT, payload=payload, cycle_dir=theme_dir, issues=[])
    payload["latest_publish"] = {"eligible": True, "issues": [], "curation": routing, "checked_at": datetime.now().isoformat()}

    final_review = build_report_review(
        root=ROOT,
        payload=payload,
        theme_key=theme_key,
        report_path=ROOT / "reports" / "themes" / theme_key / "report.md",
        draft_path=None,
        artifacts_dir=theme_dir / "report-review-final",
    )
    payload["final_report_review_agent"] = final_review
    write_json(payload_file, payload)
    return {
        "theme_key": theme_key,
        "deep_report": deep_report,
        "review_status": review.get("status"),
        "final_review_status": final_review.get("status"),
        "final_review_summary": final_review.get("summary"),
        "routing": routing.get("routed", [{}])[0] if isinstance(routing.get("routed"), list) and routing.get("routed") else {},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-file", default="data/raw/latest-full-loop.json")
    parser.add_argument("--themes", default="", help="Comma-separated theme keys. Default: all config/theme_pool.json themes.")
    parser.add_argument("--keep-theme-drafts", action="store_true")
    args = parser.parse_args()

    payload_file = ROOT / args.payload_file
    base_payload = read_json(payload_file)
    keys = [x.strip() for x in args.themes.split(",") if x.strip()] if args.themes else theme_keys()
    run_dir = ROOT / "runs" / datetime.now().strftime("%Y-%m-%d") / f"theme-pool-{datetime.now().strftime('%H%M%S')}"
    cycle_dir = run_dir / "cycle-001"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_dir.name
    results = [run_theme(key, base_payload, cycle_dir, cycle=1, run_id=run_id) for key in keys]
    if args.keep_theme_drafts:
        cleanup = {"skipped": True, "reason": "--keep-theme-drafts"}
    else:
        cleanup = cleanup_theme_drafts(ROOT, run_id)
        explicit_cleanup = cleanup_paths(
            [
                str(path)
                for result in results
                for path in (
                    result.get("deep_report", {}).get("draft") if isinstance(result.get("deep_report"), dict) else "",
                    result.get("deep_report", {}).get("draft_archive") if isinstance(result.get("deep_report"), dict) else "",
                )
                if path
            ]
        )
        cleanup = {
            "removed": int(cleanup.get("removed", 0)) + int(explicit_cleanup.get("removed", 0)),
            "files": [*cleanup.get("files", []), *explicit_cleanup.get("files", [])],
        }
    summary = {
        "status": "ok" if all(r.get("final_review_status") == "pass" for r in results) else "needs_improvement",
        "run_dir": rel_path(run_dir),
        "theme_count": len(keys),
        "themes": results,
        "theme_draft_cleanup": cleanup,
        "finished_at": datetime.now().isoformat(),
    }
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if summary["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
