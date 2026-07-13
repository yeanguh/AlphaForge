from __future__ import annotations

import hashlib
import os
import re
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(os.environ.get("RESEARCH_OS_PDF_CACHE_DIR", ROOT / "data" / "local" / "pdf-text")).expanduser()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

HARD_FACT_TERMS = (
    "订单",
    "客户",
    "认证",
    "定点",
    "中标",
    "交付",
    "出货",
    "涨价",
    "提价",
    "价格",
    "ASP",
    "产能",
    "扩产",
    "投产",
    "利用率",
    "良率",
    "交期",
    "爬坡",
    "收入占比",
    "毛利率",
    "营收",
    "净利润",
    "归母净利润",
    "资本开支",
    "capex",
)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|亿元|亿|万元|万|元|倍|G|T|P|MW|GW|台|套)")


def _cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _pdf_path(url: str) -> Path:
    return CACHE_DIR / f"{_cache_key(url)}.pdf"


def _text_path(url: str) -> Path:
    return CACHE_DIR / f"{_cache_key(url)}.txt"


def _meta_path(url: str) -> Path:
    return CACHE_DIR / f"{_cache_key(url)}.meta"


def download_pdf(url: str, *, timeout: int = 20) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _pdf_path(url)
    if path.exists() and path.stat().st_size > 1024:
        return path
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Referer": "https://pdf.dfcfw.com/",
            "Accept": "application/pdf,*/*",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    if len(raw) < 1024 or not raw[:8].startswith(b"%PDF"):
        raise RuntimeError("downloaded content is not a valid PDF")
    path.write_bytes(raw)
    return path


def extract_text_from_pdf(path: Path, *, max_pages: int = 8, max_chars: int = 24000) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("pypdf is not installed; PDF text extraction unavailable") from exc

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
        if sum(len(x) for x in chunks) >= max_chars:
            break
    text = "\n".join(chunks)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


def cached_or_extract_text(url: str, *, live: bool = False, timeout: int = 20) -> tuple[str, str]:
    """Return (text, status). status is cached/extracted/skipped/error:..."""
    if not url:
        return "", "skipped:no_url"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    text_path = _text_path(url)
    if text_path.exists() and text_path.stat().st_size > 0:
        return text_path.read_text(encoding="utf-8", errors="replace"), "cached"
    if not live:
        return "", "skipped:not_cached"
    try:
        pdf_path = download_pdf(url, timeout=timeout)
        text = extract_text_from_pdf(pdf_path)
        if text.strip():
            text_path.write_text(text, encoding="utf-8")
            _meta_path(url).write_text(url, encoding="utf-8")
            return text, "extracted"
        return "", "error:no_text"
    except Exception as exc:  # noqa: BLE001
        return "", f"error:{type(exc).__name__}:{exc}"


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[。；;.!！?？])", normalized)
    out: list[str] = []
    for part in parts:
        clean = " ".join(part.split())
        if 18 <= len(clean) <= 180:
            out.append(clean)
        elif len(clean) > 180:
            for term in HARD_FACT_TERMS:
                idx = clean.find(term)
                if idx >= 0:
                    start = max(0, idx - 70)
                    end = min(len(clean), idx + 110)
                    out.append(clean[start:end].strip(" ，；。"))
                    break
    return out


def _is_readable_fact(sent: str) -> bool:
    if not sent or any(
        marker in sent
        for marker in (
            "[Table_",
            "Table_",
            "风险提示",
            "免责声明",
            "证券投资咨询业务",
            "请务必阅读",
            "投资评级说明",
            "免责条款",
            "不会因接收人",
            "不构成",
            "投资建议",
            "证券或投资标的",
            "价格、价值及投资收入",
        )
    ):
        return False
    if re.search(r"\d+\.$", sent):
        return False
    if len(re.findall(r"[\u4e00-\u9fff]", sent)) < 8:
        return False
    return True


def extract_hard_fact_snippets(text: str, *, limit: int = 6) -> list[str]:
    scored: list[tuple[int, str]] = []
    for sent in _sentences(text):
        if not _is_readable_fact(sent):
            continue
        term_hits = sum(1 for term in HARD_FACT_TERMS if term in sent)
        if not term_hits:
            continue
        number_hits = len(NUMBER_RE.findall(sent))
        score = term_hits * 3 + number_hits * 2
        if number_hits:
            scored.append((score, sent))
    if not scored:
        for sent in _sentences(text):
            if not _is_readable_fact(sent):
                continue
            term_hits = sum(1 for term in HARD_FACT_TERMS if term in sent)
            if term_hits:
                scored.append((term_hits, sent))
    deduped: list[str] = []
    seen: set[str] = set()
    for _, sent in sorted(scored, key=lambda x: x[0], reverse=True):
        key = sent[:48]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(sent)
        if len(deduped) >= limit:
            break
    return deduped


def enrich_pdf_facts(
    rows: list[dict[str, Any]],
    *,
    live: bool = False,
    max_docs: int = 6,
    snippets_per_doc: int = 3,
    include_terms: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Extract short hard-fact snippets from report PDFs.

    The caller controls live network use. Without live=True, only cached text is
    used so normal loop runs remain bounded and deterministic.
    """
    facts: list[dict[str, Any]] = []
    tried = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "")
        if include_terms and not any(term in title for term in include_terms):
            continue
        url = str(row.get("pdf_url") or row.get("url") or "")
        if not url.lower().endswith(".pdf"):
            continue
        tried += 1
        text, status = cached_or_extract_text(url, live=live)
        if text:
            for snippet in extract_hard_fact_snippets(text, limit=snippets_per_doc):
                facts.append(
                    {
                        "title": row.get("title") or "",
                        "source": row.get("org") or row.get("source") or "PDF正文",
                        "date": row.get("publish_date") or row.get("date") or "",
                        "pdf_url": url,
                        "snippet": snippet,
                        "status": status,
                        "info_code": row.get("info_code") or row.get("infoCode") or "",
                    }
                )
        else:
            facts.append(
                {
                    "title": row.get("title") or "",
                    "source": row.get("org") or row.get("source") or "PDF正文",
                    "date": row.get("publish_date") or row.get("date") or "",
                    "pdf_url": url,
                    "snippet": "",
                    "status": status,
                    "info_code": row.get("info_code") or row.get("infoCode") or "",
                }
            )
        if tried >= max_docs:
            break
    return facts
