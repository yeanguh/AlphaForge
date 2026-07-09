from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


VALID_AGENT_MODES = {"deterministic", "codex", "claude", "auto"}


def build_deterministic_review(data: dict[str, Any]) -> dict[str, Any]:
    quotes = data.get("a_share_quotes", [])
    charts = data.get("global_charts", [])
    industry = data.get("industry_analysis", {})
    headlines = data.get("news", {}).get("headlines", [])

    positive = []
    negative = []
    risk = []
    policy = []
    hot_money = []

    for quote in quotes:
        if quote.get("change_pct") is not None and quote["change_pct"] > 0:
            positive.append(f"{quote.get('name')}上涨 {quote.get('change_pct')}%，短线风险偏好尚可。")
        if quote.get("valuation_band") == "high":
            negative.append(f"{quote.get('name')}估值处于 high band，需要更强业绩证据。")
        if quote.get("pb") and quote["pb"] > 8:
            risk.append(f"{quote.get('name')}PB={quote.get('pb')}，安全边际需要复核。")

    for chart in charts:
        if chart.get("change_pct") is not None and chart["change_pct"] < -1:
            negative.append(f"{chart.get('symbol')} 5日样本最新变动偏弱，可能压制跨市场情绪。")

    for item in industry.get("top_theme_buckets", [])[:3]:
        positive.append(f"主题桶 {item[0]} 在研报/资讯中出现 {item[1]} 次，值得进入产业链验证。")

    for headline in headlines[:3]:
        policy.append(f"资讯跟踪：{headline.get('source')} - {headline.get('title')}")

    if industry.get("catalysts"):
        hot_money.append("行业研报催化已形成候选池，但需要成交量、资金流和A股暴露二次验证。")

    decision = "needs_more_evidence"
    if positive and not negative:
        decision = "watchlist_candidate"
    elif negative and risk:
        decision = "hold_or_reject"

    return {
        "review_type": "deterministic_tradingagents_style_review",
        "agent_provider": "deterministic",
        "roles": {
            "bull": positive[:6],
            "bear": negative[:6],
            "risk": risk[:6],
            "policy_news": policy[:6],
            "hot_money": hot_money[:6],
        },
        "decision": decision,
        "reason": "本地确定性评审用于验证 loop 输出完整性；正式投委会式 LLM debate 后续通过 TradingAgents-astock adapter 接入。",
    }


def _compact_input(data: dict[str, Any]) -> dict[str, Any]:
    pipeline = data.get("research_pipeline", {})
    return {
        "a_share_quotes": data.get("a_share_quotes", [])[:5],
        "global_charts": data.get("global_charts", [])[:5],
        "news_headlines": data.get("news", {}).get("headlines", [])[:12],
        "industry_reports": data.get("industry_reports", [])[:12],
        "industry_analysis": data.get("industry_analysis", {}),
        "research_pipeline": {
            "hotspot_scoring": pipeline.get("hotspot_scoring", {}),
            "selected_industry_chain": pipeline.get("selected_industry_chain", {}),
            "stock_analyzer": pipeline.get("stock_analyzer", [])[:5],
            "trade_decision_engine": pipeline.get("trade_decision_engine", {}),
        },
    }


def build_agent_prompt(data: dict[str, Any]) -> str:
    compact = _compact_input(data)
    return (
        "你是 Research OS 的本地投研 Agent。请阅读下面的结构化市场数据、资讯、行业研报和产业链分析，"
        "做一轮归纳评审。只输出 JSON，不要 Markdown，不要解释 JSON 之外的文本。\n\n"
        "JSON schema:\n"
        "{\n"
        '  "review_type": "codex_agent_summary",\n'
        '  "agent_provider": "codex|claude",\n'
        '  "roles": {\n'
        '    "bull": ["多头证据"],\n'
        '    "bear": ["空头/反证"],\n'
        '    "risk": ["风险"],\n'
        '    "policy_news": ["政策/新闻归纳"],\n'
        '    "hot_money": ["短线资金/情绪观察"]\n'
        "  },\n"
        '  "decision": "watchlist_candidate|needs_more_evidence|hold_or_reject",\n'
        '  "reason": "一句话说明",\n'
        '  "next_actions": ["下一轮要验证的事项"]\n'
        "}\n\n"
        "约束：这是 research_only，不给真实交易指令；必须引用输入里的证据，不要编造。\n\n"
        f"INPUT_JSON:\n{json.dumps(compact, ensure_ascii=False, indent=2)}\n"
    )


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty agent output")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("agent output does not contain a JSON object")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("agent output JSON is not an object")
    return data


