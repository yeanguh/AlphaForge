from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop_os.report_curation import (
    CURATION_HEADER,
    _candidate_strength,
    _fmt_pct,
    _snippet,
    _unique_lines,
    build_increment_block,
    update_rolling_report,
)


ROOT = Path(__file__).resolve().parents[1]

# 每份最终报告里,loop 证据统一沉淀到该分节,永不覆盖人工正文
LOOP_LOG_HEADER = "## 附录 · Loop 证据增量日志"
# 低质量但有价值的线索池,不进入正文结论
WATCH_POOL_HEADER = "### 待验证 / 反证 / 观察池"
# 被后续轮次反证/推翻的旧判断,软标记沉淀于此分节(保留审计痕迹,不物理删除)
REVISION_HEADER = "### 判断修正 / 已被反证"

# 达到该强度阈值的增量才计入正文证据日志,否则仅进观察池
STRENGTH_MAIN_THRESHOLD = 12

# runs 才保留、绝不进入最终报告的阻断信号
_BLOCKING_ISSUES = {"status=error", "cycle_errors_present", "agent_review_not_usable"}

# 主题池默认回退(config/theme_pool.json 缺失/损坏时使用),与配置文件保持一致的最小集
_DEFAULT_THEME_TIERS = {
    "ai-compute-infra": "core",
    "datacenter-power": "core",
    "physical-ai": "core",
    "agentic-ai": "core",
    "sovereign-ai": "core",
    "ai-security-governance": "core",
    "edge-ai": "watch",
    "ai-healthcare": "watch",
    "ai-industrial-software": "watch",
    "ai-commercialization": "watch",
    "autonomous-low-altitude": "watch",
    "quantum-computing": "emerging",
    "space-defense-ai": "emerging",
    "ai-fintech-infra": "emerging",
    "blockchain-ai-payments": "emerging",
}
_DEFAULT_TIER_POLICY = {
    "core": {"watch_pool_default": False},
    "watch": {"watch_pool_default": False},
    "emerging": {"watch_pool_default": True},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_week(payload: dict[str, Any]) -> str:
    raw = str(payload.get("finished_at") or payload.get("started_at") or "")
    dt: datetime | None = None
    if raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            dt = None
    if dt is None:
        dt = datetime.now(timezone.utc)
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def _marker(payload: dict[str, Any], scope: str) -> str:
    run_id = str(payload.get("run_id") or "unknown-run")
    cycle = str(payload.get("cycle") or "unknown-cycle")
    return f"<!-- research-os-curation:{scope}:{run_id}:{cycle} -->"


def _pipeline(payload: dict[str, Any]) -> dict[str, Any]:
    pipeline = payload.get("research_pipeline", {})
    return pipeline if isinstance(pipeline, dict) else {}


def _selected_chain(payload: dict[str, Any]) -> dict[str, Any]:
    chain = _pipeline(payload).get("selected_industry_chain", {})
    return chain if isinstance(chain, dict) else {}


def _is_failed_cycle(payload: dict[str, Any], issues: list[str]) -> bool:
    if payload.get("status") == "error":
        return True
    return any(issue in _BLOCKING_ISSUES for issue in issues)


# ---------------------------------------------------------------------------
# 主题池:core/watch/emerging 三层,配置驱动,带默认回退
# ---------------------------------------------------------------------------

def _load_theme_pool(root: Path | None = None) -> dict[str, Any]:
    base = root if root is not None else ROOT
    path = base / "config" / "theme_pool.json"
    if not path.exists():
        # 允许项目根不在 report_router 上一级(如测试临时目录),再退回真实仓库根
        path = ROOT / "config" / "theme_pool.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _theme_index(pool: dict[str, Any]) -> dict[str, str]:
    """构造 alias/key -> theme_key 的规范化索引(全部小写、去空白)。"""
    themes = pool.get("themes")
    themes = themes if isinstance(themes, dict) else {}
    index: dict[str, str] = {}
    for key, meta in themes.items():
        norm_key = str(key).strip().lower()
        index[norm_key] = key
        index[norm_key.replace("-", "_")] = key
        index[norm_key.replace("_", "-")] = key
        aliases = meta.get("aliases", []) if isinstance(meta, dict) else []
        for alias in aliases if isinstance(aliases, list) else []:
            index[str(alias).strip().lower()] = key
    return index


def resolve_theme_key(selected_theme: str, root: Path | None = None) -> str | None:
    """把 payload 的 selected_theme(如 ai_physical_ai)解析为规范主题目录键(如 physical-ai)。

    匹配顺序:精确 key/alias -> token 子串包含。无法解析返回 None。
    """
    raw = str(selected_theme or "").strip().lower()
    if not raw:
        return None
    pool = _load_theme_pool(root)
    index = _theme_index(pool) if pool else {}
    if not index:
        # 回退:仅按默认 tier 表的 key 做 token 包含匹配
        index = {k: k for k in _DEFAULT_THEME_TIERS}
        for k in list(index):
            index[k.replace("-", "_")] = k
    if raw in index:
        return index[raw]
    # token 子串包含(双向):selected_theme 含主题 token,或主题 key 含 selected_theme token
    raw_tokens = [t for t in raw.replace("_", "-").split("-") if len(t) >= 3]
    for norm, key in index.items():
        key_tokens = [t for t in norm.replace("_", "-").split("-") if len(t) >= 3]
        if any(rt in norm for rt in raw_tokens) or any(kt in raw for kt in key_tokens):
            return key
    return None


def theme_tier(theme_key: str | None, root: Path | None = None) -> str:
    if not theme_key:
        return "core"
    pool = _load_theme_pool(root)
    themes = pool.get("themes") if isinstance(pool, dict) else None
    if isinstance(themes, dict) and theme_key in themes and isinstance(themes[theme_key], dict):
        tier = themes[theme_key].get("tier")
        if isinstance(tier, str) and tier:
            return tier
    return _DEFAULT_THEME_TIERS.get(theme_key, "core")


def _tier_watch_pool_default(tier: str, root: Path | None = None) -> bool:
    pool = _load_theme_pool(root)
    tier_policy = pool.get("tier_policy") if isinstance(pool, dict) else None
    if isinstance(tier_policy, dict) and tier in tier_policy and isinstance(tier_policy[tier], dict):
        val = tier_policy[tier].get("watch_pool_default")
        if isinstance(val, bool):
            return val
    return bool(_DEFAULT_TIER_POLICY.get(tier, {}).get("watch_pool_default", False))


def _theme_label(theme_key: str | None, fallback: str, root: Path | None = None) -> str:
    if not theme_key:
        return fallback
    pool = _load_theme_pool(root)
    themes = pool.get("themes") if isinstance(pool, dict) else None
    if isinstance(themes, dict) and theme_key in themes and isinstance(themes[theme_key], dict):
        label = themes[theme_key].get("label")
        if isinstance(label, str) and label:
            return label
    return fallback


def _ensure_section(text: str, header: str) -> str:
    """确保文本存在指定分节标题,若无则追加一个空分节,返回更新后的文本。"""
    if header in text:
        return text
    return text.rstrip() + "\n\n" + header + "\n\n"


def _append_block_under_header(text: str, header: str, block: str) -> str:
    """在指定分节标题之后追加区块(区块自带 marker,调用方已做去重)。"""
    text = _ensure_section(text, header)
    return text.rstrip() + "\n\n" + block


def _resolve_theme_report(root: Path, theme_key: str | None, chain: dict[str, Any]) -> Path:
    """定位/播种主题最终报告路径 reports/themes/<theme_key>/report.md(方案 A:themes 统一取代 industry)。

    方案 A:产业报告是主题报告的一种,人工产业正文已物理迁移到 reports/themes/<theme_key>/report.md。
    日常 loop 只写 reports/themes/;遗留 reports/industry/ 仅作迁移来源,loop 绝不触碰。
    - theme_key 已解析:reports/themes/<theme_key>/report.md。
    - 未解析:回退到 reports/themes/<selected_theme 规范化 或 uncategorized>/report.md。
    """
    themes_root = root / "reports" / "themes"
    if theme_key:
        return themes_root / theme_key / "report.md"
    theme_raw = str(chain.get("selected_theme") or "").lower()
    slug = theme_raw.replace("_", "-").strip("-") or "uncategorized"
    return themes_root / slug / "report.md"


# ---------------------------------------------------------------------------
# 各内容类型的增量正文构造
# ---------------------------------------------------------------------------

def _industry_lines(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    chain = _selected_chain(payload)
    if chain.get("selected_theme"):
        lines.append(
            f"- 主线判断:当前候选主题 `{chain.get('selected_theme')}`,产业链分数 {chain.get('score', 'NA')},阶段 {chain.get('stage', 'NA')}。"
        )
    screen = chain.get("bottleneck_screen")
    bottlenecks = []
    if isinstance(screen, dict):
        bottlenecks = screen.get("candidates", []) or []
    elif isinstance(chain.get("bottleneck_candidates"), list):
        bottlenecks = chain.get("bottleneck_candidates")
    for item in (bottlenecks or [])[:3]:
        if isinstance(item, dict):
            lines.append(
                f"- 卡口候选:{_snippet(item.get('link') or item.get('name'))},代表公司 {_snippet(item.get('companies'))},失败条件 {_snippet(item.get('invalidation'))}。"
            )
    reports = payload.get("industry_reports", [])
    reports = reports if isinstance(reports, list) else []
    for item in reports[:4]:
        if isinstance(item, dict) and item.get("title"):
            lines.append(f"- 研报证据:{item.get('org') or '公开研报'}《{_snippet(item.get('title'), 80)}》。")
    for item in (chain.get("next_verifications", []) or [])[:4]:
        lines.append(f"- 待补验证:{_snippet(item, 100)}")
    return _unique_lines(lines)


def _stock_lines(symbol: str, payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    pipeline = _pipeline(payload)
    analyzers = pipeline.get("stock_analyzer", [])
    analyzers = analyzers if isinstance(analyzers, list) else []
    analyzer = next((a for a in analyzers if isinstance(a, dict) and str(a.get("symbol")) == symbol), None)
    if analyzer:
        val = analyzer.get("valuation")
        if isinstance(val, dict):
            lines.append(
                f"- 估值快照:PE {val.get('pe', 'NA')} / PB {val.get('pb', 'NA')},区间 {val.get('band', 'NA')},评分 {val.get('score', 'NA')}({_snippet(val.get('method'), 80)})。"
            )
        for role, label in (("business_model", "商业模式"), ("catalyst", "催化"), ("risk", "风险")):
            v = analyzer.get(role)
            if isinstance(v, str) and v.strip():
                lines.append(f"- {label}:{_snippet(v, 120)}")
            elif isinstance(v, list) and v:
                lines.append(f"- {label}:" + ";".join(_snippet(x, 60) for x in v[:3]) + "。")
    supplements = payload.get("stock_supplements", {})
    supplements = supplements if isinstance(supplements, dict) else {}
    sup = supplements.get(symbol)
    if isinstance(sup, dict):
        for role, label in (("fundamental", "基本面"), ("fund_flow", "资金面"), ("dragon_tiger", "龙虎榜")):
            v = sup.get(role)
            if isinstance(v, dict) and v:
                lines.append(f"- {label}:{_snippet(v, 120)}")
            elif isinstance(v, list) and v:
                lines.append(f"- {label}:{len(v)} 条记录,首条 {_snippet(v[0], 80)}。")
        for role, label in (("catalysts", "公告催化"), ("risks", "风险提示")):
            v = sup.get(role)
            if isinstance(v, list) and v:
                lines.append(f"- {label}:" + ";".join(_snippet(x, 60) for x in v[:3]) + "。")
    decisions = pipeline.get("trade_decision_engine", {})
    decisions = decisions.get("decisions", []) if isinstance(decisions, dict) else []
    dec = next((d for d in decisions if isinstance(d, dict) and str(d.get("symbol")) == symbol), None)
    if isinstance(dec, dict):
        lines.append(
            f"- 决策框架:动作 `{dec.get('action', 'NA')}`,通过条件 {dec.get('passed_conditions', 'NA')},最小风险收益比 {dec.get('min_risk_reward', 'NA')}。"
        )
    return _unique_lines(lines)


def _weekly_lines(payload: dict[str, Any], issues: list[str]) -> list[str]:
    lines: list[str] = []
    chain = _selected_chain(payload)
    if chain.get("selected_theme"):
        lines.append(f"- 主题:`{chain.get('selected_theme')}`(分数 {chain.get('score', 'NA')})。")
    review = payload.get("agent_review", {})
    if isinstance(review, dict):
        reason = review.get("reason")
        if reason:
            lines.append(f"- 复核结论:{_snippet(reason, 140)}")
        next_actions = review.get("next_actions", [])
        if isinstance(next_actions, list) and next_actions:
            lines.append("- 验证进展:" + ";".join(_snippet(x, 60) for x in next_actions[:4]) + "。")
    if issues:
        lines.append("- 失败假设 / 本轮限制:`" + "`, `".join(issues[:6]) + "`。")
    return _unique_lines(lines)


def _watch_pool_lines(payload: dict[str, Any], issues: list[str]) -> list[str]:
    lines: list[str] = []
    headlines = payload.get("news", {}).get("headlines", [])
    headlines = headlines if isinstance(headlines, list) else []
    for item in headlines[:4]:
        if isinstance(item, dict) and item.get("title"):
            lines.append(f"- 资讯线索:{item.get('source') or '公开来源'}《{_snippet(item.get('title'), 80)}》(待验证)。")
    if issues:
        lines.append("- 本轮限制:`" + "`, `".join(issues[:6]) + "`,仅作观察线索,不替换正文结论。")
    return _unique_lines(lines)


def _revision_lines(payload: dict[str, Any]) -> list[str]:
    """从 payload 提取「本轮推翻/反证的旧判断」。

    约定来源:agent_review.invalidations 或 selected_chain.invalidated_claims,
    形如 [{"claim": "...", "reason": "..."}] 或纯字符串列表。
    """
    out: list[dict[str, str]] = []
    review = payload.get("agent_review", {})
    candidates: list[Any] = []
    if isinstance(review, dict) and isinstance(review.get("invalidations"), list):
        candidates.extend(review["invalidations"])
    chain = _selected_chain(payload)
    if isinstance(chain.get("invalidated_claims"), list):
        candidates.extend(chain["invalidated_claims"])
    for item in candidates:
        if isinstance(item, dict) and (item.get("claim") or item.get("statement")):
            out.append(
                {
                    "claim": str(item.get("claim") or item.get("statement")),
                    "reason": str(item.get("reason") or item.get("evidence") or ""),
                }
            )
        elif isinstance(item, str) and item.strip():
            out.append({"claim": item.strip(), "reason": ""})
    lines: list[str] = []
    for rev in out[:6]:
        reason = f"(依据:{_snippet(rev['reason'], 80)})" if rev["reason"] else ""
        lines.append(f"- ~~{_snippet(rev['claim'], 100)}~~ 已被本轮反证{reason}。")
    return _unique_lines(lines)


def _build_scoped_block(payload: dict[str, Any], scope: str, body_lines: list[str], header_note: str = "") -> str:
    marker = _marker(payload, scope)
    run_id = str(payload.get("run_id") or "unknown-run")
    cycle = str(payload.get("cycle") or "unknown-cycle")
    strength = _candidate_strength(payload)
    lines = [
        marker,
        f"#### {_now_iso()} · {run_id} cycle {cycle}{header_note}",
        "",
        f"- 增量强度:{strength};本轮状态:`{payload.get('status')}`。",
    ]
    lines.extend(body_lines)
    return "\n".join(lines).rstrip() + "\n"


def _merge_into_report(
    *,
    report_path: Path,
    payload: dict[str, Any],
    scope: str,
    main_lines: list[str],
    watch_lines: list[str],
    seed_title: str,
    to_watch_pool: bool,
    revision_lines: list[str] | None = None,
    seed_body: str | None = None,
) -> dict[str, Any]:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    marker = _marker(payload, scope)
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    seeded = False
    if not existing:
        # 若提供 seed_body(如从遗留 industry 报告迁移的人工正文),则以其为种子,
        # 否则仅播种一个标题。人工正文永远不会被覆盖,只会被增量追加。
        existing = seed_body if (seed_body and seed_body.strip()) else f"# {seed_title}\n"
        seeded = True
    if marker in existing:
        return {"status": "skipped", "scope": scope, "reason": "increment already present", "path": report_path.name}

    if to_watch_pool:
        block = _build_scoped_block(payload, scope, watch_lines or ["- (无可用观察线索)"], header_note="  · 观察池")
        existing = _ensure_section(existing, LOOP_LOG_HEADER)
        existing = _ensure_section(existing, WATCH_POOL_HEADER)
        updated = existing.rstrip() + "\n\n" + block
        mode = "watch_pool"
    else:
        block = _build_scoped_block(payload, scope, main_lines or ["- (无可用正文增量)"])
        updated = _append_block_under_header(existing, LOOP_LOG_HEADER, block)
        mode = "main_log"

    # 修正旧判断:软标记沉淀,永不物理删除人工正文
    revisions = revision_lines or []
    if revisions:
        rev_block = _build_scoped_block(payload, f"{scope}:revision", revisions, header_note="  · 判断修正")
        updated = _ensure_section(updated, REVISION_HEADER)
        rev_marker = _marker(payload, f"{scope}:revision")
        if rev_marker not in updated:
            updated = updated.rstrip() + "\n\n" + rev_block

    report_path.write_text(updated, encoding="utf-8")
    return {
        "status": "seeded" if seeded else "merged",
        "scope": scope,
        "mode": mode,
        "path": str(report_path.name),
        "revisions": len(revisions),
    }


def route_cycle_reports(
    *,
    root: Path,
    payload: dict[str, Any],
    cycle_dir: Path,
    issues: list[str],
) -> dict[str, Any]:
    """按内容类型把本轮 loop 证据路由到对应最终报告。

    - 失败轮次:完全跳过,只留在 runs/。
    - 主题(theme)最终报告:reports/themes/<theme_key>/report.md,三层主题池驱动:
        core 每天必扫;watch 每周;emerging 默认只进观察池,strength 达标才升正文。
    - 方案 A:themes 统一取代 industry(产业报告即主题报告);日常 loop 只写 themes/,遗留 industry/ 已迁移、loop 不触碰。
    - 个股最终报告:reports/stocks/<symbol>/report.md。
    - 复盘周报:reports/weekly/YYYY-Www.md,始终累积。
    - daily/latest-full-loop.md:降级为增量 inbox(沿用 update_rolling_report)。
    - 每轮 loop 只做三件事:补新证据(正文日志)、修正旧判断(软标记)、追加反证(观察池)。
    """
    result: dict[str, Any] = {"routed": [], "skipped": [], "checked_at": _now_iso()}

    if _is_failed_cycle(payload, issues):
        result["skipped"].append({"reason": "failed_cycle_stays_in_runs", "issues": issues})
        return result

    strength = _candidate_strength(payload)
    strong_enough = strength >= STRENGTH_MAIN_THRESHOLD
    watch_lines = _watch_pool_lines(payload, issues)
    revision_lines = _revision_lines(payload)

    # 1) 主题最终报告(方案 A:themes 统一取代 industry;保留 industry 遗留兼容)
    chain = _selected_chain(payload)
    theme_key = resolve_theme_key(chain.get("selected_theme", ""), root)
    tier = theme_tier(theme_key, root)
    # tier 层级门槛:emerging 默认进观察池,除非本轮 strength 越过阈值(有实质事件)
    theme_to_watch = _tier_watch_pool_default(tier, root) or (not strong_enough)
    theme_report = _resolve_theme_report(root, theme_key, chain)
    theme_scope = f"theme:{theme_key}" if theme_key else "theme:uncategorized"
    # 方案 A:人工产业正文已一次性迁移至 reports/themes/;日常 loop 只在其上追加增量,不覆盖人工正文。
    outcome = _merge_into_report(
        report_path=theme_report,
        payload=payload,
        scope=theme_scope,
        main_lines=_industry_lines(payload),
        watch_lines=watch_lines,
        seed_title=f"{_theme_label(theme_key, '主题', root)}主题最终报告",
        to_watch_pool=theme_to_watch,
        revision_lines=revision_lines,
    )
    outcome["theme_key"] = theme_key
    outcome["tier"] = tier
    result["routed"].append(outcome)

    # 2) 个股最终报告(每只候选一份)
    to_watch_pool = not strong_enough
    supplements = payload.get("stock_supplements", {})
    supplements = supplements if isinstance(supplements, dict) else {}
    symbols = [str(s) for s in supplements.keys() if s]
    for symbol in symbols:
        stock_report = root / "reports" / "stocks" / symbol / "report.md"
        analyzers = _pipeline(payload).get("stock_analyzer", [])
        analyzers = analyzers if isinstance(analyzers, list) else []
        name = next(
            (a.get("name") for a in analyzers if isinstance(a, dict) and str(a.get("symbol")) == symbol and a.get("name")),
            symbol,
        )
        outcome = _merge_into_report(
            report_path=stock_report,
            payload=payload,
            scope=f"stock:{symbol}",
            main_lines=_stock_lines(symbol, payload),
            watch_lines=watch_lines,
            seed_title=f"{name}({symbol})个股最终报告",
            to_watch_pool=to_watch_pool,
            revision_lines=revision_lines,
        )
        result["routed"].append(outcome)

    # 3) 复盘周报(累积)
    week = _iso_week(payload)
    weekly_report = root / "reports" / "weekly" / f"{week}.md"
    weekly_outcome = _merge_into_report(
        report_path=weekly_report,
        payload=payload,
        scope="weekly",
        main_lines=_weekly_lines(payload, issues),
        watch_lines=watch_lines,
        seed_title=f"{week} 复盘周报",
        to_watch_pool=False,
    )
    result["routed"].append(weekly_outcome)

    # 4) daily 增量 inbox(降级:不再是最终报告,只沉淀原始增量流水)
    inbox = update_rolling_report(
        root=root,
        payload=payload,
        candidate_report_path=cycle_dir / "report.md",
        latest_report_path=root / "reports" / "daily" / "latest-full-loop.md",
        issues=issues,
    )
    result["inbox"] = inbox

    result["strength"] = strength
    result["to_watch_pool"] = to_watch_pool
    result["theme_key"] = theme_key
    result["tier"] = tier
    return result
