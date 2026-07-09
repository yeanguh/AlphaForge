from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from loop_os.schemas.provider import ProviderResult


ROOT = Path(__file__).resolve().parents[2]
PROVIDER_NAME = "wen-cai"
SKILL_VERSION = "1.0.0"
SKILL_DIR_CANDIDATES = sorted((ROOT / "skills").glob("wen-cai*"))
SKILL_DIR = SKILL_DIR_CANDIDATES[0] if SKILL_DIR_CANDIDATES else ROOT / "skills" / "wen-cai"
CLI = SKILL_DIR / "scripts" / "cli.py"
BASE_URL = "https://openapi.iwencai.com"
COMPREHENSIVE_TYPES = {"report": "report", "announcement": "announcement", "news": "news"}


def is_configured() -> bool:
    return bool(os.environ.get("IWENCAI_API_KEY"))


def skill_available() -> bool:
    return CLI.exists() and (SKILL_DIR / "SKILL.md").exists()


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['IWENCAI_API_KEY']}",
        "Content-Type": "application/json",
        "X-Claw-Call-Type": "normal",
        "X-Claw-Skill-Id": "wen-cai",
        "X-Claw-Skill-Version": SKILL_VERSION,
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }


def _post(path: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    base_url = os.environ.get("IWENCAI_BASE_URL", BASE_URL).rstrip("/")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=body,
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {"_http_error": exc.code, "_error_body": raw}
    except urllib.error.URLError as exc:
        return {"_network_error": str(exc.reason)}


def query(qtype: str, query_text: str, *, page: int = 1, limit: int = 10, timeout: int = 45) -> dict[str, Any]:
    if not skill_available():
        return {
            "status": "skipped",
            "reason": "wen-cai skill CLI missing",
            "qtype": qtype,
            "query": query_text,
            "skill_dir": str(SKILL_DIR),
        }
    if not is_configured():
        return {
            "status": "skipped",
            "reason": "IWENCAI_API_KEY missing in current process",
            "qtype": qtype,
            "query": query_text,
            "skill_dir": str(SKILL_DIR),
        }

    if qtype in COMPREHENSIVE_TYPES:
        payload = _post(
            "/v1/comprehensive/search",
            {
                "channels": [COMPREHENSIVE_TYPES[qtype]],
                "app_id": "AIME_SKILL",
                "query": query_text,
                "size": limit,
            },
            timeout=timeout,
        )
    else:
        payload = _post(
            "/v1/query2data",
            {
                "query": query_text,
                "page": str(page),
                "limit": str(limit),
                "is_cache": "1",
                "expand_index": "true",
            },
            timeout=timeout,
        )
    ok = not any(key in payload for key in ("_http_error", "_network_error")) and payload.get("status_code", 0) in (0, "0")
    return {
        "status": "ok" if ok else "error",
        "qtype": qtype,
        "query": query_text,
        "returncode": 0 if ok else 1,
        "stdout": payload,
        "stderr": payload.get("_error_body") or payload.get("_network_error") or payload.get("status_msg", ""),
        "skill_dir": str(SKILL_DIR),
    }


def fetch_research_enrichment(symbols: dict[str, str]) -> dict[str, Any]:
    queries: list[tuple[str, str, str, int]] = [
        ("sector_hotspots", "sector-select", "人形机器人概念板块 今日涨跌幅 主力资金净流入 市盈率", 10),
        ("robotics_reports", "report", "人形机器人 产业链 核心零部件 研报 投资评级", 8),
        ("robotics_news", "news", "人形机器人 产业链 最新 政策 订单 量产", 8),
    ]
    for symbol, name in symbols.items():
        queries.extend(
            [
                (f"{symbol}_business", "business", f"{name} 主营业务 主要客户 供应商 重大合同 机器人", 6),
                (f"{symbol}_rating", "rating", f"{name} 机构评级 目标价 业绩预测", 6),
                (f"{symbol}_event", "event", f"{name} 机构调研 重大事件 业绩预告 机器人", 6),
                (f"{symbol}_report", "report", f"{name} 机器人 研报 投资评级 目标价", 5),
            ]
        )
    results = {key: query(qtype, text, limit=limit) for key, qtype, text, limit in queries}
    enabled = any(item.get("status") == "ok" for item in results.values())
    skipped = all(item.get("status") == "skipped" for item in results.values())
    return {
        "provider": PROVIDER_NAME,
        "skill_dir": str(SKILL_DIR),
        "configured": is_configured(),
        "enabled": enabled,
        "skipped": skipped,
        "results": results,
    }


def _result_count(item: dict[str, Any]) -> int:
    stdout = item.get("stdout")
    if not isinstance(stdout, dict):
        return 0
    if isinstance(stdout.get("datas"), list):
        return len(stdout["datas"])
    if isinstance(stdout.get("data"), list):
        return len(stdout["data"])
    return 0


def summarize_enrichment(enrichment: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, item in enrichment.get("results", {}).items():
        if not isinstance(item, dict):
            continue
        stdout = item.get("stdout") if isinstance(item.get("stdout"), dict) else {}
        samples = stdout.get("datas") if isinstance(stdout.get("datas"), list) else stdout.get("data")
        sample = samples[0] if isinstance(samples, list) and samples else {}
        fields = list(sample.keys())[:8] if isinstance(sample, dict) else []
        title = sample.get("title") or sample.get("股票简称") or sample.get("证券简称") or sample.get("公司简称") if isinstance(sample, dict) else ""
        rows.append(
            {
                "key": key,
                "status": item.get("status"),
                "qtype": item.get("qtype"),
                "query": item.get("query"),
                "count": _result_count(item),
                "sample": title,
                "fields": fields,
                "reason": item.get("reason") or item.get("stderr", ""),
            }
        )
    return rows


def smoke(live: bool = False) -> ProviderResult:
    if not skill_available():
        return ProviderResult(PROVIDER_NAME, "error", "wen-cai skill CLI missing", errors=[str(CLI)])
    if not live:
        return ProviderResult(
            PROVIDER_NAME,
            "ok",
            "wen-cai skill readable; live calls require IWENCAI_API_KEY",
            {"path": str(SKILL_DIR), "configured": is_configured()},
        )
    if not is_configured():
        return ProviderResult(
            PROVIDER_NAME,
            "error",
            "IWENCAI_API_KEY missing in current process",
            {"path": str(SKILL_DIR)},
            errors=["export IWENCAI_API_KEY=... before live smoke"],
        )
    result = query("report", "人形机器人 研报", limit=1, timeout=45)
    if result.get("status") == "ok":
        return ProviderResult(PROVIDER_NAME, "ok", "wen-cai live query succeeded", {"sample": result})
    return ProviderResult(PROVIDER_NAME, "error", "wen-cai live query failed", {"sample": result}, errors=[str(result.get("stderr"))])
