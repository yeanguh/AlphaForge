from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


VALID_AGENT_MODES = {"deterministic", "codex", "claude", "openai_compatible", "auto"}


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


def _truncate_text(value: Any, max_chars: int = 240) -> Any:
    if not isinstance(value, str):
        return value
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1] + "…"


def _compact_records(records: Any, fields: tuple[str, ...], *, limit: int, max_chars: int = 240) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        return []
    compacted: list[dict[str, Any]] = []
    for record in records[:limit]:
        if not isinstance(record, dict):
            continue
        item = {}
        for field in fields:
            if field in record and record[field] is not None:
                item[field] = _truncate_text(record[field], max_chars=max_chars)
        compacted.append(item)
    return compacted


def _compact_stock_analyzer(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    compacted = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        compacted.append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "business_model": _truncate_text(item.get("business_model"), 180),
                "financial": item.get("financial"),
                "valuation": item.get("valuation"),
                "technical": item.get("technical"),
                "catalyst": item.get("catalyst", [])[:3] if isinstance(item.get("catalyst"), list) else item.get("catalyst"),
                "risk": item.get("risk", [])[:3] if isinstance(item.get("risk"), list) else item.get("risk"),
                "a_stock_data_coverage": item.get("a_stock_data_coverage"),
            }
        )
    return compacted


def _compact_selected_chain(chain: Any) -> dict[str, Any]:
    if not isinstance(chain, dict):
        return {}
    return {
        "stage": chain.get("stage"),
        "mode": chain.get("mode"),
        "selected_theme": chain.get("selected_theme"),
        "score": chain.get("score"),
        "chain_map": chain.get("chain_map"),
        "core_value_distribution": chain.get("core_value_distribution", [])[:3]
        if isinstance(chain.get("core_value_distribution"), list)
        else [],
        "company_mapping": chain.get("company_mapping", [])[:5] if isinstance(chain.get("company_mapping"), list) else [],
        "bottleneck_candidates": chain.get("bottleneck_candidates", [])[:5]
        if isinstance(chain.get("bottleneck_candidates"), list)
        else [],
        "supporting_public_items": _compact_records(
            chain.get("supporting_public_items"),
            ("id", "kind", "title", "source", "industry", "published_at", "digest"),
            limit=5,
            max_chars=180,
        ),
        "next_verifications": chain.get("next_verifications", [])[:5] if isinstance(chain.get("next_verifications"), list) else [],
        "invalidation_triggers": chain.get("invalidation_triggers", [])[:5]
        if isinstance(chain.get("invalidation_triggers"), list)
        else [],
    }


def _compact_input(data: dict[str, Any]) -> dict[str, Any]:
    pipeline = data.get("research_pipeline", {})
    return {
        "a_share_quotes": _compact_records(
            data.get("a_share_quotes"),
            ("symbol", "name", "price", "change_pct", "pe", "pb", "valuation_band", "evidence_id"),
            limit=5,
        ),
        "global_charts": _compact_records(data.get("global_charts"), ("symbol", "change_pct", "evidence_id"), limit=5),
        "news_headlines": _compact_records(
            data.get("news", {}).get("headlines", []),
            ("source", "title", "published_at", "url", "evidence_id"),
            limit=12,
            max_chars=180,
        ),
        "industry_reports": _compact_records(
            data.get("industry_reports", []),
            ("title", "org", "industry_name", "rating", "publish_date", "url", "evidence_id"),
            limit=12,
            max_chars=180,
        ),
        "industry_analysis": data.get("industry_analysis", {}),
        "research_pipeline": {
            "hotspot_scoring": pipeline.get("hotspot_scoring", {}),
            "selected_industry_chain": _compact_selected_chain(pipeline.get("selected_industry_chain", {})),
            "stock_analyzer": _compact_stock_analyzer(pipeline.get("stock_analyzer", [])),
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


def _llm_config() -> tuple[str, str, str]:
    base_url = os.environ.get("BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("MODEL_NAME") or os.environ.get("OPENAI_MODEL")
    missing = [
        name
        for name, value in [
            ("BASE_URL/OPENAI_BASE_URL", base_url),
            ("API_KEY/OPENAI_API_KEY", api_key),
            ("MODEL_NAME/OPENAI_MODEL", model),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(f"missing OpenAI-compatible env: {', '.join(missing)}")
    return str(base_url).rstrip("/"), str(api_key), str(model)


def _run_openai_compatible(prompt: str, root: Path, artifacts_dir: Path, timeout_seconds: int) -> dict[str, Any]:
    base_url, api_key, model = _llm_config()
    url = f"{base_url}/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是 Research OS 的本地投研 Agent。只输出用户要求的 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": int(os.environ.get("OPENAI_MAX_TOKENS", "4096")),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    attempts = max(1, int(os.environ.get("OPENAI_RETRY_ATTEMPTS", "3")))
    retry_statuses = {429, 502, 503, 504}
    raw = ""
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="replace")
            (artifacts_dir / f"openai-compatible-review.stderr.attempt-{attempt}.txt").write_text(raw_error, encoding="utf-8")
            if exc.code not in retry_statuses or attempt >= attempts:
                (artifacts_dir / "openai-compatible-review.stderr.txt").write_text(raw_error, encoding="utf-8")
                raise RuntimeError(f"openai-compatible chat failed http={exc.code}: {raw_error[-1000:]}") from exc
        except urllib.error.URLError as exc:
            if attempt >= attempts:
                raise RuntimeError(f"openai-compatible chat network failed: {exc.reason}") from exc
        time.sleep(min(2 ** (attempt - 1), 8))

    (artifacts_dir / "openai-compatible-review.response.json").write_text(raw, encoding="utf-8")
    payload = json.loads(raw)
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("openai-compatible response missing choices")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("openai-compatible response missing message content")
    (artifacts_dir / "openai-compatible-review.raw.txt").write_text(content, encoding="utf-8")
    if not content.strip():
        finish_reason = choices[0].get("finish_reason") if isinstance(choices[0], dict) else None
        raise RuntimeError(f"openai-compatible response content empty; finish_reason={finish_reason}")
    return _normalize_review(_extract_json(content), "openai_compatible")


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
    providers = ["openai_compatible", "codex", "claude"] if selected == "auto" else [selected]
    for provider in providers:
        try:
            if provider == "codex":
                review = _run_codex(prompt, root, artifacts_dir, timeout_seconds)
            elif provider == "claude":
                review = _run_claude(prompt, root, artifacts_dir, timeout_seconds)
            else:
                review = _run_openai_compatible(prompt, root, artifacts_dir, timeout_seconds)
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
