from __future__ import annotations

import csv
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from loop_os.domain.market_analysis import valuation_band
from loop_os.schemas.provider import ProviderResult

from .http_utils import get_json, get_text


ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = ROOT / "skills" / "a-stock-data"
LOCAL_A_DATA = Path(os.environ.get("RESEARCH_OS_A_DATA_DIR", ROOT / "data" / "local" / "a-data")).expanduser()
PROVIDER_NAME = "a-stock-data"
PROVIDER_SUBMODULE = "skills/a-stock-data"


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return "$RESEARCH_OS_A_DATA_DIR"


def _get_json_retry(url: str, params: dict[str, str], *, timeout: int = 15, retries: int = 1) -> dict:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return get_json(url, params=params, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - provider fallback wrapper
            last_exc = exc
            if attempt < retries:
                time.sleep(1.2)
    assert last_exc is not None
    raise last_exc


def _safe_float(value: object, *, scale: float = 1.0) -> float | None:
    if value in (None, "", "--", "-"):
        return None
    try:
        return float(str(value).replace(",", "")) / scale
    except ValueError:
        return None


def _tencent_a_quote(symbol: str = "600519") -> dict:
    prefix = "sh" if symbol.startswith("6") else "sz"
    text = get_text(f"https://qt.gtimg.cn/q={prefix}{symbol}", encoding="gbk")
    match = re.search(r'"([^"]*)"', text)
    if not match:
        raise RuntimeError("Tencent quote response did not contain quoted payload")
    fields = match.group(1).split("~")
    if len(fields) < 46:
        raise RuntimeError(f"Tencent quote field count too small: {len(fields)}")
    price = float(fields[3])
    prev_close = float(fields[4])
    pe = float(fields[39]) if fields[39] else None
    pb = float(fields[46]) if len(fields) > 46 and fields[46] else None
    return {
        "symbol": symbol,
        "name": fields[1],
        "price": price,
        "prev_close": prev_close,
        "change_pct": round((price - prev_close) / prev_close * 100, 4) if prev_close else None,
        "volume": fields[6],
        "turnover": fields[37] if len(fields) > 37 else None,
        "pe": pe,
        "pb": pb,
        "valuation_band": valuation_band(pe),
        "source": "tencent_finance",
        "provider": PROVIDER_NAME,
        "provider_submodule": PROVIDER_SUBMODULE,
    }


def _eastmoney_secid(symbol: str) -> str:
    market = "1" if symbol.startswith(("6", "9")) else "0"
    return f"{market}.{symbol}"


def _eastmoney_secucode(symbol: str) -> str:
    suffix = "SH" if symbol.startswith(("6", "9")) else "SZ"
    return f"{symbol}.{suffix}"


def _eastmoney_a_quote(symbol: str) -> dict:
    payload = get_json(
        "https://push2.eastmoney.com/api/qt/stock/get",
        params={
            "secid": _eastmoney_secid(symbol),
            "fields": "f43,f47,f48,f57,f58,f60,f116,f117,f162,f167,f168,f170",
        },
        timeout=10,
    )
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or not data:
        raise RuntimeError(f"Eastmoney quote returned empty data for {symbol}")
    price = _safe_float(data.get("f43"), scale=100)
    prev_close = _safe_float(data.get("f60"), scale=100)
    pe = _safe_float(data.get("f162"), scale=100)
    pb = _safe_float(data.get("f167"), scale=100)
    if price is None or prev_close is None:
        raise RuntimeError(f"Eastmoney quote missing price fields for {symbol}")
    return {
        "symbol": symbol,
        "name": data.get("f58") or symbol,
        "price": price,
        "prev_close": prev_close,
        "change_pct": _safe_float(data.get("f170"), scale=100),
        "volume": data.get("f47"),
        "turnover": data.get("f48"),
        "turnover_rate": _safe_float(data.get("f168"), scale=100),
        "pe": pe,
        "pb": pb,
        "float_market_cap": data.get("f117"),
        "total_market_cap": data.get("f116"),
        "valuation_band": valuation_band(pe),
        "source": "eastmoney_push2",
        "provider": PROVIDER_NAME,
        "provider_submodule": PROVIDER_SUBMODULE,
    }


def _local_hist_quote(symbol: str) -> dict:
    path = LOCAL_A_DATA / "hist" / f"{symbol}.csv"
    if not path.exists():
        raise RuntimeError(f"local hist missing for {symbol}: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"local hist empty for {symbol}: {path}")
    row = rows[-1]
    price = _safe_float(row.get("收盘"))
    prev_close = _safe_float(rows[-2].get("收盘")) if len(rows) >= 2 else None
    if price is None:
        raise RuntimeError(f"local hist missing close for {symbol}: {path}")
    return {
        "symbol": symbol,
        "name": symbol,
        "price": price,
        "prev_close": prev_close,
        "change_pct": _safe_float(row.get("涨跌幅")),
        "volume": row.get("成交量"),
        "turnover": row.get("成交额"),
        "pe": None,
        "pb": None,
        "valuation_band": "unknown",
        "source": "local_a_data_hist",
        "provider": PROVIDER_NAME,
        "provider_submodule": PROVIDER_SUBMODULE,
        "trade_date": row.get("日期"),
    }


def fetch_quote(symbol: str) -> dict:
    errors: list[str] = []
    for fn in (_tencent_a_quote, _eastmoney_a_quote, _local_hist_quote):
        try:
            quote = fn(symbol)
            if errors:
                quote["fallback_errors"] = errors
            return quote
        except Exception as exc:
            fn_name = getattr(fn, "__name__", fn.__class__.__name__)
            errors.append(f"{fn_name}: {exc!r}")
    raise RuntimeError("; ".join(errors))


def fetch_quotes(symbols: Iterable[str] = ("600519", "300750", "688017")) -> list[dict]:
    return [fetch_quote(symbol) for symbol in symbols]


def fetch_fund_flow(symbol: str, days: int = 5) -> dict:
    secid = _eastmoney_secid(symbol)
    payload = _get_json_retry(
        "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
        params={
            "secid": secid,
            "lmt": str(days),
            "klt": "101",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
        },
        timeout=15,
        retries=1,
    )
    rows = payload.get("data", {}).get("klines", []) if isinstance(payload, dict) else []
    parsed = []
    for row in rows[-days:]:
        parts = str(row).split(",")
        if len(parts) >= 6:
            parsed.append(
                {
                    "date": parts[0],
                    "main_net_inflow": _safe_float(parts[1]),
                    "small_net_inflow": _safe_float(parts[2]),
                    "medium_net_inflow": _safe_float(parts[3]),
                    "large_net_inflow": _safe_float(parts[4]),
                    "super_large_net_inflow": _safe_float(parts[5]),
                }
            )
    return {"symbol": symbol, "source": "eastmoney_fund_flow", "rows": parsed}


def fetch_price_history(symbol: str, days: int = 120) -> dict:
    payload = _get_json_retry(
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        params={
            "secid": _eastmoney_secid(symbol),
            "klt": "101",
            "fqt": "1",
            "lmt": str(days),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        },
        timeout=15,
        retries=1,
    )
    rows = payload.get("data", {}).get("klines", []) if isinstance(payload, dict) else []
    parsed = []
    for row in rows:
        parts = str(row).split(",")
        if len(parts) >= 7:
            parsed.append(
                {
                    "date": parts[0],
                    "open": _safe_float(parts[1]),
                    "close": _safe_float(parts[2]),
                    "high": _safe_float(parts[3]),
                    "low": _safe_float(parts[4]),
                    "volume": _safe_float(parts[5]),
                    "turnover": _safe_float(parts[6]),
                    "change_pct": _safe_float(parts[8]) if len(parts) > 8 else None,
                }
            )
    return {"symbol": symbol, "source": "eastmoney_kline", "rows": parsed}


def fetch_price_history_fallback(symbol: str, days: int = 120) -> dict:
    path = LOCAL_A_DATA / "hist" / f"{symbol}.csv"
    if not path.exists():
        raise RuntimeError(f"local hist missing for {symbol}: {path}")
    parsed = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            parsed.append(
                {
                    "date": row.get("日期"),
                    "open": _safe_float(row.get("开盘")),
                    "close": _safe_float(row.get("收盘")),
                    "high": _safe_float(row.get("最高")),
                    "low": _safe_float(row.get("最低")),
                    "volume": _safe_float(row.get("成交量")),
                    "turnover": _safe_float(row.get("成交额")),
                    "change_pct": _safe_float(row.get("涨跌幅")),
                }
            )
    return {"symbol": symbol, "source": "local_a_data_hist", "rows": parsed[-days:]}


def fetch_dragon_tiger(symbol: str | None = None, date: str | None = None) -> dict:
    date = date or ""
    payload = _get_json_retry(
        "https://datacenter-web.eastmoney.com/api/data/v1/get",
        params={
            "reportName": "RPT_DAILYBILLBOARD_DETAILS",
            "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,CLOSE_PRICE,CHANGE_RATE,BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,EXPLANATION,TRADE_DATE",
            "pageNumber": "1",
            "pageSize": "50",
            "sortColumns": "BILLBOARD_NET_AMT",
            "sortTypes": "-1",
            "filter": f"(TRADE_DATE='{date}')" if date else "",
        },
        timeout=15,
        retries=1,
    )
    rows = payload.get("result", {}).get("data", []) if isinstance(payload, dict) else []
    if symbol:
        rows = [row for row in rows if str(row.get("SECURITY_CODE")) == symbol]
    return {"symbol": symbol, "source": "eastmoney_dragon_tiger", "rows": rows[:10]}


def fetch_basic_info(symbol: str) -> dict:
    payload = _get_json_retry(
        "https://push2.eastmoney.com/api/qt/stock/get",
        params={
            "secid": _eastmoney_secid(symbol),
            "fields": "f57,f58,f84,f85,f116,f117,f127,f128,f129,f130,f131,f132",
        },
        timeout=10,
        retries=1,
    )
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    return {
        "symbol": symbol,
        "source": "eastmoney_basic_info",
        "name": data.get("f58"),
        "total_shares": data.get("f84"),
        "float_shares": data.get("f85"),
        "total_market_cap": data.get("f116"),
        "float_market_cap": data.get("f117"),
        "industry": data.get("f127") or data.get("f128"),
    }


def fetch_basic_info_fallback(symbol: str) -> dict:
    quote = fetch_quote(symbol)
    return {
        "symbol": symbol,
        "source": f"{quote.get('source')}_basic_fallback",
        "name": quote.get("name"),
        "total_market_cap": quote.get("total_market_cap"),
        "float_market_cap": quote.get("float_market_cap"),
        "pe": quote.get("pe"),
        "pb": quote.get("pb"),
        "industry": None,
    }


def fetch_liquidity_proxy(symbol: str) -> dict:
    quote = fetch_quote(symbol)
    return {
        "symbol": symbol,
        "source": "liquidity_proxy_from_quote",
        "proxy": True,
        "method": "Eastmoney fund-flow endpoint unavailable; use public quote change/turnover as liquidity proxy only.",
        "rows": [
            {
                "date": quote.get("trade_date") or datetime.now().strftime("%Y-%m-%d"),
                "main_net_inflow": None,
                "change_pct": quote.get("change_pct"),
                "volume": quote.get("volume"),
                "turnover": quote.get("turnover"),
                "price": quote.get("price"),
            }
        ],
    }


def fetch_announcements(symbol: str, limit: int = 10) -> dict:
    payload = get_json(
        "https://np-anotice-stock.eastmoney.com/api/security/ann",
        params={
            "sr": "-1",
            "page_size": str(limit),
            "page_index": "1",
            "ann_type": "A",
            "client_source": "web",
            "stock_list": symbol,
            "f_node": "0",
            "s_node": "0",
        },
        timeout=20,
    )
    rows = payload.get("data", {}).get("list", []) if isinstance(payload, dict) else []
    parsed = []
    for row in rows[:limit]:
        columns = row.get("columns") or []
        col_names = [item.get("column_name") for item in columns if isinstance(item, dict) and item.get("column_name")]
        art_code = row.get("art_code") or ""
        parsed.append(
            {
                "date": (row.get("notice_date") or row.get("display_time") or "")[:10],
                "title": row.get("title") or row.get("title_ch") or "",
                "category": col_names[0] if col_names else "",
                "url": f"https://data.eastmoney.com/notices/detail/{symbol}/{art_code}.html" if art_code else "",
                "source": "eastmoney_announcement",
            }
        )
    return {"symbol": symbol, "source": "eastmoney_announcement", "rows": parsed}


def fetch_financials(symbol: str, periods: int = 4) -> dict:
    secucode = _eastmoney_secucode(symbol)
    report_names = {
        "indicators": "RPT_F10_FINANCE_MAINFINADATA",
        "balance": "RPT_F10_FINANCE_GBALANCE",
        "income": "RPT_F10_FINANCE_GINCOME",
        "cashflow": "RPT_F10_FINANCE_GCASHFLOW",
    }
    statements: dict[str, list[dict]] = {}
    errors: list[str] = []
    for key, report_name in report_names.items():
        try:
            payload = get_json(
                "https://datacenter.eastmoney.com/securities/api/data/v1/get",
                params={
                    "reportName": report_name,
                    "columns": "ALL",
                    "filter": f'(SECUCODE="{secucode}")',
                    "pageNumber": "1",
                    "pageSize": str(periods),
                    "sortColumns": "REPORT_DATE",
                    "sortTypes": "-1",
                },
                timeout=20,
            )
            rows = payload.get("result", {}).get("data", []) if isinstance(payload, dict) else []
            statements[key] = rows[:periods]
        except Exception as exc:
            statements[key] = []
            errors.append(f"{key}: {exc!r}")
    return {"symbol": symbol, "source": "eastmoney_f10_finance", "statements": statements, "errors": errors}


def fetch_stock_research_reports(symbol: str, limit: int = 10, begin: str = "2024-01-01") -> dict:
    payload = get_json(
        "https://reportapi.eastmoney.com/report/list",
        params={
            "industryCode": "*",
            "pageSize": str(limit),
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": begin,
            "endTime": "2030-01-01",
            "pageNo": "1",
            "fields": "",
            "qType": "0",
            "orgCode": "",
            "code": symbol,
            "rcode": "",
            "p": "1",
            "pageNum": "1",
            "pageNumber": "1",
        },
        timeout=30,
    )
    rows = payload.get("data") or []
    parsed = []
    for row in rows[:limit]:
        parsed.append(
            {
                "title": row.get("title") or "",
                "org": row.get("orgSName") or row.get("orgName") or "",
                "analyst": row.get("researcher") or "",
                "publish_date": (row.get("publishDate") or "")[:10],
                "rating": row.get("emRatingName") or row.get("sRatingName") or "",
                "info_code": row.get("infoCode") or "",
                "eps_forecast": {
                    "this_year": _safe_float(row.get("predictThisYearEps")),
                    "next_year": _safe_float(row.get("predictNextYearEps")),
                    "next_two_year": _safe_float(row.get("predictNextTwoYearEps")),
                },
                "pe_forecast": {
                    "this_year": _safe_float(row.get("predictThisYearPe")),
                    "next_year": _safe_float(row.get("predictNextYearPe")),
                    "next_two_year": _safe_float(row.get("predictNextTwoYearPe")),
                },
                "pdf_url": f"https://pdf.dfcfw.com/pdf/H3_{row.get('infoCode')}_1.pdf" if row.get("infoCode") else "",
                "source": "eastmoney_reportapi",
            }
        )
    return {"symbol": symbol, "source": "eastmoney_reportapi", "rows": parsed}


def fetch_stock_supplement(symbol: str) -> dict:
    result: dict[str, object] = {
        "symbol": symbol,
        "provider": PROVIDER_NAME,
        "provider_submodule": PROVIDER_SUBMODULE,
        "fundamental": {},
        "announcements": {},
        "fund_flow": {},
        "price_history": {},
        "dragon_tiger": {},
        "financials": {},
        "research_reports": {},
        "catalysts": [],
        "risks": [],
        "errors": [],
    }
    try:
        result["fundamental"] = fetch_basic_info(symbol)
    except Exception as exc:
        result["errors"].append(f"basic_info: {exc!r}")  # type: ignore[index]
        try:
            result["fundamental"] = fetch_basic_info_fallback(symbol)
        except Exception as fallback_exc:
            result["errors"].append(f"basic_info_fallback: {fallback_exc!r}")  # type: ignore[index]
    try:
        result["fund_flow"] = fetch_fund_flow(symbol)
    except Exception as exc:
        result["errors"].append(f"fund_flow: {exc!r}")  # type: ignore[index]
        try:
            result["fund_flow"] = fetch_liquidity_proxy(symbol)
        except Exception as fallback_exc:
            result["errors"].append(f"fund_flow_proxy: {fallback_exc!r}")  # type: ignore[index]
    try:
        result["price_history"] = fetch_price_history(symbol)
    except Exception as exc:
        result["errors"].append(f"price_history: {exc!r}")  # type: ignore[index]
        try:
            result["price_history"] = fetch_price_history_fallback(symbol)
        except Exception as fallback_exc:
            result["errors"].append(f"price_history_fallback: {fallback_exc!r}")  # type: ignore[index]
    try:
        result["dragon_tiger"] = fetch_dragon_tiger(symbol)
    except Exception as exc:
        result["errors"].append(f"dragon_tiger: {exc!r}")  # type: ignore[index]
    try:
        result["announcements"] = fetch_announcements(symbol)
    except Exception as exc:
        result["errors"].append(f"announcements: {exc!r}")  # type: ignore[index]
    try:
        result["financials"] = fetch_financials(symbol)
    except Exception as exc:
        result["errors"].append(f"financials: {exc!r}")  # type: ignore[index]
    try:
        since = (datetime.now() - timedelta(days=900)).strftime("%Y-%m-%d")
        result["research_reports"] = fetch_stock_research_reports(symbol, begin=since)
    except Exception as exc:
        result["errors"].append(f"research_reports: {exc!r}")  # type: ignore[index]
    return result


def fetch_industry_reports(max_pages: int = 1, begin: str = "2024-01-01") -> list[dict]:
    records: list[dict] = []
    for page in range(1, max_pages + 1):
        payload = get_json(
            "https://reportapi.eastmoney.com/report/list",
            params={
                "industryCode": "*",
                "pageSize": "50",
                "industry": "*",
                "rating": "*",
                "ratingChange": "*",
                "beginTime": begin,
                "endTime": "2030-01-01",
                "pageNo": str(page),
                "fields": "",
                "qType": "1",
            },
            timeout=30,
        )
        rows = payload.get("data") or []
        if not rows:
            break
        records.extend(rows)
        total_page = payload.get("TotalPage") or payload.get("totalPage") or 1
        if page >= int(total_page):
            break
    parsed = []
    for item in records:
        info_code = item.get("infoCode") or ""
        if not item.get("title"):
            continue
        pdf_url = f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf" if info_code else ""
        parsed.append(
            {
                "title": item.get("title") or "",
                "industry_name": item.get("industryName") or item.get("indvInduName") or "",
                "industry_code": item.get("industryCode") or "",
                "org": item.get("orgSName") or "",
                "rating": item.get("emRatingName") or "",
                "publish_date": (item.get("publishDate") or "")[:10],
                "info_code": info_code,
                "url": pdf_url,
                "pdf_url": pdf_url,
                "report_type": item.get("reportType") or "",
                "raw": item,
            }
        )
    return parsed


def smoke(live: bool = False) -> ProviderResult:
    skill_path = SUBMODULE / "SKILL.md"
    if not SUBMODULE.exists() or not skill_path.exists():
        return ProviderResult("a-stock-data", "error", "submodule or SKILL.md missing", errors=[_display_path(skill_path)])
    if not live:
        return ProviderResult(
            "a-stock-data",
            "ok",
            "submodule readable and adapter available",
            {
                "path": _display_path(SUBMODULE),
                "skill": _display_path(skill_path),
                "adapter_strategy": "tencent -> eastmoney -> configured local a-data",
                "local_data_dir": _display_path(LOCAL_A_DATA),
            },
        )
    try:
        quote = fetch_quote("600519")
        return ProviderResult(
            "a-stock-data",
            "ok",
            f"A股样本 {quote['symbol']} {quote['name']} 取数成功，PE band={quote['valuation_band']}",
            {"quote": quote},
        )
    except Exception as exc:
        return ProviderResult("a-stock-data", "error", "A股实时行情取数失败", errors=[repr(exc)])
