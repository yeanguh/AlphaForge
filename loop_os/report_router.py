from __future__ import annotations

import json
import re
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

# 每份最终报告的 loop 证据统一沉淀到旁路 change log,永不污染人工正文
CHANGE_LOG_NAME = "report_change_log.md"
LOOP_LOG_HEADER = "## 附录 · Loop 证据增量日志"
# 低质量但有价值的线索池,不进入正文结论
WATCH_POOL_HEADER = "### 待验证 / 反证 / 观察池"
# 被后续轮次反证/推翻的旧判断,软标记沉淀于此分节(保留审计痕迹,不物理删除)
REVISION_HEADER = "### 判断修正 / 已被反证"

# 达到该强度阈值的增量才计入正文证据日志,否则仅进观察池
STRENGTH_MAIN_THRESHOLD = 12

# 对标深度研究文章的 canonical 研报骨架。新主题不能只长成流水日志:
# 先保留可持续填充的研究框架,再把每轮 loop 证据追加到附录。
BENCHMARK_REPORT_SECTIONS = [
    "## 研究课题",
    "## 一句话结论",
    "## 市场盘点",
    "## 核心逻辑",
    "## 关键数据",
    "## 产业链跟踪",
    "## 投资机会挖掘",
    "## A股可交易标的估值对比",
    "## 核心个股交易跟踪",
    "## 产业链 / 竞争格局",
    "## 标的分层与入场条件",
    "## 风险、反证与退出条件",
    "## 数据来源与证据强度",
]

PHYSICAL_AI_REPORT_SECTIONS = [
    "## 0. 核心结论",
    "## 1. 研究对象、边界与口径",
    "## 2. 行业背景与需求驱动",
    "## 2.5 硬事实台账与证据密度",
    "## 3. 产业链全景图谱",
    "## 4. 上游材料、部件与制程要素挖掘",
    "## 5. 产业链核心环节价值分布",
    "## 6. 竞争格局与核心壁垒",
    "## 7. A股公司映射与核心地位判断",
    "## 8. 投资线索、交易跟踪与目标价情景",
    "## 9. 催化因素与产业传导路径",
    "## 10. 风险提示",
    "## 11. 数据来源、证据强度与待核验事项",
]

_SECTION_RE = re.compile(r"(?m)^## .+$")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|<img[^>]*\bsrc=[\"']([^\"']+)[\"']")
_BENCHMARK_STRUCTURE_TERMS = (
    "| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |",
    "| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |",
    "| 候选环节 | 不可替代 | 供给刚性 | 寡头垄断 | 机构低配 | 反证条件 |",
    "| 结论/数据 | 来源 | 日期 | 置信度 |",
)

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
    """在指定分节标题内追加区块(区块自带 marker,调用方已做去重)。"""
    text = _ensure_section(text, header)
    header_re = re.compile(rf"(?m)^{re.escape(header)}\s*$")
    match = header_re.search(text)
    if not match:
        return text.rstrip() + "\n\n" + block
    next_heading = re.search(r"(?m)^#{1,6}\s+", text[match.end():])
    if not next_heading:
        return text.rstrip() + "\n\n" + block
    insert_at = match.end() + next_heading.start()
    before = text[:insert_at].rstrip()
    after = text[insert_at:].lstrip("\n")
    return before + "\n\n" + block.rstrip() + "\n\n" + after


def _change_log_path(report_path: Path) -> Path:
    if report_path.name == "report.md":
        return report_path.with_name(CHANGE_LOG_NAME)
    return report_path.with_name(f"{report_path.stem}_change_log.md")


