from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|<img[^>]*\bsrc=[\"']([^\"']+)[\"']")
_ARCHITECTURE_CONTEXT_FILES = (
    "docs/reference/architecture-invariants.md",
    "docs/reference/theme-pool-and-reports.md",
    "docs/reference/harness-checks.md",
    "docs/reference/data-access.md",
)
_COMPANY_MAPPING_COLUMNS = (
    "公司",
    "代码",
    "环节",
    "细分领域",
    "产业占比/暴露度",
    "核心技术/产品",
    "卡脖子相关性",
    "环节地位",
    "证据与备注",
)
_VALUE_DISTRIBUTION_COLUMNS = (
    "产业链环节",
    "细分领域/关键产品",
    "BOM成本占比/价值占比",
    "核心技术壁垒",
    "卡脖子程度",
    "代表A股公司",
    "公司环节地位",
    "证据口径/备注",
)
_BOTTLENECK_STANDARDS = ("不可替代", "供给刚性", "寡头垄断", "机构低配")
_SOURCE_SUMMARY_COLUMNS = ("结论/数据", "来源", "日期", "置信度")
_READER_FACING_FORBIDDEN_TERMS = (
    "公共数据适配器留痕",
    "render_source_trail_table",
    "adapter call",
    "health-check",
    "row count",
    "endpoint failure",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _rel(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _image_refs(markdown_text: str) -> list[str]:
    refs: list[str] = []
    for md_ref, html_ref in _IMAGE_RE.findall(markdown_text):
        ref = (md_ref or html_ref).strip().split()[0].strip("<>")
        if ref:
            refs.append(ref)
    return refs


def _has_table_columns(text: str, columns: tuple[str, ...], *, min_matches: int | None = None) -> bool:
    min_matches = min_matches if min_matches is not None else len(columns)
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        matches = sum(1 for column in columns if column in line)
        if matches >= min_matches:
            return True
    return False


def _mentions_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _theme_policy(root: Path, theme_key: str | None) -> dict[str, Any]:
    policy = _read_json(root / "config" / "report_policy.json")
    theme_report = policy.get("theme_report", {}) if isinstance(policy.get("theme_report"), dict) else {}
    base = dict(theme_report.get("quality", {}) if isinstance(theme_report.get("quality"), dict) else {})
    by_theme = theme_report.get("quality_by_theme", {})
    if theme_key and isinstance(by_theme, dict) and isinstance(by_theme.get(theme_key), dict):
        base.update(by_theme[theme_key])
    return base


def _architecture_context(root: Path, max_chars: int = 2400) -> str:
    chunks: list[str] = []
    for rel in _ARCHITECTURE_CONTEXT_FILES:
        text = _read_text(root / rel)
        if text:
            chunks.append(f"## {rel}\n{text[:max_chars]}")
    return "\n\n".join(chunks)[: max_chars * 2]


def _finding(priority: str, title: str, detail: str, recommendation: str) -> dict[str, str]:
    return {
        "priority": priority,
        "title": title,
        "detail": detail,
        "recommendation": recommendation,
    }


def _review_text_against_policy(
    *,
    root: Path,
    text: str,
    report_path: Path | None,
    theme_key: str | None,
    policy: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    findings: list[dict[str, str]] = []
    images = _image_refs(text)
    missing_images = []
    if report_path is not None:
        for ref in images:
            if ref.startswith(("http://", "https://", "data:")):
                continue
            if not (report_path.parent / ref).exists():
                missing_images.append(ref)

    required_sections = [str(x) for x in policy.get("required_sections", []) if isinstance(x, str)]
    required_terms = [str(x) for x in policy.get("required_terms", []) if isinstance(x, str)]
    missing_sections = [section for section in required_sections if section not in text]
    missing_terms = [term for term in required_terms if term not in text]
    min_chars = int(policy.get("min_chars") or 0)
    min_images = int(policy.get("min_images") or 0)
    max_todo = int(policy.get("max_todo_count") if policy.get("max_todo_count") is not None else 999)
    todo_count = text.count("待补")
    pending_collect_count = text.count("待采集")

    if missing_sections:
        findings.append(
            _finding(
                "P1",
                "缺少策略要求章节",
                "缺少: " + "、".join(missing_sections[:8]),
                "按 config/report_policy.json 补齐 canonical 章节，避免 loop 产物退化成流水日志。",
            )
        )
    if len(text) < min_chars:
        findings.append(
            _finding(
                "P1",
                "报告正文长度低于主题门槛",
                f"当前 {len(text)} 字符，门槛 {min_chars} 字符。",
                "优先补硬事实台账、产业链竞争格局、公司映射和反证条件，而不是堆叠泛化观点。",
            )
        )
    if len(images) < min_images:
        findings.append(
            _finding(
                "P2",
                "图表数量不足",
                f"当前 {len(images)} 张图，门槛 {min_images} 张图。",
                "补产业链图、估值对比图、候选 K 线图或财务趋势图；K线只允许用于现阶段买入候选。",
            )
        )
    if missing_images:
        findings.append(
            _finding(
                "P1",
                "报告存在坏图链",
                "缺失图片: " + "、".join(missing_images[:8]),
                "生成或迁移对应 assets 文件，或从正文移除无效引用。",
            )
        )
    if todo_count > max_todo:
        findings.append(
            _finding(
                "P2",
                "占位文字过多",
                f"`待补` 出现 {todo_count} 次，门槛 {max_todo} 次。",
                "将占位改成明确的证据缺口、下一轮验证项或观察池条目。",
            )
        )
    if pending_collect_count > max(8, max_todo):
        findings.append(
            _finding(
                "P2",
                "缺数占位表达过多",
                f"`待采集` 出现 {pending_collect_count} 次。",
                "将缺数表述改成明确的数据缺口、已尝试渠道和下一轮验证条件，避免报告读起来像半成品模板。",
            )
        )
    if theme_key not in {"ai-compute-infra"} and "先进封装材料与设备" in text:
        findings.append(
            _finding(
                "P2",
                "主题错配卡口残留",
                "非 AI 算力主题中出现 `先进封装材料与设备`。",
                "全量主题池生成时应以当前主题蓝图为主，避免继承上一轮选中主题的算力链卡口。",
            )
        )
    if missing_terms:
        findings.append(
            _finding(
                "P2",
                "缺少主题质量关键词",
                "缺少: " + "、".join(missing_terms[:12]),
                "按主题门槛补齐瓶颈、估值、财务、订单/产能/客户认证、反证和证据强度等要素。",
            )
        )
    if "## 附录 · Loop 证据增量日志" in text:
        findings.append(
            _finding(
                "P1",
                "最终报告混入 Loop 证据日志",
                "canonical report.md 中出现 Loop 证据增量日志。",
                "将过程日志迁移到 report_change_log.md，保持最终报告可读。",
            )
        )
    if any(token in text for token in ("/Users/", "data/raw/", "payload", "TradingAgents")):
        findings.append(
            _finding(
                "P2",
                "最终报告泄露运行时细节",
                "正文包含本地路径、payload 或内部 provider 名称。",
                "保留来源口径和证据强度，不暴露运行时路径或内部编排细节。",
            )
        )
    if "核心标的K线结构" in text:
        findings.append(
            _finding(
                "P1",
                "K线分析仍按核心/龙头口径呈现",
                "正文出现 `核心标的K线结构`。",
                "改为 `现阶段买入候选K线结构`，并确保候选来自交易决策和风险收益比门槛。",
            )
        )
    if "建议买点" in text and "等待买入触发" not in text and "paper_candidate" not in text:
        findings.append(
            _finding(
                "P2",
                "买点纪律证据不足",
                "正文出现建议买点，但没有看到等待触发或显式买入候选语义。",
                "只对现阶段适合买入的股票写支撑/压力买点；其它股票统一写等待买入触发。",
            )
        )
    forbidden_reader_terms = [term for term in _READER_FACING_FORBIDDEN_TERMS if term in text]
    if forbidden_reader_terms:
        findings.append(
            _finding(
                "P2",
                "读者报告混入数据适配器日志",
                "命中: " + "、".join(forbidden_reader_terms[:8]),
                "将适配器调用、健康检查、失败端点和行数统计移到 source_data.json 或 runs/ 调试产物。",
            )
        )

    has_company_mapping_context = _mentions_any(
        text,
        (
            "A股公司映射",
            "A股可交易标的",
            "标的分层",
            "公司映射",
            "核心地位判断",
        ),
    )
    if has_company_mapping_context and not _has_table_columns(text, _COMPANY_MAPPING_COLUMNS):
        findings.append(
            _finding(
                "P1",
                "缺少A股九列公司映射表",
                "报告讨论了 A 股标的或公司映射，但没有出现 canonical 9-column mapping table。",
                "按 industry-chain-analysis/a-share-screening 统一使用: 公司、代码、环节、细分领域、产业占比/暴露度、核心技术/产品、卡脖子相关性、环节地位、证据与备注。",
            )
        )

    has_value_distribution_context = _mentions_any(
        text,
        (
            "产业链核心环节价值分布",
            "价值分布",
            "BOM成本",
            "BOM 成本",
            "卡口",
            "瓶颈",
        ),
    )
    if has_value_distribution_context and not _has_table_columns(text, _VALUE_DISTRIBUTION_COLUMNS, min_matches=6):
        findings.append(
            _finding(
                "P2",
                "缺少核心环节价值分布表",
                "报告涉及价值分布、BOM 或瓶颈卡口，但未看到链路级价值分布表。",
                "在公司映射前补链路级表: 环节、关键产品、成本/价值占比、壁垒、卡脖子程度、代表公司、环节地位、证据口径。",
            )
        )

    if _mentions_any(text, ("瓶颈", "卡口", "卡脖子")):
        missing_standards = [standard for standard in _BOTTLENECK_STANDARDS if standard not in text]
        if missing_standards:
            findings.append(
                _finding(
                    "P2",
                    "瓶颈判断缺少四标准校验",
                    "缺少: " + "、".join(missing_standards),
                    "对候选卡口补齐不可替代、供给刚性、寡头垄断、机构低配四项判断；少于三项满足时降级为普通受益环节。",
                )
            )

    if _mentions_any(text, ("投资机会", "卡口", "瓶颈", "强命题")) and not _mentions_any(
        text, ("反证", "失效条件", "退出条件", "无效信号")
    ):
        findings.append(
            _finding(
                "P1",
                "缺少反证退出条件",
                "报告提出投资机会或瓶颈命题，但没有明确反证/失效/退出语义。",
                "为每条强命题补替代路线、客户切换、产能过剩、毛利压缩、订单不兑现等可观察退出条件。",
            )
        )

    if "数据来源与证据强度" in text and not _has_table_columns(text, _SOURCE_SUMMARY_COLUMNS, min_matches=4):
        findings.append(
            _finding(
                "P2",
                "证据强度缺少 claim-level 来源表",
                "报告有数据来源与证据强度章节，但没有出现 `结论/数据、来源、日期、置信度` 表。",
                "用 claim-level 来源表替代原始适配器日志，标清 High/Medium/Low 证据强度和待核验事项。",
            )
        )

    metrics = {
        "char_count": len(text),
        "image_count": len(images),
        "missing_image_count": len(missing_images),
        "todo_count": todo_count,
        "pending_collect_count": pending_collect_count,
        "missing_sections": missing_sections,
        "missing_terms": missing_terms,
        "has_company_mapping_table": _has_table_columns(text, _COMPANY_MAPPING_COLUMNS),
        "has_value_distribution_table": _has_table_columns(text, _VALUE_DISTRIBUTION_COLUMNS, min_matches=6),
        "has_source_summary_table": _has_table_columns(text, _SOURCE_SUMMARY_COLUMNS, min_matches=4),
    }
    return findings, metrics


def review_report_text(
    *,
    root: Path,
    text: str,
    report_path: Path | None,
    theme_key: str | None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the deterministic report review without writing artifacts."""
    findings, metrics = _review_text_against_policy(
        root=root,
        text=text,
        report_path=report_path,
        theme_key=theme_key,
        policy=policy if policy is not None else _theme_policy(root, theme_key),
    )
    p1 = sum(1 for finding in findings if finding.get("priority") == "P1")
    p2 = sum(1 for finding in findings if finding.get("priority") == "P2")
    return {
        "status": "pass" if p1 == 0 and p2 <= 2 else "needs_improvement",
        "findings": findings,
        "metrics": metrics,
        "summary": {
            "p1": p1,
            "p2": p2,
            "finding_count": len(findings),
        },
    }


def build_report_review(
    *,
    root: Path,
    payload: dict[str, Any],
    theme_key: str | None,
    report_path: Path | None,
    draft_path: Path | None,
    artifacts_dir: Path,
) -> dict[str, Any]:
    """Review every generated theme report with architecture-aware local rules.

    This agent is intentionally deterministic and repository-local so it can run
    in every loop. It reviews both the generated cycle draft and the canonical
    report that route_cycle_reports will refine, then persists JSON/Markdown
    artifacts under the cycle directory.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    policy = _theme_policy(root, theme_key)
    targets = []
    if draft_path is not None and draft_path.exists():
        targets.append(("draft", draft_path))
    if report_path is not None and report_path.exists():
        targets.append(("canonical", report_path))
    if not targets and report_path is not None:
        targets.append(("canonical", report_path))

    reviews: list[dict[str, Any]] = []
    all_findings: list[dict[str, str]] = []
    for kind, path in targets:
        text = _read_text(path)
        review = review_report_text(
            root=root,
            text=text,
            report_path=path,
            theme_key=theme_key,
            policy=policy,
        )
        findings = review["findings"]
        metrics = review["metrics"]
        for finding in findings:
            finding = dict(finding)
            finding["target"] = kind
            finding["path"] = _rel(root, path)
            all_findings.append(finding)
        reviews.append({"target": kind, "path": _rel(root, path), "metrics": metrics, "findings": findings})

    p1 = sum(1 for finding in all_findings if finding.get("priority") == "P1")
    p2 = sum(1 for finding in all_findings if finding.get("priority") == "P2")
    status = "pass" if p1 == 0 and p2 <= 2 else "needs_improvement"
    result = {
        "review_type": "architecture_aware_report_review",
        "agent_provider": "deterministic_report_review_agent",
        "status": status,
        "theme_key": theme_key,
        "generated_at": _now_iso(),
        "architecture_context_files": list(_ARCHITECTURE_CONTEXT_FILES),
        "architecture_context_excerpt": _architecture_context(root),
        "targets": reviews,
        "findings": all_findings[:24],
        "summary": {
            "p1": p1,
            "p2": p2,
            "finding_count": len(all_findings),
            "recommendation": "继续吸收更强报告片段并补硬事实/K线候选纪律。" if status != "pass" else "当前报告通过本地架构与质量审查。",
        },
        "state_mutation_allowed": False,
        "payload_ref": {
            "run_id": payload.get("run_id"),
            "cycle": payload.get("cycle"),
            "finished_at": payload.get("finished_at"),
        },
    }
    (artifacts_dir / "report-review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Report Review Agent",
        "",
        f"- status: {status}",
        f"- theme: {theme_key or 'unknown'}",
        f"- findings: P1={p1}, P2={p2}, total={len(all_findings)}",
        "",
    ]
    for finding in all_findings[:12]:
        lines.append(f"- [{finding['priority']}] {finding['target']} {finding['title']}: {finding['recommendation']}")
    (artifacts_dir / "report-review.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return result
