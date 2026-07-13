from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from loop_os.domain.report_review_agent import review_report_text
from loop_os.schemas.state import REQUIRED_STATE_FILES, load_state_file


ROOT = Path(__file__).resolve().parents[2]


# Report/harness policy is externalized to config/report_policy.json so themes and
# forbidden terms can change without editing code. Hardcoded fallbacks preserve
# backward compatibility if the config file is missing or malformed.
_DEFAULT_INDUSTRY_DIR_GLOB = "physical-ai-chain-analysis-*"
_DEFAULT_INDUSTRY_REQUIRED_TERMS = [
    "核心结论",
    "产业链全景图谱",
    "A股公司映射",
    "买点区间",
    "目标价/空间",
    "数据来源",
]
_DEFAULT_FORBIDDEN_REPORT_TERMS = [
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

# 方案 A: reports/themes/* 是持续沉淀的 canonical final reports, 门禁必须存在的主题键。
_DEFAULT_THEME_CANONICAL_REQUIRED = ["physical-ai"]
FINAL_REPORT_OPERATIONAL_MARKERS = [
    "## 附录 · Loop 证据增量日志",
    "### 待验证 / 反证 / 观察池",
    "### 判断修正 / 已被反证",
    "<!-- research-os-curation:",
]


def _load_report_policy() -> dict[str, Any]:
    path = ROOT / "config" / "report_policy.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_industry_dir_glob() -> str:
    policy = _load_report_policy()
    value = policy.get("industry_report", {}).get("dir_glob")
    return value if isinstance(value, str) and value.strip() else _DEFAULT_INDUSTRY_DIR_GLOB


def get_industry_required_terms() -> list[str]:
    policy = _load_report_policy()
    value = policy.get("industry_report", {}).get("required_terms")
    if isinstance(value, list) and value and all(isinstance(x, str) for x in value):
        return value
    return list(_DEFAULT_INDUSTRY_REQUIRED_TERMS)


def get_forbidden_report_terms() -> list[str]:
    policy = _load_report_policy()
    value = policy.get("latest_report", {}).get("forbidden_terms")
    if isinstance(value, list) and value and all(isinstance(x, str) for x in value):
        return value
    return list(_DEFAULT_FORBIDDEN_REPORT_TERMS)


def get_theme_canonical_required() -> list[str]:
    policy = _load_report_policy()
    value = policy.get("theme_report", {}).get("canonical_required")
    if isinstance(value, list) and value and all(isinstance(x, str) for x in value):
        return value
    return list(_DEFAULT_THEME_CANONICAL_REQUIRED)


def get_theme_quality_policy() -> dict[str, Any]:
    policy = _load_report_policy()
    theme_report_policy = policy.get("theme_report", {})
    theme_report_policy = theme_report_policy if isinstance(theme_report_policy, dict) else {}
    quality = theme_report_policy.get("quality")
    if not isinstance(quality, dict):
        quality = {}
    return {
        "min_chars": int(quality.get("min_chars", 0) or 0),
        "min_images": int(quality.get("min_images", 0) or 0),
        "max_todo_count": int(quality.get("max_todo_count", 9999) or 9999),
        "required_sections": [str(x) for x in quality.get("required_sections", []) if isinstance(x, str)],
        "required_terms": [str(x) for x in quality.get("required_terms", []) if isinstance(x, str)],
        "quality_by_theme": (
            theme_report_policy.get("quality_by_theme")
            if isinstance(theme_report_policy.get("quality_by_theme"), dict)
            else quality.get("quality_by_theme", {})
        ),
    }


def _theme_quality_policy_for(key: str, base_policy: dict[str, Any]) -> dict[str, Any]:
    policy = dict(base_policy)
    by_theme = policy.pop("quality_by_theme", {})
    override = by_theme.get(key) if isinstance(by_theme, dict) else None
    if isinstance(override, dict):
        for name in ("min_chars", "min_images", "max_todo_count"):
            if name in override:
                policy[name] = int(override.get(name) or 0)
        for name in ("required_sections", "required_terms"):
            if isinstance(override.get(name), list):
                policy[name] = [str(x) for x in override[name] if isinstance(x, str)]
    return policy


def _main_report_text(text: str) -> str:
    # 附录/loop 日志用于审计，不应把“待补验证”当作正文占位。
    for marker in ("## 附录 · Loop 证据增量日志", "## 滚动修订记录"):
        if marker in text:
            return text.split(marker, 1)[0]
    return text


def _final_report_files() -> list[Path]:
    files: list[Path] = []
    themes_root = ROOT / "reports" / "themes"
    stocks_root = ROOT / "reports" / "stocks"
    weekly_root = ROOT / "reports" / "weekly"
    if themes_root.exists():
        files.extend(sorted(themes_root.glob("*/report.md")))
    if stocks_root.exists():
        files.extend(sorted(stocks_root.glob("*/report.md")))
    if weekly_root.exists():
        files.extend(
            path
            for path in sorted(weekly_root.glob("*.md"))
            if not path.name.endswith("_change_log.md")
        )
    return files


def check_final_reports_no_operational_logs() -> list[dict[str, Any]]:
    offenders: list[str] = []
    for path in _final_report_files():
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if any(marker in text for marker in FINAL_REPORT_OPERATIONAL_MARKERS):
            offenders.append(str(path.relative_to(ROOT)))
    return [
        {
            "check": "final_reports:no_operational_logs",
            "status": "ok" if not offenders else "error",
            "reports_scanned": len(_final_report_files()),
            **({"offenders": offenders} if offenders else {}),
        }
    ]


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

SECRET_SCAN_PATHS = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "config",
    "data/raw",
    "docs",
    "evidence",
    "reports",
    "runs",
    "state",
]