def _benchmark_seed_body(seed_title: str) -> str:
    """生成对标深度研究文的主题研报骨架。

    骨架只提供可填充章节,不伪造结论;后续循环通过附录证据日志和人工/agent
    复盘逐步把空位填实。
    """
    return "\n".join(
        [
            f"# {seed_title}",
            "",
            "## 研究课题",
            "",
            "围绕本主题持续验证:产业趋势是否从叙事进入供需、订单、价格或资本开支的可证伪阶段。",
            "",
            "## 一句话结论",
            "",
            "待补:给出方向、置信度、核心催化、首选标的与入场纪律。",
            "",
            "## 市场盘点",
            "",
            "### 技术突破",
            "",
            "- 待补:会改变性能、成本、供给或国产替代路径的技术事件。",
            "",
            "### 产能变化",
            "",
            "- 待补:扩产、涨价、交期、良率、材料供给和设备瓶颈。",
            "",
            "### 订单确认",
            "",
            "- 待补:大客户订单、平台放量、招投标、收入确认和 capex 指引。",
            "",
            "### 政策 / 监管 / 地缘",
            "",
            "- 待补:政策边际变化、地缘供给扰动、监管风险。",
            "",
            "### 市场观点",
            "",
            "- 待补:把不可证伪观点、短期情绪和可验证框架分开。",
            "",
            "## 核心逻辑",
            "",
            "1. 待补:需求侧变化、供给侧约束或政策/技术拐点。",
            "2. 待补:产业链利润向哪一环节传导,哪些环节只是主题受益。",
            "3. 待补:从公开证据到可交易标的的筛选链路。",
            "",
            "## 关键数据",
            "",
            "| 数据 | 数值/变化 | 来源 | 日期 | 置信度 |",
            "| --- | --- | --- | --- | --- |",
            "| 待补 | 待补 | 待补 | 待补 | 待补 |",
            "",
            "## 产业链跟踪",
            "",
            "| 环节 | 事实映射 | 供需变化方向 | 瓶颈/卡口 | A股映射 |",
            "| --- | --- | --- | --- | --- |",
            "| 待补 | 待补 | 待补 | 待补 | 待补 |",
            "",
            "## 投资机会挖掘",
            "",
            "### 瓶颈识别",
            "",
            "- 待补:明确哪个环节最缺、为什么短期解不了、价格/订单如何传导。",
            "",
            "### 可交易标的筛选",
            "",
            "- 待补:按直接暴露、业绩弹性、估值位置、交易拥挤度排序。",
            "",
            "## A股可交易标的估值对比",
            "",
            "| 公司 | 代码 | 产业链位置 | 当前估值 | 财务/订单信号 | 催化 | 买点条件 | 失效条件 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            "| 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |",
            "",
            "## 核心个股交易跟踪",
            "",
            "| 公司 | 代码 | 产业链位置 | 估值 | 财务质量 | 趋势结构 | 关键位 | 入场条件 | 止损/失效 | 目标/压力 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |",
            "",
            "## 产业链 / 竞争格局",
            "",
            "待补:上游 - 中游 - 下游结构、全球/国产竞争格局、卡口环节与替代路线。",
            "",
            "## 标的分层与入场条件",
            "",
            "- 核心环节龙头:待补。",
            "- 关键技术突破者:待补。",
            "- 重要配套:待补。",
            "- 待验证概念:待补。",
            "",
            "## 风险、反证与退出条件",
            "",
            "- 待补:价格/订单/产能/竞争/政策/估值拥挤的反证信号。",
            "",
            "## 数据来源与证据强度",
            "",
            "| 结论/数据 | 来源 | 日期 | 置信度 |",
            "| --- | --- | --- | --- |",
            "| 待补 | 待补 | 待补 | 待补 |",
            "",
        ]
    )


def _needs_benchmark_frame(text: str) -> bool:
    if not text.strip():
        return True
    if all(section in text for section in BENCHMARK_REPORT_SECTIONS):
        return False
    # 已有人写深度正文的报告不强行插入骨架;只给标题/附录日志的轻量报告补框架。
    content_before_log = text.split(LOOP_LOG_HEADER, 1)[0]
    return len(content_before_log.strip()) < 800


def _ensure_benchmark_frame(text: str, seed_title: str) -> str:
    if not _needs_benchmark_frame(text):
        return text
    frame = _benchmark_seed_body(seed_title).rstrip()
    if not text.strip():
        return frame + "\n"
    if LOOP_LOG_HEADER in text:
        _, rest = text.split(LOOP_LOG_HEADER, 1)
        return frame + "\n\n" + LOOP_LOG_HEADER + rest
    return frame + "\n\n" + text.lstrip()


def _split_main_and_loop(text: str) -> tuple[str, str]:
    if LOOP_LOG_HEADER not in text:
        return text.rstrip(), ""
    main, rest = text.split(LOOP_LOG_HEADER, 1)
    return main.rstrip(), (LOOP_LOG_HEADER + rest).rstrip()


