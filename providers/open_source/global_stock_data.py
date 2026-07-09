from __future__ import annotations

import re
from pathlib import Path

from loop_os.domain.market_analysis import price_change_pct
from loop_os.schemas.provider import ProviderResult

from .http_utils import get_json, get_text


ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = ROOT / "skills" / "global-stock-data"


def _display_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def _yahoo_chart(symbol: str = "AAPL") -> dict:
    data = get_json(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"range": "5d", "interval": "1d"},
    )
    result = data.get("chart", {}).get("result", [])
    if not result:
        raise RuntimeError(f"Yahoo chart returned no result: {data.get('chart', {}).get('error')}")
    node = result[0]
    quote = node["indicators"]["quote"][0]
    closes = [v for v in quote.get("close", []) if isinstance(v, (int, float))]
    if len(closes) < 2:
        raise RuntimeError("Yahoo chart returned fewer than two closes")
    latest, previous = float(closes[-1]), float(closes[-2])
    meta = node.get("meta", {})
    return {
        "symbol": symbol,
        "currency": meta.get("currency"),
        "exchange": meta.get("exchangeName"),
        "latest_close": latest,
        "previous_close": previous,
        "change_pct": price_change_pct(latest, previous),
        "bars": len(closes),
        "source": "yahoo_chart",
    }


def _stooq_chart(symbol: str) -> dict:
    text = get_text(
        "https://stooq.com/q/d/l/",
        params={"s": f"{symbol.lower()}.us", "i": "d"},
        timeout=15,
    )
    rows = [line.split(",") for line in text.splitlines() if line and not line.startswith("Date,")]
    closes = [float(row[4]) for row in rows[-5:] if len(row) >= 5 and row[4]]
    if len(closes) < 2:
        raise RuntimeError(f"Stooq returned fewer than two closes for {symbol}")
    latest, previous = closes[-1], closes[-2]
    return {
        "symbol": symbol,
        "currency": "USD",
        "exchange": "stooq",
        "latest_close": latest,
        "previous_close": previous,
        "change_pct": price_change_pct(latest, previous),
        "bars": len(closes),
        "source": "stooq_daily_csv",
    }


def _tencent_us_quote(symbol: str) -> dict:
    text = get_text(f"https://qt.gtimg.cn/q=us{symbol.upper()}", encoding="gbk", timeout=10)
    match = re.search(r'"([^"]*)"', text)
    if not match:
        raise RuntimeError(f"Tencent US quote response did not contain payload for {symbol}")
    fields = match.group(1).split("~")
    if len(fields) < 45:
        raise RuntimeError(f"Tencent US quote field count too small for {symbol}: {len(fields)}")
    latest = float(fields[3])
    previous = float(fields[4])
    return {
        "symbol": symbol,
        "currency": fields[34] or "USD",
        "exchange": "tencent_us",
        "latest_close": latest,
        "previous_close": previous,
        "change_pct": price_change_pct(latest, previous),
        "bars": 1,
        "source": "tencent_us_quote",
        "name": fields[1],
        "name_en": fields[45] if len(fields) > 45 else None,
    }


def fetch_chart(symbol: str) -> dict:
    try:
        return _yahoo_chart(symbol)
    except Exception as yahoo_error:
        try:
            chart = _tencent_us_quote(symbol)
            chart["fallback_reason"] = repr(yahoo_error)
            return chart
        except Exception as tencent_error:
            chart = _stooq_chart(symbol)
            chart["fallback_reason"] = f"yahoo={yahoo_error!r}; tencent={tencent_error!r}"
            return chart


def fetch_charts(symbols: tuple[str, ...] = ("AAPL", "NVDA", "TSLA")) -> list[dict]:
    return [fetch_chart(symbol) for symbol in symbols]


def smoke(live: bool = False) -> ProviderResult:
    if not SUBMODULE.exists():
        return ProviderResult("global-stock-data", "error", "submodule missing", errors=[_display_path(SUBMODULE)])
    if not live:
        return ProviderResult("global-stock-data", "ok", "submodule readable", {"path": _display_path(SUBMODULE)})
    try:
        chart = fetch_chart("AAPL")
        return ProviderResult(
            "global-stock-data",
            "ok",
            f"全球股票样本 {chart['symbol']} 取数成功，5d bars={chart['bars']}",
            {"chart": chart},
        )
    except Exception as exc:
        return ProviderResult("global-stock-data", "error", "全球股票行情取数失败", errors=[repr(exc)])
