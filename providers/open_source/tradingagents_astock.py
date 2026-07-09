from __future__ import annotations

from pathlib import Path
from typing import Any

from loop_os.schemas.provider import ProviderResult


ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = ROOT / "external" / "TradingAgents-astock"
SCHEMA_FILE = SUBMODULE / "tradingagents" / "agents" / "schemas.py"


def _display_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def review_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """TradingAgents-astock style structured committee review.

    This adapter intentionally does not let the submodule write state. It uses the
    submodule's structured-output schema file as the locked role/rating contract
    and renders a local ReviewReport.
    """
    schema_text = SCHEMA_FILE.read_text(encoding="utf-8") if SCHEMA_FILE.exists() else ""
    stocks = packet.get("stock_analyzer", [])
    chain = packet.get("selected_industry_chain", {})
    decisions = packet.get("trade_decision_engine", {}).get("decisions", [])
    rejected = [item for item in decisions if item.get("action") == "reject_or_wait"]
    candidates = [item for item in decisions if item.get("action") == "paper_candidate"]
    rating = "Hold"
    if candidates:
        rating = "Overweight"
    if rejected and not candidates:
        rating = "Underweight"
    return {
        "review_type": "tradingagents_astock",
        "provider": "TradingAgents-astock",
        "schema_contract": "ResearchPlan/TraderProposal/PortfolioDecision" if "ResearchPlan" in schema_text else "local_contract",
        "roles": {
            "bull_researcher": [
                f"{chain.get('selected_theme')} 是本轮最高权重产业链，score={chain.get('score')}。",
                "若终端需求和A股收入暴露被公告/研报正文确认，可进入模拟观察。",
            ],
            "bear_researcher": [
                "当前多数证据仍是标题级研报/新闻，需要防止把研究热度误判为业绩兑现。",
                "高估值或技术破位标的必须先降级为反证样本。",
            ],
            "risk_manager": [
                "无真实交易；所有候选必须通过 evidence、估值、技术和反证条件。",
                f"本轮 reject_or_wait 数量={len(rejected)}。",
            ],
            "policy_news": [
                "只接受公开新闻、研报、公告、行情和财务数据作为证据来源。",
            ],
            "hot_money": [
                "资金面仅作为拥挤度和确认度的辅助信号，不作为单独买入理由。",
            ],
        },
        "portfolio_rating": rating,
        "trader_action": "Hold" if rating in {"Hold", "Underweight"} else "Buy",
        "state_mutation_allowed": False,
        "source_submodule": "external/TradingAgents-astock",
    }


def smoke(live: bool = False) -> ProviderResult:
    readme = SUBMODULE / "README.md"
    if not readme.exists():
        return ProviderResult("TradingAgents-astock", "error", "README missing", errors=[_display_path(readme)])
    return ProviderResult(
        "TradingAgents-astock",
        "ok",
        "review provider submodule readable; adapter can produce TradingAgents-style ReviewReport",
        {"path": _display_path(SUBMODULE), "live_invoked": False},
    )