def _append_legacy_log_once(change_log_path: Path, legacy_log: str) -> None:
    if not legacy_log.strip():
        return
    change_log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = change_log_path.read_text(encoding="utf-8") if change_log_path.exists() else ""
    markers = re.findall(r"<!--\s*research-os-curation:[^>]+-->", legacy_log)
    if markers and all(marker in existing for marker in markers):
        return
    if legacy_log.strip() in existing:
        return
    updated = existing.rstrip()
    updated = (updated + "\n\n" if updated else "") + legacy_log.strip() + "\n"
    change_log_path.write_text(updated, encoding="utf-8")


def _read_report_and_migrate_legacy_log(report_path: Path) -> tuple[str, Path, bool]:
    """Read canonical report text and move any old embedded loop log aside."""
    change_log_path = _change_log_path(report_path)
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    main, legacy_log = _split_main_and_loop(existing)
    migrated = bool(legacy_log)
    if migrated:
        cleaned = main.rstrip() + ("\n" if main.strip() else "")
        report_path.write_text(cleaned, encoding="utf-8")
        _append_legacy_log_once(change_log_path, legacy_log)
    return main, change_log_path, migrated


def _append_change_log_block(
    *,
    change_log_path: Path,
    marker: str,
    header: str,
    block: str,
) -> bool:
    change_log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = change_log_path.read_text(encoding="utf-8") if change_log_path.exists() else ""
    if marker in existing:
        return False
    updated = _ensure_section(existing, LOOP_LOG_HEADER)
    updated = _append_block_under_header(updated, header, block)
    change_log_path.write_text(updated, encoding="utf-8")
    return True


def _section_map(text: str) -> dict[str, str]:
    """Return a markdown H2 section map keyed by the literal H2 heading."""
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[match.group(0).strip()] = text[start:end].strip()
    return sections


def _image_refs(markdown_text: str) -> list[str]:
    refs: list[str] = []
    for md_ref, html_ref in _IMAGE_RE.findall(markdown_text):
        ref = (md_ref or html_ref).strip().split()[0].strip("<>")
        if ref:
            refs.append(ref)
    return refs


