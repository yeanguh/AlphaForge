from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CURATION_HEADER = "## 滚动修订记录"
# daily/latest-full-loop.md 已从"最终报告"降级为增量 inbox / 研究日志:
# 仅沉淀每轮原始增量流水,最终研究资产以 reports/themes|stocks|weekly/ 为准。
INBOX_BANNER = (
    "> ⚠️ 本文件是**增量 inbox / 研究日志**,非最终报告。\n"
    "> 每轮 loop 的原始增量在此流水沉淀;最终研究资产请见 "
    "`reports/themes/<theme>/`(canonical 持续沉淀)、`reports/stocks/<symbol>/`、`reports/weekly/`。\n"
)


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return str(value)


def _snippet(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _unique_lines(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        if line and line not in seen:
            seen.add(line)
            result.append(line)
    return result


def _candidate_strength(payload: dict[str, Any]) -> int:
    pipeline = payload.get("research_pipeline", {})
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    score = 0
    score += min(len(payload.get("evidence_ids", []) or []), 20)
    score += min(len(payload.get("industry_reports", []) or []), 10)
    score += min(len(payload.get("news", {}).get("headlines", []) or []), 10)
    score += 5 if payload.get("agent_review", {}).get("roles") else 0
    score += 5 if pipeline.get("selected_industry_chain", {}).get("company_mapping") else 0
    score += 5 if pipeline.get("trade_decision_engine", {}).get("decisions") else 0
    score -= min(len(payload.get("errors", []) or []) * 4, 20)
    return max(score, 0)


def _increment_lines(payload: dict[str, Any], issues: list[str]) -> list[str]:
    lines: list[str] = []
    quotes = payload.get("a_share_quotes", []) if isinstance(payload.get("a_share_quotes"), list) else []
    if quotes:
        sample = "；".join(
            f"{item.get('name') or item.get('symbol')} {_fmt_pct(item.get('change_pct'))}" for item in quotes[:3]
        )
        lines.append(f"- 市场样本更新：{sample}。")

    chain = payload.get("research_pipeline", {}).get("selected_industry_chain", {})
    if isinstance(chain, dict) and chain.get("selected_theme"):
        lines.append(
            f"- 主线判断更新：当前候选主题为 `{chain.get('selected_theme')}`，产业链分数 {chain.get('score', 'NA')}。"
        )
    for item in chain.get("bottleneck_candidates", [])[:3] if isinstance(chain, dict) else []:
        if isinstance(item, dict):
            lines.append(
                f"- 卡口候选补强：{_snippet(item.get('link'))}，代表公司 {_snippet(item.get('companies'))}，失效条件 {_snippet(item.get('invalidation'))}。"
            )

    reports = payload.get("industry_reports", []) if isinstance(payload.get("industry_reports"), list) else []
    for item in reports[:4]:
        if isinstance(item, dict) and item.get("title"):
            lines.append(
                f"- 研报证据更新：{item.get('org') or '公开研报'}《{_snippet(item.get('title'), 80)}》。"
            )

    headlines = payload.get("news", {}).get("headlines", [])
    headlines = headlines if isinstance(headlines, list) else []
    for item in headlines[:4]:
        if isinstance(item, dict) and item.get("title"):
            lines.append(
                f"- 公开资讯更新：{item.get('source') or '公开来源'}《{_snippet(item.get('title'), 80)}》。"
            )

    review = payload.get("agent_review", {})
    if isinstance(review, dict):
        reason = review.get("reason")
        if reason:
            lines.append(f"- Agent 复核更新：{_snippet(reason, 160)}")
        next_actions = review.get("next_actions", [])
        if isinstance(next_actions, list) and next_actions:
            lines.append("- 下一轮优先验证：" + "；".join(_snippet(item, 80) for item in next_actions[:4]) + "。")

    if issues:
        lines.append("- 本轮限制：存在 `" + "`, `".join(issues[:6]) + "`，仅作为增量线索，不替换主报告。")
    return _unique_lines(lines)


def build_increment_block(payload: dict[str, Any], issues: list[str], candidate_report_path: Path | None = None) -> str:
    run_id = str(payload.get("run_id") or "unknown-run")
    cycle = str(payload.get("cycle") or "unknown-cycle")
    marker = f"<!-- research-os-curation:{run_id}:{cycle} -->"
    generated_at = datetime.now(timezone.utc).isoformat()
    strength = _candidate_strength(payload)
    lines = [
        marker,
        f"### {generated_at} · {run_id} cycle {cycle}",
        "",
        f"- 候选增量强度：{strength}；本轮状态：`{payload.get('status')}`。",
    ]
    lines.extend(_increment_lines(payload, issues))
    return "\n".join(lines).rstrip() + "\n"


def update_rolling_report(
    *,
    root: Path,
    payload: dict[str, Any],
    candidate_report_path: Path,
    latest_report_path: Path,
    issues: list[str],
) -> dict[str, Any]:
    latest_report_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_text = candidate_report_path.read_text(encoding="utf-8") if candidate_report_path.exists() else ""
    relative_candidate = candidate_report_path.resolve().relative_to(root.resolve())
    block = build_increment_block(payload, issues, relative_candidate)
    marker = block.splitlines()[0]

    if latest_report_path.exists():
        current = latest_report_path.read_text(encoding="utf-8")
        # 降级横幅补写:老文件(降级前建立、开头仍像最终报告)自动在顶部补 inbox 提示,
        # 使其与新建文件语义一致——避免后续 agent 误把 inbox 当最终报告。
        banner_backfilled = False
        if "增量 inbox / 研究日志" not in current:
            current = INBOX_BANNER + "\n\n" + current.lstrip()
            banner_backfilled = True
        if marker in current:
            if banner_backfilled:
                latest_report_path.write_text(current, encoding="utf-8")
                return {"status": "merged", "mode": "banner_backfill_only", "candidate": str(relative_candidate)}
            return {"status": "skipped", "reason": "increment already present", "candidate": str(relative_candidate)}
        if CURATION_HEADER not in current:
            current = current.rstrip() + "\n\n" + CURATION_HEADER + "\n\n"
        updated = current.rstrip() + "\n\n" + block
        latest_report_path.write_text(updated, encoding="utf-8")
        return {"status": "merged", "mode": "append_increment", "banner_backfilled": banner_backfilled, "candidate": str(relative_candidate)}

    if candidate_text:
        latest_report_path.write_text(INBOX_BANNER + "\n\n" + candidate_text.rstrip() + "\n\n" + CURATION_HEADER + "\n\n" + block, encoding="utf-8")
        return {"status": "seeded", "mode": "candidate_plus_increment", "candidate": str(relative_candidate)}

    latest_report_path.write_text("# Research OS 增量 inbox / 研究日志\n\n" + INBOX_BANNER + "\n\n" + CURATION_HEADER + "\n\n" + block, encoding="utf-8")
    return {"status": "seeded", "mode": "increment_only", "candidate": str(relative_candidate)}
