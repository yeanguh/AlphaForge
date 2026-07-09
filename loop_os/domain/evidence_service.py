from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loop_os.schemas.evidence import EvidenceCard


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def build_evidence_cards(cycle: int, payload: dict[str, Any]) -> list[EvidenceCard]:
    cards: list[EvidenceCard] = []

    for quote in payload.get("a_share_quotes", []):
        symbol = str(quote.get("symbol") or "")
        name = str(quote.get("name") or symbol)
        cards.append(
            EvidenceCard(
                id=_stable_id("ev-market-cn", symbol, str(payload.get("started_at")), str(cycle)),
                source_name="a-stock-data/tencent_finance",
                source_type="market_snapshot",
                title=f"A股行情快照：{symbol} {name}",
                freshness="intraday_or_latest_available",
                related_companies=[symbol],
                claims=[
                    f"{name} 最新价 {quote.get('price')}",
                    f"{name} PE {quote.get('pe')} PB {quote.get('pb')}",
                    f"{name} valuation_band={quote.get('valuation_band')}",
                ],
                raw=quote,
            )
        )

    for chart in payload.get("global_charts", []):
        symbol = str(chart.get("symbol") or "")
        cards.append(
            EvidenceCard(
                id=_stable_id("ev-market-global", symbol, str(payload.get("started_at")), str(cycle)),
                source_name="global-stock-data/yahoo_chart",
                source_type="global_market_snapshot",
                title=f"全球股票行情快照：{symbol}",
                freshness="intraday_or_latest_available",
                related_companies=[symbol],
                claims=[
                    f"{symbol} latest_close={chart.get('latest_close')}",
                    f"{symbol} change_pct={chart.get('change_pct')}",
                ],
                raw=chart,
            )
        )

    for headline in payload.get("news", {}).get("headlines", [])[:12]:
        title = str(headline.get("title") or "")
        url = headline.get("url")
        cards.append(
            EvidenceCard(
                id=_stable_id("ev-news", title, str(url)),
                source_name=str(headline.get("source") or "investment-news"),
                source_type="news",
                title=title,
                url=url,
                source_url=url,
                freshness=str(headline.get("published_at") or headline.get("date") or "latest_available"),
                claims=[title],
                raw=headline,
            )
        )

    for report in payload.get("industry_reports", [])[:12]:
        title = str(report.get("title") or "")
        cards.append(
            EvidenceCard(
                id=_stable_id("ev-report", str(report.get("info_code")), title),
                source_name=f"eastmoney_industry_report/{report.get('org') or 'unknown'}",
                source_type="industry_research_report",
                title=title,
                source_url=report.get("url") or report.get("source_url"),
                freshness=str(report.get("publish_date") or "latest_available"),
                related_themes=[str(report.get("industry_name") or "")],
                claims=[
                    f"industry={report.get('industry_name')}",
                    f"rating={report.get('rating')}",
                    f"publish_date={report.get('publish_date')}",
                ],
                raw={k: v for k, v in report.items() if k != "raw"},
            )
        )

    pipeline = payload.get("research_pipeline", {})
    chain = pipeline.get("selected_industry_chain", {}) if isinstance(pipeline, dict) else {}
    if chain:
        cards.append(
            EvidenceCard(
                id=_stable_id("ev-chain", str(chain.get("selected_theme")), str(payload.get("started_at")), str(cycle)),
                source_name="skill/industry-chain-analysis",
                source_type="industry_chain_analysis",
                title=f"产业链分析：{chain.get('selected_theme')}",
                freshness="current_cycle",
                related_themes=[str(chain.get("selected_theme") or "")],
                claims=[
                    f"selected_theme={chain.get('selected_theme')}",
                    f"score={chain.get('score')}",
                    f"skill_files={','.join(chain.get('skill_manifest', {}).get('files_used', []))}",
                ],
                raw=chain,
            )
        )

    for symbol, supplement in payload.get("stock_supplements", {}).items():
        announcements = supplement.get("announcements", {}).get("rows", []) if isinstance(supplement, dict) else []
        financials = supplement.get("financials", {}).get("statements", {}) if isinstance(supplement, dict) else {}
        indicators = financials.get("indicators", []) if isinstance(financials, dict) else []
        research_reports = supplement.get("research_reports", {}).get("rows", []) if isinstance(supplement, dict) else []
        cards.append(
            EvidenceCard(
                id=_stable_id("ev-stock-supplement", str(symbol), str(payload.get("started_at")), str(cycle)),
                source_name="a-stock-data/eastmoney_public_data",
                source_type="stock_supplement",
                title=f"A股补充数据：{symbol}",
                freshness="latest_available",
                related_companies=[str(symbol)],
                claims=[
                    f"symbol={symbol}",
                    f"fund_flow_rows={len(supplement.get('fund_flow', {}).get('rows', [])) if isinstance(supplement, dict) else 0}",
                    f"dragon_tiger_rows={len(supplement.get('dragon_tiger', {}).get('rows', [])) if isinstance(supplement, dict) else 0}",
                    f"announcement_rows={len(announcements)}",
                    f"financial_indicator_periods={len(indicators)}",
                    f"research_report_rows={len(research_reports)}",
                ],
                raw=supplement,
            )
        )

    trading_review = payload.get("tradingagents_review", {})
    if trading_review:
        cards.append(
            EvidenceCard(
                id=_stable_id("ev-tradingagents", str(payload.get("started_at")), str(cycle)),
                source_name="external/TradingAgents-astock",
                source_type="committee_review",
                title=f"TradingAgents投委会评审：{trading_review.get('portfolio_rating')}",
                freshness="current_cycle",
                claims=[
                    f"portfolio_rating={trading_review.get('portfolio_rating')}",
                    f"trader_action={trading_review.get('trader_action')}",
                    f"schema_contract={trading_review.get('schema_contract')}",
                ],
                raw=trading_review,
            )
        )

    decisions = pipeline.get("trade_decision_engine", {}) if isinstance(pipeline, dict) else {}
    if decisions:
        cards.append(
            EvidenceCard(
                id=_stable_id("ev-decision", str(payload.get("started_at")), str(cycle)),
                source_name="loop_os/trade-decision-engine",
                source_type="decision_gate",
                title="交易决策门禁输出",
                freshness="current_cycle",
                claims=[
                    f"decision_count={len(decisions.get('decisions', []))}",
                    "research_only=true",
                ],
                raw=decisions,
            )
        )

    review = payload.get("agent_review", {})
    review_provider = review.get("agent_provider") or review.get("review_type") or "agent_review"
    cards.append(
        EvidenceCard(
            id=_stable_id("ev-review", str(payload.get("started_at")), str(cycle)),
            source_name=f"loop_os/{review_provider}",
            source_type="agent_review",
            title=f"Agent评审：cycle {cycle} decision={review.get('decision')}",
            freshness="current_cycle",
            claims=[
                f"decision={review.get('decision')}",
                f"agent_provider={review.get('agent_provider')}",
                str(review.get("reason") or ""),
            ],
            raw=review or {"review": "empty"},
        )
    )
    return cards