def _normalize_review(raw: dict[str, Any], provider: str) -> dict[str, Any]:
    roles = raw.get("roles") if isinstance(raw.get("roles"), dict) else {}
    normalized_roles: dict[str, list[str]] = {}
    for role in ("bull", "bear", "risk", "policy_news", "hot_money"):
        values = roles.get(role, [])
        if isinstance(values, str):
            values = [values]
        normalized_roles[role] = [str(item) for item in values[:8]] if isinstance(values, list) else []
    decision = raw.get("decision")
    if decision not in {"watchlist_candidate", "needs_more_evidence", "hold_or_reject"}:
        decision = "needs_more_evidence"
    next_actions = raw.get("next_actions", [])
    if isinstance(next_actions, str):
        next_actions = [next_actions]
    if not isinstance(next_actions, list):
        next_actions = []
    return {
        "review_type": f"{provider}_agent_summary",
        "agent_provider": provider,
        "roles": normalized_roles,
        "decision": decision,
        "reason": str(raw.get("reason") or "agent review completed"),
        "next_actions": [str(item) for item in next_actions[:8]],
    }


def _run_codex(prompt: str, root: Path, artifacts_dir: Path, timeout_seconds: int) -> dict[str, Any]:
    if shutil.which("codex") is None:
        raise RuntimeError("codex CLI not found")
    schema = root / "config" / "agent_review_schema.json"
    output_path = artifacts_dir / "codex-review.raw.txt"
    cmd = [
        "codex",
        "exec",
        "--cd",
        str(root),
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--output-last-message",
        str(output_path),
    ]
    if schema.exists():
        cmd.extend(["--output-schema", str(schema)])
    cmd.append("-")
    proc = subprocess.run(cmd, input=prompt, cwd=root, text=True, capture_output=True, timeout=timeout_seconds)
    raw = output_path.read_text(encoding="utf-8") if output_path.exists() else proc.stdout
    (artifacts_dir / "codex-review.stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (artifacts_dir / "codex-review.stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"codex exec failed rc={proc.returncode}: {proc.stderr[-1000:]}")
    return _normalize_review(_extract_json(raw), "codex")


def _run_claude(prompt: str, root: Path, artifacts_dir: Path, timeout_seconds: int) -> dict[str, Any]:
    if shutil.which("claude") is None:
        raise RuntimeError("claude CLI not found")
    cmd = [
        "claude",
        "--print",
        "--output-format",
        "text",
        "--add-dir",
        str(root),
        "--system-prompt",
        "你是 Research OS 的本地投研 Agent。只输出用户要求的 JSON。",
        prompt,
    ]
    proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=timeout_seconds)
    (artifacts_dir / "claude-review.stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (artifacts_dir / "claude-review.stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"claude --print failed rc={proc.returncode}: {proc.stderr[-1000:]}")
    return _normalize_review(_extract_json(proc.stdout), "claude")


def build_review(
    data: dict[str, Any],
    *,
    mode: str | None = None,
    root: Path | None = None,
    artifacts_dir: Path | None = None,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    selected = mode or os.environ.get("RESEARCH_OS_AGENT_MODE", "deterministic")
    if selected not in VALID_AGENT_MODES:
        raise ValueError(f"unknown agent mode: {selected}")
    if selected == "deterministic":
        return build_deterministic_review(data)

    root = root or Path.cwd()
    artifacts_dir = artifacts_dir or root / "runs" / "agent-review"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_agent_prompt(data)
    (artifacts_dir / "agent-review.prompt.txt").write_text(prompt, encoding="utf-8")

    errors: list[str] = []
    providers = ["codex", "claude"] if selected == "auto" else [selected]
    for provider in providers:
        try:
            if provider == "codex":
                review = _run_codex(prompt, root, artifacts_dir, timeout_seconds)
            else:
                review = _run_claude(prompt, root, artifacts_dir, timeout_seconds)
            review["artifact_dir"] = str(artifacts_dir)
            return review
        except Exception as exc:
            errors.append(f"{provider}: {exc!r}")

    review = build_deterministic_review(data)
    review["review_type"] = "fallback_deterministic_agent_summary"
    review["agent_provider"] = "deterministic_fallback"
    review["agent_errors"] = errors
    review["artifact_dir"] = str(artifacts_dir)
    return review