def _section_quality(text: str) -> int:
    """Small deterministic quality heuristic for section-level draft adoption."""
    compact = text.strip()
    if not compact:
        return 0
    score = min(len(compact) // 120, 16)
    score -= compact.count("待补") * 4
    score -= compact.count("NA") * 2
    score -= compact.count("待采集") * 5
    if compact.count("PE 待采集") >= 3 or compact.count("财务指标待采集") >= 3:
        score -= 90
    score -= 5 if "围绕本主题持续验证:产业趋势是否从叙事进入供需、订单、价格或资本开支的可证伪阶段" in compact else 0
    score += min(compact.count("|"), 12)
    score += 8 if _image_refs(compact) else 0
    score += 4 if "证据" in compact else 0
    score += 3 if "失效" in compact or "反证" in compact else 0
    strategic_terms = (
        "CPO", "光模块", "PCB", "液冷", "中际旭创", "新易盛", "天孚通信", "沪电股份", "胜宏科技", "深南电路",
        "工业富联", "浪潮信息", "中科曙光", "英维克", "申菱环境", "高澜股份", "寒武纪", "海光信息", "龙芯中科",
        "支撑", "压力", "风险收益比", "买入条件", "等待买入触发", "建议买点", "卖出", "目标", "核心节点三公司",
        "硬事实台账", "证据密度", "订单", "产能", "客户认证", "收入占比",
    )
    score += min(sum(3 for term in strategic_terms if term in compact), 48)
    if "第一优先级是 `先进封装材料与设备`" in compact:
        score -= 16
    if "核心标的K线结构" in compact:
        score -= 120
    if compact.count("建议买点") >= 8 and "等待买入触发" not in compact:
        score -= 90
    if "空头趋势" in compact and "建议买点" in compact:
        score -= 35
    if "physical-ai-stock-valuation" in compact or "核心标的估值与赔率" in compact:
        score += 14
    if "physical-ai-evidence-density" in compact or "证据密度评分" in compact:
        score += 10
    if "等待买入触发" in compact:
        score += 36
    if compact.startswith("## 核心个股交易跟踪"):
        has_buy_discipline = "买入条件" in compact or "等待买入触发" in compact or "建议买点" in compact
        has_sell_discipline = "卖出" in compact or "目标" in compact or "压力" in compact
        score += 120 if has_buy_discipline and has_sell_discipline else -60
    if "核心节点三公司" not in compact and "产业链图谱" in compact:
        score -= 12
    return score


def _has_benchmark_sections(text: str) -> bool:
    return all(section in text for section in BENCHMARK_REPORT_SECTIONS)


def _has_physical_ai_sections(text: str) -> bool:
    return all(section in text for section in PHYSICAL_AI_REPORT_SECTIONS)


def _is_weak_benchmark_seed(text: str) -> bool:
    """Detect a seeded skeleton/weak first-pass report that a full draft may replace."""
    main, _ = _split_main_and_loop(text)
    if not main.strip():
        return True
    if not _has_benchmark_sections(main):
        return False
    return main.count("待补") > 12 or len(_image_refs(main)) < 3


def _is_weak_physical_ai_seed(text: str) -> bool:
    main, _ = _split_main_and_loop(text)
    if not main.strip():
        return True
    if not _has_physical_ai_sections(main):
        return False
    return main.count("待补") > 8 or len(_image_refs(main)) < 4


def _is_complete_benchmark_draft(text: str) -> bool:
    return (
        _has_benchmark_sections(text)
        and len(_image_refs(text)) >= 3
        and text.count("待补") <= 1
        and len(text) >= 3000
        and all(term in text for term in _BENCHMARK_STRUCTURE_TERMS)
    )


def _has_benchmark_quality_structure(text: str) -> bool:
    return all(term in text for term in _BENCHMARK_STRUCTURE_TERMS)


def _is_complete_physical_ai_draft(text: str) -> bool:
    return _has_physical_ai_sections(text) and len(_image_refs(text)) >= 4 and text.count("待补") <= 8 and len(text) >= 8000


def _local_image_links_exist(report_path: Path, text: str) -> bool:
    for ref in _image_refs(text):
        if ref.startswith(("http://", "https://", "data:")):
            continue
        if not (report_path.parent / ref).exists():
            return False
    return True


def _candidate_draft_path(root: Path, payload: dict[str, Any]) -> Path | None:
    deep_report = payload.get("theme_deep_report")
    if not isinstance(deep_report, dict):
        return None
    draft = deep_report.get("draft")
    if not isinstance(draft, str) or not draft:
        return None
    path = root / draft
    return path if path.exists() else None


def _absorb_benchmark_draft(
    *,
    report_path: Path,
    current: str,
    candidate_text: str,
) -> tuple[str, dict[str, Any]]:
    """Merge better benchmark sections from a cycle draft into canonical text.

    This deliberately avoids whole-file replacement. A section is adopted only
    when the draft section is materially stronger than the current section, so
    failed/weak runs cannot wipe out a useful human-edited report.
    """
    candidate_main, _ = _split_main_and_loop(candidate_text)
    if not _has_benchmark_sections(candidate_main):
        return current, {"absorbed": False, "reason": "candidate_missing_benchmark_sections"}
    if not _has_benchmark_quality_structure(candidate_main):
        return current, {"absorbed": False, "reason": "candidate_missing_skill_quality_structure"}
    if not _local_image_links_exist(report_path, candidate_main):
        return current, {"absorbed": False, "reason": "candidate_image_link_broken"}

    current_main, current_loop = _split_main_and_loop(current)
    if _is_weak_benchmark_seed(current_main) and _is_complete_benchmark_draft(candidate_main):
        merged = candidate_main.rstrip()
        if current_loop:
            merged = merged + "\n\n" + current_loop
        return merged + "\n", {"absorbed": True, "mode": "full_draft_seed", "sections": "all"}
    if (
        report_path.parent.name != "ai-compute-infra"
        and "先进封装材料与设备" in current_main
        and "先进封装材料与设备" not in candidate_main
        and _is_complete_benchmark_draft(candidate_main)
    ):
        merged = candidate_main.rstrip()
        if current_loop:
            merged = merged + "\n\n" + current_loop
        return merged + "\n", {"absorbed": True, "mode": "full_draft_theme_cleanup", "sections": "all"}

    current_sections = _section_map(current_main)
    candidate_sections = _section_map(candidate_main)

    title = current_main.splitlines()[0].strip() if current_main.strip() else candidate_main.splitlines()[0].strip()
    if not title.startswith("# "):
        title = candidate_main.splitlines()[0].strip() if candidate_main.strip() else "# 主题最终报告"

    adopted: list[str] = []
    rendered = [title, ""]
    for header in BENCHMARK_REPORT_SECTIONS:
        existing_section = current_sections.get(header, "")
        candidate_section = candidate_sections.get(header, "")
        if candidate_section and _section_quality(candidate_section) > _section_quality(existing_section) + 1:
            rendered.append(candidate_section)
            adopted.append(header.replace("## ", ""))
        elif existing_section:
            rendered.append(existing_section)
        elif candidate_section:
            rendered.append(candidate_section)
            adopted.append(header.replace("## ", ""))
        else:
            rendered.append(header)
        rendered.append("")

    # Preserve any custom H2 sections that are not part of the benchmark frame.
    for header, section in current_sections.items():
        if header not in BENCHMARK_REPORT_SECTIONS and section not in rendered:
            rendered.append(section)
            rendered.append("")

    merged = "\n".join(rendered).rstrip()
    if current_loop:
        merged = merged + "\n\n" + current_loop
    return merged + "\n", {"absorbed": bool(adopted), "sections": adopted}


def _absorb_physical_ai_draft(
    *,
    report_path: Path,
    current: str,
    candidate_text: str,
) -> tuple[str, dict[str, Any]]:
    candidate_main, _ = _split_main_and_loop(candidate_text)
    if not _has_physical_ai_sections(candidate_main):
        return current, {"absorbed": False, "reason": "candidate_missing_physical_ai_sections"}
    if not _local_image_links_exist(report_path, candidate_main):
        return current, {"absorbed": False, "reason": "candidate_image_link_broken"}

    current_main, current_loop = _split_main_and_loop(current)
    if _is_weak_physical_ai_seed(current_main) and _is_complete_physical_ai_draft(candidate_main):
        merged = candidate_main.rstrip()
        if current_loop:
            merged = merged + "\n\n" + current_loop
        return merged + "\n", {"absorbed": True, "mode": "full_draft_seed", "sections": "all", "frame": "physical-ai"}

    current_sections = _section_map(current_main)
    candidate_sections = _section_map(candidate_main)

    title = current_main.splitlines()[0].strip() if current_main.strip() else candidate_main.splitlines()[0].strip()
    if not title.startswith("# "):
        title = candidate_main.splitlines()[0].strip() if candidate_main.strip() else "# 物理AI主题最终报告"

    adopted: list[str] = []
    rendered = [title, ""]
    for header in PHYSICAL_AI_REPORT_SECTIONS:
        existing_section = current_sections.get(header, "")
        candidate_section = candidate_sections.get(header, "")
        if candidate_section and _section_quality(candidate_section) > _section_quality(existing_section) + 1:
            rendered.append(candidate_section)
            adopted.append(header.replace("## ", ""))
        elif existing_section:
            rendered.append(existing_section)
        elif candidate_section:
            rendered.append(candidate_section)
            adopted.append(header.replace("## ", ""))
        else:
            rendered.append(header)
        rendered.append("")

    for header, section in current_sections.items():
        if header not in PHYSICAL_AI_REPORT_SECTIONS and section not in rendered:
            rendered.append(section)
            rendered.append("")

    merged = "\n".join(rendered).rstrip()
    if current_loop:
        merged = merged + "\n\n" + current_loop
    return merged + "\n", {"absorbed": bool(adopted), "sections": adopted, "frame": "physical-ai"}


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
    report_review = payload.get("report_review_agent", {})
    if isinstance(report_review, dict):
        summary = report_review.get("summary", {}) if isinstance(report_review.get("summary"), dict) else {}
        lines.append(
            f"- 报告Review Agent:{report_review.get('status', 'NA')};"
            f"P1={summary.get('p1', 'NA')},P2={summary.get('p2', 'NA')},建议:{_snippet(summary.get('recommendation'), 100)}"
        )
        for finding in (report_review.get("findings", []) if isinstance(report_review.get("findings"), list) else [])[:3]:
            if isinstance(finding, dict):
                lines.append(
                    f"- 报告改进项[{finding.get('priority', 'P?')}]:{_snippet(finding.get('title'), 40)};"
                    f"{_snippet(finding.get('recommendation'), 100)}"
                )
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
    report_review = payload.get("report_review_agent", {})
    if isinstance(report_review, dict):
        summary = report_review.get("summary", {}) if isinstance(report_review.get("summary"), dict) else {}
        lines.append(
            f"- 报告质量复核:{report_review.get('status', 'NA')};"
            f"P1={summary.get('p1', 'NA')},P2={summary.get('p2', 'NA')}。"
        )
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
    benchmark_frame: bool = False,
    deep_draft_path: Path | None = None,
) -> dict[str, Any]:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    marker = _marker(payload, scope)
    existing, change_log_path, migrated_legacy_log = _read_report_and_migrate_legacy_log(report_path)
    existing_log = change_log_path.read_text(encoding="utf-8") if change_log_path.exists() else ""
    seeded = False
    if not existing:
        # 若提供 seed_body(如从遗留 industry 报告迁移的人工正文),则以其为种子,
        # 主题报告播种对标深度研究文章的结构化骨架;个股/周报保持轻量标题。
        # 人工正文永远不会被覆盖,只会被增量追加。
        if seed_body and seed_body.strip():
            existing = seed_body
        elif benchmark_frame:
            existing = _benchmark_seed_body(seed_title)
        else:
            existing = f"# {seed_title}\n"
        seeded = True
    frame_backfilled = False
    if benchmark_frame:
        framed = _ensure_benchmark_frame(existing, seed_title)
        frame_backfilled = framed != existing
        existing = framed
    draft_absorption: dict[str, Any] = {"absorbed": False}
    if benchmark_frame and deep_draft_path is not None and deep_draft_path.exists():
        try:
            draft_text = deep_draft_path.read_text(encoding="utf-8")
        except Exception as exc:
            draft_absorption = {"absorbed": False, "reason": repr(exc)}
        else:
            if report_path.parent.name == "physical-ai":
                existing, draft_absorption = _absorb_physical_ai_draft(
                    report_path=report_path,
                    current=existing,
                    candidate_text=draft_text,
                )
            else:
                existing, draft_absorption = _absorb_benchmark_draft(
                    report_path=report_path,
                    current=existing,
                    candidate_text=draft_text,
                )
    if marker in existing_log:
        if frame_backfilled or draft_absorption.get("absorbed"):
            report_path.write_text(existing, encoding="utf-8")
            mode = "draft_absorb_only" if draft_absorption.get("absorbed") else "frame_backfill_only"
            return {
                "status": "merged",
                "scope": scope,
                "mode": mode,
                "path": report_path.name,
                "change_log_path": change_log_path.name,
                "migrated_legacy_log": migrated_legacy_log,
                "draft_absorption": draft_absorption,
            }
        if migrated_legacy_log:
            report_path.write_text(existing, encoding="utf-8")
        return {
            "status": "skipped",
            "scope": scope,
            "reason": "increment already present",
            "path": report_path.name,
            "change_log_path": change_log_path.name,
            "migrated_legacy_log": migrated_legacy_log,
        }

    if to_watch_pool:
        block = _build_scoped_block(payload, scope, watch_lines or ["- (无可用观察线索)"], header_note="  · 观察池")
        _append_change_log_block(
            change_log_path=change_log_path,
            marker=marker,
            header=WATCH_POOL_HEADER,
            block=block,
        )
        mode = "watch_pool"
    else:
        block = _build_scoped_block(payload, scope, main_lines or ["- (无可用正文增量)"])
        _append_change_log_block(
            change_log_path=change_log_path,
            marker=marker,
            header=LOOP_LOG_HEADER,
            block=block,
        )
        mode = "main_log"

    # 修正旧判断:软标记沉淀,永不物理删除人工正文
    revisions = revision_lines or []
    if revisions:
        rev_block = _build_scoped_block(payload, f"{scope}:revision", revisions, header_note="  · 判断修正")
        rev_marker = _marker(payload, f"{scope}:revision")
        _append_change_log_block(
            change_log_path=change_log_path,
            marker=rev_marker,
            header=REVISION_HEADER,
            block=rev_block,
        )

    report_path.write_text(existing.rstrip() + "\n", encoding="utf-8")
    return {
        "status": "seeded" if seeded else "merged",
        "scope": scope,
        "mode": mode,
        "path": str(report_path.name),
        "change_log_path": str(change_log_path.name),
        "migrated_legacy_log": migrated_legacy_log,
        "revisions": len(revisions),
        "draft_absorption": draft_absorption,
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
        benchmark_frame=True,
        deep_draft_path=_candidate_draft_path(root, payload),
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