def _claim_records_from_card(card: dict[str, Any]) -> dict[str, Any]:
    claims: dict[str, Any] = {}
    evidence_id = str(card.get("id") or "")
    if not evidence_id:
        return claims

    for idx, claim in enumerate(card.get("claims", [])):
        claim_text = str(claim).strip()
        if not claim_text:
            continue
        claim_id = card.get("claim_id") if idx == 0 and card.get("claim_id") else f"{evidence_id}:claim:{idx}"
        claims[str(claim_id)] = {
            "claim_id": str(claim_id),
            "evidence_id": evidence_id,
            "claim": claim_text,
            "source_name": card.get("source_name"),
            "source_type": card.get("source_type"),
            "source_url": card.get("source_url") or card.get("url"),
            "raw_path": card.get("raw_path"),
            "freshness": card.get("freshness"),
            "related_companies": card.get("related_companies") or [],
            "related_themes": card.get("related_themes") or [],
            "created_at": card.get("created_at") or card.get("observed_at"),
        }
    return claims


def rebuild_claim_index(evidence_dir: Path) -> dict[str, Any]:
    claims: dict[str, Any] = {}
    for path in sorted(evidence_dir.glob("ev-*.json")):
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        claims.update(_claim_records_from_card(card))
    return {"schema_version": "1.0", "updated_at": _utc_now(), "claims": claims}


def rebuild_all_claim_indexes(root: Path) -> list[Path]:
    evidence_root = root / "evidence"
    rebuilt: list[Path] = []
    if not evidence_root.exists():
        return rebuilt
    for evidence_dir in sorted(path for path in evidence_root.iterdir() if path.is_dir()):
        claim_index_path = evidence_dir / "claim-index.json"
        claim_index_path.write_text(
            json.dumps(rebuild_claim_index(evidence_dir), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rebuilt.append(claim_index_path)
    return rebuilt


def write_evidence(root: Path, cycle: int, payload: dict[str, Any]) -> list[str]:
    cards = build_evidence_cards(cycle, payload)
    date_key = datetime.now().strftime("%Y-%m-%d")
    evidence_dir = root / "evidence" / date_key
    evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_index_path = evidence_dir / "raw-index.json"
    claim_index_path = evidence_dir / "claim-index.json"
    if raw_index_path.exists():
        index = json.loads(raw_index_path.read_text(encoding="utf-8"))
    else:
        index = {"schema_version": "1.0", "updated_at": None, "evidence_ids": []}

    written: list[str] = []
    for card in cards:
        errors = card.validate()
        if errors:
            raise ValueError(f"invalid evidence {card.id}: {errors}")
        path = evidence_dir / f"{card.id}.json"
        path.write_text(json.dumps(card.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(card.id)
        if card.id not in index["evidence_ids"]:
            index["evidence_ids"].append(card.id)

    index["updated_at"] = _utc_now()
    raw_index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    claim_index_path.write_text(json.dumps(rebuild_claim_index(evidence_dir), ensure_ascii=False, indent=2), encoding="utf-8")
    return written