SECRET_PATTERNS = {
    "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{16,}\b"),
    "named_secret_assignment": re.compile(r"(?i)\b(api[_-]?key|secret|token)\b\s*[:=]\s*['\"]?[A-Za-z0-9][A-Za-z0-9_.-]{16,}"),
    "bearer_token": re.compile(r"(?i)\bauthorization\b\s*[:=]\s*['\"]?bearer\s+[A-Za-z0-9_.-]{16,}"),
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


def check_no_secret_leaks() -> list[dict[str, Any]]:
    offenders: list[dict[str, str]] = []
    for base in SECRET_SCAN_PATHS:
        path = ROOT / base
        if not path.exists():
            continue
        paths = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
        for file_path in paths:
            if _should_skip_secret_scan_file(file_path):
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            except Exception as exc:
                offenders.append({"path": str(file_path.relative_to(ROOT)), "pattern": "read_error", "detail": repr(exc)})
                continue
            for name, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    offenders.append({"path": str(file_path.relative_to(ROOT)), "pattern": name})
                    break
    return [{"check": "secrets:no_leaks", "status": "ok" if not offenders else "error", "offenders": offenders[:20]}]


def _should_skip_secret_scan_file(path: Path) -> bool:
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".duckdb", ".parquet", ".pyc"}:
        return True
    try:
        if path.stat().st_size > 2_000_000:
            return True
    except OSError:
        return True
    return False


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
    forbidden_report_terms = get_forbidden_report_terms()
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
    if review.get("agent_provider") in {"codex", "claude", "openai_compatible"}:
        checks.append({"check": "latest_loop:llm_agent_review", "status": "ok"})
    else:
        checks.append({"check": "latest_loop:llm_agent_review", "status": "warn", "provider": review.get("agent_provider")})
    return checks


def _image_refs(markdown_text: str) -> list[str]:
    """抽取 markdown 里的图片引用(![](path) 与 <img src=...>)。"""
    refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown_text)
    refs += re.findall(r"<img[^>]*\bsrc=[\"\']([^\"\']+)[\"\']", markdown_text)
    cleaned: list[str] = []
    for raw in refs:
        ref = raw.strip().split()[0].strip("<>") if raw.strip() else ""
        if ref:
            cleaned.append(ref)
    return cleaned


