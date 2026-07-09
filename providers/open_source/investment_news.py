from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from loop_os.schemas.provider import ProviderResult

from .http_utils import get_text


ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = ROOT / "external" / "investment-news"
SOURCES = SUBMODULE / "sources.json"


def _display_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _parse_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def _fetch_feed(source: dict) -> list[dict]:
    text = get_text(source["url"], timeout=14)
    root = ET.fromstring(text.encode("utf-8"))
    items: list[dict] = []
    for node in [e for e in root.iter() if _local(e.tag) in {"item", "entry"}]:
        title = ""
        url = ""
        raw_time = ""
        for child in node:
            tag = _local(child.tag)
            if tag == "title" and not title:
                title = (child.text or "").strip()
            elif tag == "link" and not url:
                url = child.get("href") or (child.text or "").strip()
            elif tag in {"pubDate", "published", "updated", "date"} and not raw_time:
                raw_time = (child.text or "").strip()
        if title:
            items.append({"title": title, "url": url, "published_at": _parse_time(raw_time), "source": source["name"]})
        if len(items) >= 3:
            break
    return items


def fetch_headlines(max_sources: int = 24, max_items: int = 24) -> dict:
    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    sources = cfg.get("sources", [])
    errors: list[str] = []
    headlines: list[dict] = []
    for source in sources[:max_sources]:
        try:
            headlines.extend(_fetch_feed(source))
        except Exception as exc:
            errors.append(f"{source.get('name')}: {exc!r}")
        if len(headlines) >= max_items:
            break
    return {
        "source_count": len(sources),
        "headlines": headlines[:max_items],
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def smoke(live: bool = False) -> ProviderResult:
    if not SUBMODULE.exists() or not SOURCES.exists():
        return ProviderResult("investment-news", "error", "submodule or sources.json missing", errors=[_display_path(SOURCES)])
    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    sources = cfg.get("sources", [])
    if not live:
        return ProviderResult(
            "investment-news",
            "ok",
            f"sources.json readable，配置源数量={len(sources)}",
            {"source_count": len(sources)},
        )

    fetched = fetch_headlines(max_sources=12, max_items=5)
    headlines = fetched["headlines"]
    errors = fetched["errors"]
    if not headlines:
        return ProviderResult("investment-news", "error", "资讯源抓取失败", {"source_count": len(sources)}, errors)
    return ProviderResult(
        "investment-news",
        "ok",
        f"资讯源抓取成功，样本 headlines={len(headlines)}",
        {"source_count": len(sources), "headlines": headlines[:5], "generated_at": datetime.now(timezone.utc).isoformat()},
        errors=errors[:5],
    )