def check_theme_reports() -> list[dict[str, Any]]:
    """canonical 主题报告门禁(方案 A)。

    - reports/themes/<key>/report.md 必须存在(canonical_required 列出的核心主题);
    - 每篇主题报告里的本地图片引用必须能解析到真实文件(F1: 断链检查)。
    远程 http(s) 引用跳过。
    """
    checks: list[dict[str, Any]] = []
    themes_root = ROOT / "reports" / "themes"
    required_theme_keys = get_theme_canonical_required()
    quality_policy = get_theme_quality_policy()

    # 1) canonical 核心主题必须存在 report.md
    for key in required_theme_keys:
        report = themes_root / key / "report.md"
        checks.append(
            {
                "check": f"theme_report:canonical:{key}",
                "status": "ok" if report.exists() else "error",
                "path": str(report.relative_to(ROOT)),
            }
        )

    # 2) 核心主题报告质量门禁:对标深度研究文章,不能只保留空壳/流水日志
    for key in required_theme_keys:
        report = themes_root / key / "report.md"
        if not report.exists():
            continue
        try:
            text = report.read_text(encoding="utf-8")
        except Exception as exc:
            checks.append({"check": f"theme_report:quality:{key}", "status": "error", "error": repr(exc)})
            continue
        policy_for_theme = _theme_quality_policy_for(key, quality_policy)
        main_text = _main_report_text(text)
        missing_sections = [section for section in policy_for_theme["required_sections"] if section not in main_text]
        missing_terms = [term for term in policy_for_theme["required_terms"] if term not in main_text]
        image_count = len(_image_refs(text))
        char_count = len(main_text)
        todo_count = main_text.count("待补")
        ok = (
            char_count >= policy_for_theme["min_chars"]
            and image_count >= policy_for_theme["min_images"]
            and todo_count <= policy_for_theme["max_todo_count"]
            and not missing_sections
            and not missing_terms
        )
        checks.append(
            {
                "check": f"theme_report:quality:{key}",
                "status": "ok" if ok else "error",
                "path": str(report.relative_to(ROOT)),
                "char_count": char_count,
                "image_count": image_count,
                "todo_count": todo_count,
                **({"missing_sections": missing_sections} if missing_sections else {}),
                **({"missing_terms": missing_terms} if missing_terms else {}),
            }
        )
        structure_review = review_report_text(
            root=ROOT,
            text=main_text,
            report_path=report,
            theme_key=key,
            policy=policy_for_theme,
        )
        summary = structure_review.get("summary", {})
        findings = structure_review.get("findings", [])
        checks.append(
            {
                "check": f"theme_report:structure:{key}",
                # New skill-aligned structural checks are intentionally warn-only
                # until existing canonical reports have been backfilled.
                "status": "ok" if not findings else "warn",
                "path": str(report.relative_to(ROOT)),
                "p1": summary.get("p1", 0),
                "p2": summary.get("p2", 0),
                "finding_count": summary.get("finding_count", len(findings)),
                **({"findings": [item.get("title", "") for item in findings[:8]]} if findings else {}),
            }
        )

    # 3) 全部主题报告的本地图片断链检查
    broken: list[str] = []
    report_files = sorted(themes_root.glob("*/report.md")) if themes_root.exists() else []
    for report in report_files:
        try:
            text = report.read_text(encoding="utf-8")
        except Exception:
            continue
        for ref in _image_refs(text):
            if ref.startswith(("http://", "https://", "data:")):
                continue
            target = (report.parent / ref).resolve()
            if not target.exists():
                broken.append(f"{report.relative_to(ROOT)} -> {ref}")
    checks.append(
        {
            "check": "theme_report:image_links",
            "status": "ok" if not broken else "error",
            **({"broken": broken} if broken else {}),
            "reports_scanned": len(report_files),
        }
    )
    checks.extend(check_final_reports_no_operational_logs())
    return checks


def check_industry_analysis_report() -> list[dict[str, Any]]:
    """LEGACY(方案 A): reports/industry 是历史/手写深度快照, 不再是主报告门禁。

    canonical final reports 已迁移到 reports/themes/(见 check_theme_reports)。
    这里保留为可选检查: 目录缺失只 warn(skip), 目录存在时才校验其内部完整性,
    以免 legacy 快照缺失阻塞整个 loop。
    """
    root = ROOT / "reports" / "industry"
    dirs = sorted(root.glob(get_industry_dir_glob())) if root.exists() else []
    if not dirs:
        return [{"check": "industry_report:legacy_snapshot", "status": "warn", "reason": f"no legacy reports/industry/{get_industry_dir_glob()} (migrated to reports/themes/)"}]
    report_dir = dirs[-1]
    report = report_dir / "report.md"
    quality_path = report_dir / "quality_report.json"
    source_path = report_dir / "source_data.json"
    assets_dir = report_dir / "assets"
    checks: list[dict[str, Any]] = [
        {"check": "industry_report:legacy_artifact", "status": "ok" if report.exists() else "warn", "path": str(report.relative_to(ROOT))},
        {"check": "industry_report:legacy_source_data", "status": "ok" if source_path.exists() else "warn"},
        {"check": "industry_report:legacy_assets", "status": "ok" if assets_dir.exists() and any(assets_dir.glob("*.png")) else "warn"},
    ]
    try:
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
    except Exception as exc:
        checks.append({"check": "industry_report:legacy_quality", "status": "warn", "error": repr(exc)})
        return checks
    checks.append({"check": "industry_report:legacy_quality", "status": "ok" if quality.get("passed") is True else "warn", "score": quality.get("score"), "total": quality.get("total")})
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    required_terms = get_industry_required_terms()
    checks.append(
        {
            "check": "industry_report:legacy_deep_report_terms",
            "status": "ok" if all(term in text for term in required_terms) else "warn",
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
    checks.extend(check_theme_reports())
    checks.extend(check_industry_analysis_report())
    checks.extend(check_no_core_external_imports())
    checks.extend(check_no_secret_leaks())
    provider_payload = run_provider_smoke(live=live)
    provider_ok = provider_payload.get("status") == "ok" and provider_payload.get("returncode") == 0
    checks.append({"check": "providers:smoke", "status": "ok" if provider_ok else "error", "details": provider_payload})
    status = "ok" if all(item.get("status") in {"ok", "warn"} for item in checks) else "error"
    return {"status": status, "checks": checks}
