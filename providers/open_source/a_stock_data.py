from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import time
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Iterable

from loop_os.domain.market_analysis import valuation_band
from loop_os.schemas.provider import ProviderResult

from . import tushare_provider
from .http_utils import get_json, get_text


ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = ROOT / "skills" / "a-stock-data"
VIBE_RESEARCH_ASTOCK = ROOT / "external" / "Vibe-Research" / "backend" / "astock.py"
LOCAL_A_DATA = Path(os.environ.get("RESEARCH_OS_A_DATA_DIR", ROOT / "data" / "local" / "a-data")).expanduser()
PROVIDER_NAME = "a-stock-data"
PROVIDER_SUBMODULE = "skills/a-stock-data"
TUSHARE_SOURCE = "tushare_priority"
_VIBE_ASTOCK_MODULE = None


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


def _vibe_astock():
    """Load Vibe-Research's A-share data helpers behind the provider boundary."""
    global _VIBE_ASTOCK_MODULE
    if _VIBE_ASTOCK_MODULE is not None:
        return _VIBE_ASTOCK_MODULE
    if not VIBE_RESEARCH_ASTOCK.exists():
        raise RuntimeError(f"Vibe-Research astock adapter missing: {VIBE_RESEARCH_ASTOCK}")
    spec = importlib.util.spec_from_file_location("research_os_vibe_astock", VIBE_RESEARCH_ASTOCK)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Vibe-Research astock adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _VIBE_ASTOCK_MODULE = module
    return module


def _safe_float(value: object, *, scale: float = 1.0) -> float | None:
    if value in (None, "", "--", "-"):
        return None
    try:
        return float(str(value).replace(",", "")) / scale
    except ValueError:
        return None


def _history_cache_path(symbol: str) -> Path:
    return LOCAL_A_DATA / "hist" / f"{symbol}.csv"


def _quote_cache_path(symbol: str) -> Path:
    return LOCAL_A_DATA / "quote" / f"{symbol}.json"


def _compact_date(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())[:8]


def _date_from_compact(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y%m%d")
    except Exception:
        return None


def latest_expected_trade_date(now: datetime | None = None) -> str:
    now = now or datetime.now()
    candidate = now.date()
    if now.weekday() >= 5 or now.time() < dt_time(15, 30):
        candidate = candidate - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate = candidate - timedelta(days=1)
    fallback = candidate.strftime("%Y%m%d")
    try:
        cal = tushare_provider.query(
            "trade_cal",
            {"exchange": "SSE", "start_date": (candidate - timedelta(days=10)).strftime("%Y%m%d"), "end_date": now.strftime("%Y%m%d")},
            "cal_date,is_open,pretrade_date",
            limit=15,
        )
        open_dates = sorted(_compact_date(row.get("cal_date")) for row in cal.get("rows", []) if str(row.get("is_open")) in {"1", "1.0", "True", "true"})
        return open_dates[-1] if open_dates else fallback
    except Exception:
        return fallback


def _history_latest_date(history: dict) -> str:
    rows = history.get("rows", []) if isinstance(history, dict) else []
    dates = sorted(_compact_date(row.get("date")) for row in rows if isinstance(row, dict) and _compact_date(row.get("date")))
    return dates[-1] if dates else ""


def _history_is_stale(history: dict, *, expected_date: str | None = None, max_lag_days: int = 0) -> bool:
    latest = _date_from_compact(_history_latest_date(history))
    expected = _date_from_compact(expected_date or latest_expected_trade_date())
    if latest is None or expected is None:
        return True
    return latest < expected and (expected - latest).days > max_lag_days


def price_history_is_stale(history: dict, *, expected_date: str | None = None, max_lag_days: int = 0) -> bool:
    return _history_is_stale(history, expected_date=expected_date, max_lag_days=max_lag_days)


def _supplement_cache_path(symbol: str) -> Path:
    return LOCAL_A_DATA / "supplement" / f"{symbol}.json"


def _write_quote_cache(symbol: str, quote: dict) -> None:
    if not quote or quote.get("price") is None:
        return
    path = _quote_cache_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(quote)
    payload.setdefault("symbol", symbol)
    payload["cached_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _local_quote(symbol: str) -> dict:
    path = _quote_cache_path(symbol)
    if not path.exists():
        raise RuntimeError(f"local quote missing for {symbol}: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("price") is None:
        raise RuntimeError(f"local quote unusable for {symbol}: {path}")
    data.setdefault("source", "local_a_data_quote")
    return data


def _write_supplement_cache(symbol: str, supplement: dict) -> None:
    if not supplement:
        return
    path = _supplement_cache_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(supplement)
    payload.setdefault("symbol", symbol)
    payload["cached_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def fetch_stock_supplement_fallback(symbol: str) -> dict:
    path = _supplement_cache_path(symbol)
    if not path.exists():
        raise RuntimeError(f"local supplement missing for {symbol}: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"local supplement unusable for {symbol}: {path}")
    data.setdefault("symbol", symbol)
    data.setdefault("source", "local_a_data_supplement")
    return data


def _rows_present(section: object) -> bool:
    if not isinstance(section, dict):
        return False
    rows = section.get("rows")
    if isinstance(rows, list) and len(rows) > 0:
        return True
    statements = section.get("statements")
    if isinstance(statements, dict):
        return any(isinstance(value, list) and len(value) > 0 for value in statements.values())
    return False


def stock_supplement_usable(supplement: object) -> bool:
    if not isinstance(supplement, dict) or not supplement:
        return False
    if supplement.get("price_history") and _rows_present(supplement.get("price_history")):
        return True
    if supplement.get("financials") and _rows_present(supplement.get("financials")):
        return True
    if supplement.get("research_reports") and _rows_present(supplement.get("research_reports")):
        return True
    if supplement.get("announcements") and _rows_present(supplement.get("announcements")):
        return True
    fundamental = supplement.get("fundamental")
    if isinstance(fundamental, dict) and any(fundamental.get(key) for key in ("name", "industry", "total_market_cap", "pe", "pb")):
        return True
    return False


def _section_useful(value: object) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    if _rows_present(value):
        return True
    return any(v for k, v in value.items() if k not in {"source", "symbol", "provider", "provider_submodule", "errors"})


def merge_stock_supplement(primary: dict, fallback: dict) -> dict:
    """Fill holes in a live supplement from a cached/local supplement."""
    if not isinstance(primary, dict) or not primary:
        return dict(fallback) if isinstance(fallback, dict) else {}
    if not isinstance(fallback, dict) or not fallback:
        return dict(primary)
    merged = dict(primary)
    for key in (
        "fundamental",
        "announcements",
        "fund_flow",
        "price_history",
        "dragon_tiger",
        "financials",
        "research_reports",
        "margin_trading",
        "concept_blocks",
        "valuation_percentile",
        "capital_actions",
    ):
        value = merged.get(key)
        fallback_value = fallback.get(key)
        if not _section_useful(value) and fallback_value:
            merged[key] = fallback_value
    for key in ("catalysts", "risks"):
        value = merged.get(key)
        fallback_value = fallback.get(key)
        if not value and fallback_value:
            merged[key] = fallback_value
    errors = []
    for source in (primary.get("errors"), fallback.get("errors")):
        if isinstance(source, list):
            errors.extend(str(item) for item in source if item)
    if errors:
        merged["errors"] = errors
    merged.setdefault("symbol", primary.get("symbol") or fallback.get("symbol"))
    merged.setdefault("provider", PROVIDER_NAME)
    merged.setdefault("provider_submodule", PROVIDER_SUBMODULE)
    merged["cache_backfilled"] = True
    return merged


def fetch_stock_supplement_resilient(symbol: str) -> dict:
    """Fetch Tushare-first supplement and backfill missing sections from public/cache sources."""
    live_errors: list[str] = []
    tushare_live: dict = {}
    try:
        tushare_live = fetch_stock_supplement_tushare(symbol)
    except Exception as exc:  # noqa: BLE001 - provider boundary
        live_errors.append(f"tushare: {exc!r}")
    public_live: dict = {}
    try:
        if stock_supplement_usable(tushare_live):
            public_live = fetch_stock_supplement_public_backfill(symbol)
        else:
            public_live = fetch_stock_supplement(symbol)
    except Exception as exc:  # noqa: BLE001 - provider boundary
        live_errors.append(f"public_live: {exc!r}")
    cached: dict = {}
    try:
        cached = fetch_stock_supplement_fallback(symbol)
    except Exception as exc:  # noqa: BLE001 - provider boundary
        if live_errors:
            live_errors.append(f"local_cache: {exc!r}")
    merged: dict = {}
    if tushare_live and public_live:
        merged = merge_stock_supplement(tushare_live, public_live)
    elif tushare_live:
        merged = dict(tushare_live)
    elif public_live:
        merged = dict(public_live)
    if merged and cached:
        merged = merge_stock_supplement(merged, cached)
    if stock_supplement_usable(merged):
        return merged
    if stock_supplement_usable(cached):
        if live_errors:
            cached = dict(cached)
            cached.setdefault("errors", []).extend(live_errors)
        return cached
    errors = list(live_errors)
    for payload in (tushare_live, public_live):
        if payload and isinstance(payload.get("errors"), list):
            errors.extend(str(item) for item in payload["errors"])
    raise RuntimeError("; ".join(errors) or f"no usable stock supplement for {symbol}")


def _history_rows_usable(rows: list[dict], *, min_rows: int = 20) -> bool:
    usable = [
        row
        for row in rows
        if row.get("date")
        and _safe_float(row.get("open")) is not None
        and _safe_float(row.get("close")) is not None
        and _safe_float(row.get("high")) is not None
        and _safe_float(row.get("low")) is not None
    ]
    return len(usable) >= min_rows


def _write_price_history_cache(symbol: str, rows: list[dict]) -> None:
    if not _history_rows_usable(rows, min_rows=5):
        return
    path = _history_cache_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "涨跌幅"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "日期": row.get("date"),
                    "开盘": row.get("open"),
                    "收盘": row.get("close"),
                    "最高": row.get("high"),
                    "最低": row.get("low"),
                    "成交量": row.get("volume"),
                    "成交额": row.get("turnover"),
                    "涨跌幅": row.get("change_pct"),
                }
            )


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
    for fn in (fetch_quote_tushare, _tencent_a_quote, _eastmoney_a_quote, _local_quote, _local_hist_quote):
        try:
            quote = fn(symbol)
            if errors:
                quote["fallback_errors"] = errors
            if quote.get("source") not in {"local_a_data_quote", "local_a_data_hist"}:
                _write_quote_cache(symbol, quote)
            return quote
        except Exception as exc:
            fn_name = getattr(fn, "__name__", fn.__class__.__name__)
            errors.append(f"{fn_name}: {exc!r}")
    raise RuntimeError("; ".join(errors))


def fetch_quote_fallback(symbol: str) -> dict:
    try:
        return _local_quote(symbol)
    except Exception:
        return _local_hist_quote(symbol)


def fetch_quotes(symbols: Iterable[str] = ("600519", "300750", "688017")) -> list[dict]:
    return [fetch_quote(symbol) for symbol in symbols]


def _tushare_rows_or_raise(result: dict, api: str) -> list[dict]:
    status = result.get("status")
    if status not in {"ok", "ok_empty"}:
        raise RuntimeError(f"Tushare {api} {status}: {result.get('error', '')}")
    rows = result.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"Tushare {api} returned empty rows")
    return [row for row in rows if isinstance(row, dict)]


def _date_to_tushare(value: datetime) -> str:
    return value.strftime("%Y%m%d")


def _date_from_tushare(value: object) -> str | None:
    raw = str(value or "")
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw or None


def fetch_quote_tushare(symbol: str) -> dict:
    code = tushare_provider.normalize_ts_code(symbol)
    end = datetime.now()
    start = end - timedelta(days=30)
    params = {"ts_code": code, "start_date": _date_to_tushare(start), "end_date": _date_to_tushare(end)}
    daily_rows = _tushare_rows_or_raise(
        tushare_provider.query(
            "daily",
            params,
            "ts_code,trade_date,close,pct_chg,vol,amount",
            limit=10,
        ),
        "daily",
    )
    basic_rows = _tushare_rows_or_raise(
        tushare_provider.query(
            "daily_basic",
            params,
            "ts_code,trade_date,close,pe,pe_ttm,pb,total_mv,circ_mv,turnover_rate",
            limit=10,
        ),
        "daily_basic",
    )
    daily_rows.sort(key=lambda row: str(row.get("trade_date") or ""), reverse=True)
    basic_rows.sort(key=lambda row: str(row.get("trade_date") or ""), reverse=True)
    daily = daily_rows[0]
    basic = basic_rows[0]
    name = symbol
    industry = None
    try:
        stock_rows = _tushare_rows_or_raise(
            tushare_provider.query("stock_basic", {"ts_code": code}, "ts_code,name,industry,list_date", limit=1),
            "stock_basic",
        )
        stock = stock_rows[0]
        raw_name = stock.get("name")
        raw_industry = stock.get("industry")
        if raw_name and str(raw_name).lower() != "nan":
            name = str(raw_name)
        if raw_industry and str(raw_industry).lower() != "nan":
            industry = str(raw_industry)
    except Exception:
        pass
    pe = _safe_float(basic.get("pe_ttm") or basic.get("pe"))
    price = _safe_float(daily.get("close") or basic.get("close"))
    if price is None:
        raise RuntimeError(f"Tushare quote missing price for {symbol}")
    return {
        "symbol": symbol,
        "ts_code": code,
        "name": name,
        "industry": industry,
        "price": price,
        "prev_close": None,
        "change_pct": _safe_float(daily.get("pct_chg")),
        "volume": daily.get("vol"),
        "turnover": daily.get("amount"),
        "turnover_rate": _safe_float(basic.get("turnover_rate")),
        "pe": pe,
        "pe_ttm": _safe_float(basic.get("pe_ttm")),
        "pb": _safe_float(basic.get("pb")),
        "float_market_cap": basic.get("circ_mv"),
        "total_market_cap": basic.get("total_mv"),
        "valuation_band": valuation_band(pe),
        "source": TUSHARE_SOURCE,
        "provider": PROVIDER_NAME,
        "provider_submodule": PROVIDER_SUBMODULE,
        "upstream_provider": "tushare",
        "trade_date": _date_from_tushare(daily.get("trade_date") or basic.get("trade_date")),
    }


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


def fetch_fund_flow_vibe(symbol: str, days: int = 120) -> dict:
    module = _vibe_astock()
    rows = module.stock_fund_flow_120d(symbol)
    rows = rows[-days:] if isinstance(rows, list) else []
    if not rows:
        raise RuntimeError(f"Vibe-Research fund flow returned empty data for {symbol}")
    parsed = [
        {
            "date": row.get("date"),
            "main_net_inflow": row.get("main_net"),
            "small_net_inflow": row.get("small_net"),
            "medium_net_inflow": row.get("mid_net"),
            "large_net_inflow": row.get("large_net"),
            "super_large_net_inflow": row.get("super_net"),
        }
        for row in rows
        if isinstance(row, dict)
    ]
    return {
        "symbol": symbol,
        "source": "vibe_research_stock_fund_flow_120d",
        "rows": parsed,
        "provider": "Vibe-Research",
        "source_submodule": "external/Vibe-Research/backend/astock.py",
    }


def fetch_margin_trading_vibe(symbol: str, days: int = 30) -> dict:
    module = _vibe_astock()
    rows = module.margin_trading(symbol, page_size=days)
    rows = rows if isinstance(rows, list) else []
    if not rows:
        raise RuntimeError(f"Vibe-Research margin trading returned empty data for {symbol}")
    return {
        "symbol": symbol,
        "source": "vibe_research_margin_trading",
        "rows": rows[:days],
        "provider": "Vibe-Research",
        "source_submodule": "external/Vibe-Research/backend/astock.py",
    }


def fetch_liquidity_fallback(symbol: str) -> dict:
    errors: list[str] = []
    for label, fetcher in (
        ("vibe_fund_flow_120d", fetch_fund_flow_vibe),
        ("vibe_margin_trading", fetch_margin_trading_vibe),
        ("quote_liquidity_proxy", fetch_liquidity_proxy),
    ):
        try:
            result = fetcher(symbol)
            if errors:
                result["fallback_errors"] = errors
            if label == "vibe_margin_trading":
                result["proxy"] = True
                result["method"] = "融资融券余额/买入额作为资金拥挤度代理，不等同于主力净流入。"
            return result
        except Exception as exc:  # noqa: BLE001 - provider fallback wrapper
            errors.append(f"{label}: {exc!r}")
    raise RuntimeError("; ".join(errors))


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
    if not parsed:
        raise RuntimeError(f"Eastmoney kline returned empty data for {symbol}")
    _write_price_history_cache(symbol, parsed)
    return {"symbol": symbol, "source": "eastmoney_kline", "rows": parsed}


def fetch_price_history_tushare(symbol: str, days: int = 120) -> dict:
    code = tushare_provider.normalize_ts_code(symbol)
    end = datetime.now()
    start = end - timedelta(days=max(days * 2, 240))
    rows = _tushare_rows_or_raise(
        tushare_provider.query(
            "daily",
            {"ts_code": code, "start_date": _date_to_tushare(start), "end_date": _date_to_tushare(end)},
            "ts_code,trade_date,open,high,low,close,vol,amount,pct_chg",
            limit=days,
        ),
        "daily",
    )
    parsed = [
        {
            "date": _date_from_tushare(row.get("trade_date")),
            "open": _safe_float(row.get("open")),
            "close": _safe_float(row.get("close")),
            "high": _safe_float(row.get("high")),
            "low": _safe_float(row.get("low")),
            "volume": _safe_float(row.get("vol")),
            "turnover": _safe_float(row.get("amount")),
            "change_pct": _safe_float(row.get("pct_chg")),
        }
        for row in rows
    ]
    parsed = [row for row in parsed if row.get("date")]
    parsed.sort(key=lambda row: str(row.get("date")))
    if not _history_rows_usable(parsed, min_rows=min(5, days)):
        raise RuntimeError(f"Tushare daily history unusable for {symbol}")
    _write_price_history_cache(symbol, parsed)
    return {"symbol": symbol, "source": TUSHARE_SOURCE, "rows": parsed[-days:], "upstream_provider": "tushare"}


def fetch_price_history_tencent(symbol: str, days: int = 120) -> dict:
    prefix = "sh" if symbol.startswith("6") else "sz"
    key = f"{prefix}{symbol}"
    payload = get_json(
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        params={"param": f"{key},day,,,{days},qfq"},
        timeout=15,
    )
    data = payload.get("data", {}).get(key, {}) if isinstance(payload, dict) else {}
    rows = data.get("qfqday") or data.get("day") or []
    parsed = []
    for row in rows[-days:]:
        if isinstance(row, list) and len(row) >= 6:
            parsed.append(
                {
                    "date": row[0],
                    "open": _safe_float(row[1]),
                    "close": _safe_float(row[2]),
                    "high": _safe_float(row[3]),
                    "low": _safe_float(row[4]),
                    "volume": _safe_float(row[5]),
                    "turnover": None,
                    "change_pct": None,
                }
            )
    if not parsed:
        raise RuntimeError(f"Tencent kline returned empty data for {symbol}")
    _write_price_history_cache(symbol, parsed)
    return {"symbol": symbol, "source": "tencent_qfq_kline", "rows": parsed}


def fetch_price_history_efinance(symbol: str, days: int = 120) -> dict:
    try:
        import efinance as ef  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("efinance unavailable") from exc

    end = datetime.now().strftime("%Y%m%d")
    begin = (datetime.now() - timedelta(days=max(days * 2, 240))).strftime("%Y%m%d")
    df = ef.stock.get_quote_history(symbol, beg=begin, end=end, klt=101, fqt=1)
    if df is None or getattr(df, "empty", True):
        raise RuntimeError(f"efinance returned empty history for {symbol}")
    parsed = []
    for row in df.tail(days).to_dict("records"):
        parsed.append(
            {
                "date": row.get("日期") or row.get("date"),
                "open": _safe_float(row.get("开盘") or row.get("open")),
                "close": _safe_float(row.get("收盘") or row.get("close")),
                "high": _safe_float(row.get("最高") or row.get("high")),
                "low": _safe_float(row.get("最低") or row.get("low")),
                "volume": _safe_float(row.get("成交量") or row.get("volume")),
                "turnover": _safe_float(row.get("成交额") or row.get("turnover")),
                "change_pct": _safe_float(row.get("涨跌幅") or row.get("change_pct")),
            }
        )
    if not _history_rows_usable(parsed):
        raise RuntimeError(f"efinance history unusable for {symbol}")
    _write_price_history_cache(symbol, parsed)
    return {"symbol": symbol, "source": "efinance_quote_history", "rows": parsed}


def fetch_price_history_baostock(symbol: str, days: int = 120) -> dict:
    try:
        import baostock as bs  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("baostock unavailable") from exc

    code = f"{'sh' if symbol.startswith(('6', '9')) else 'sz'}.{symbol}"
    start = (datetime.now() - timedelta(days=max(days * 2, 240))).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    login = bs.login()
    try:
        if getattr(login, "error_code", "0") != "0":
            raise RuntimeError(f"baostock login failed: {getattr(login, 'error_msg', '')}")
        rs = bs.query_history_k_data_plus(
            code,
            "date,open,high,low,close,volume,amount,pctChg",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag="2",
        )
        rows = []
        while rs.next():
            rows.append(rs.get_row_data())
        if getattr(rs, "error_code", "0") != "0":
            raise RuntimeError(f"baostock query failed: {getattr(rs, 'error_msg', '')}")
    finally:
        bs.logout()
    parsed = []
    for row in rows[-days:]:
        if len(row) < 8:
            continue
        parsed.append(
            {
                "date": row[0],
                "open": _safe_float(row[1]),
                "high": _safe_float(row[2]),
                "low": _safe_float(row[3]),
                "close": _safe_float(row[4]),
                "volume": _safe_float(row[5]),
                "turnover": _safe_float(row[6]),
                "change_pct": _safe_float(row[7]),
            }
        )
    if not _history_rows_usable(parsed):
        raise RuntimeError(f"baostock history unusable for {symbol}")
    _write_price_history_cache(symbol, parsed)
    return {"symbol": symbol, "source": "baostock_qfq_kline", "rows": parsed}


def fetch_price_history_fallback(symbol: str, days: int = 120) -> dict:
    path = _history_cache_path(symbol)
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
    rows = parsed[-days:]
    if not _history_rows_usable(rows, min_rows=min(5, days)):
        raise RuntimeError(f"local hist unusable for {symbol}: {path}")
    return {"symbol": symbol, "source": "local_a_data_hist", "rows": rows}


def fetch_price_history_cached_or_live(symbol: str, days: int = 120, *, max_lag_days: int = 0) -> dict:
    cached: dict | None = None
    try:
        cached = fetch_price_history_fallback(symbol, days=days)
        if not _history_is_stale(cached, max_lag_days=max_lag_days):
            return cached
    except Exception:
        cached = None

    errors: list[str] = []
    for label, fetcher in (
        ("price_history_tushare", fetch_price_history_tushare),
        ("price_history_tencent", fetch_price_history_tencent),
        ("price_history_efinance", fetch_price_history_efinance),
        ("price_history_baostock", fetch_price_history_baostock),
    ):
        try:
            history = fetcher(symbol, days=days)
            if not _history_is_stale(history, max_lag_days=max_lag_days):
                history["refreshed_cache"] = True
                return history
            errors.append(f"{label}:stale:{_history_latest_date(history)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{label}:{exc!r}")

    if cached is not None:
        cached["stale_cache"] = True
        cached["refresh_errors"] = errors
        return cached
    raise RuntimeError(f"no usable price history for {symbol}; refresh_errors={errors[:3]}")


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
    if rows:
        return {"symbol": symbol, "source": "eastmoney_dragon_tiger", "rows": rows[:10]}
    if symbol:
        return fetch_dragon_tiger_vibe(symbol, date=date)
    return {"symbol": symbol, "source": "eastmoney_dragon_tiger", "rows": rows[:10]}


def fetch_dragon_tiger_vibe(symbol: str, date: str | None = None, look_back: int = 30) -> dict:
    module = _vibe_astock()
    payload = module.dragon_tiger_board(symbol, trade_date=date, look_back=look_back)
    records = payload.get("records", []) if isinstance(payload, dict) else []
    if not isinstance(records, list):
        records = []
    return {
        "symbol": symbol,
        "source": "vibe_research_dragon_tiger_30d",
        "rows": records,
        "seats": payload.get("seats", {}) if isinstance(payload, dict) else {},
        "institution": payload.get("institution", {}) if isinstance(payload, dict) else {},
        "provider": "Vibe-Research",
        "source_submodule": "external/Vibe-Research/backend/astock.py",
        "look_back_days": look_back,
    }


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


def _tushare_bundle_section(bundle: dict, key: str) -> list[dict]:
    result = bundle.get("results", {}).get(key, {}) if isinstance(bundle, dict) else {}
    rows = result.get("rows") if isinstance(result, dict) else []
    return rows if isinstance(rows, list) else []


def _tushare_bundle_errors(bundle: dict, prefix: str) -> list[str]:
    errors = bundle.get("errors", []) if isinstance(bundle, dict) else []
    if not isinstance(errors, list):
        return []
    return [f"{prefix}:{item}" for item in errors]


def fetch_basic_info_tushare(symbol: str) -> dict:
    bundle = tushare_provider.fetch_company_profile(symbol)
    company_rows = _tushare_bundle_section(bundle, "stock_company")
    if not company_rows:
        raise RuntimeError(f"Tushare company profile empty for {symbol}")
    row = company_rows[0]
    return {
        "symbol": symbol,
        "ts_code": tushare_provider.normalize_ts_code(symbol),
        "source": TUSHARE_SOURCE,
        "upstream_provider": "tushare",
        "name": row.get("shortname") or symbol,
        "chairman": row.get("chairman"),
        "manager": row.get("manager"),
        "secretary": row.get("secretary"),
        "reg_capital": row.get("reg_capital"),
        "setup_date": _date_from_tushare(row.get("setup_date")),
        "province": row.get("province"),
        "city": row.get("city"),
        "industry": row.get("industry"),
        "main_business": row.get("main_business"),
        "business_scope": row.get("business_scope"),
        "namechange": _tushare_bundle_section(bundle, "namechange"),
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


def fetch_liquidity_tushare(symbol: str, days: int = 120) -> dict:
    code = tushare_provider.normalize_ts_code(symbol)
    end = datetime.now()
    start = end - timedelta(days=max(days * 2, 240))
    rows = _tushare_rows_or_raise(
        tushare_provider.query(
            "moneyflow",
            {"ts_code": code, "start_date": _date_to_tushare(start), "end_date": _date_to_tushare(end)},
            "ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount,buy_lg_amount,sell_lg_amount,buy_elg_amount,sell_elg_amount,net_mf_amount",
            limit=days,
        ),
        "moneyflow",
    )
    parsed = [
        {
            "date": _date_from_tushare(row.get("trade_date")),
            "main_net_inflow": _safe_float(row.get("net_mf_amount")),
            "small_buy_amount": _safe_float(row.get("buy_sm_amount")),
            "small_sell_amount": _safe_float(row.get("sell_sm_amount")),
            "medium_buy_amount": _safe_float(row.get("buy_md_amount")),
            "medium_sell_amount": _safe_float(row.get("sell_md_amount")),
            "large_buy_amount": _safe_float(row.get("buy_lg_amount")),
            "large_sell_amount": _safe_float(row.get("sell_lg_amount")),
            "extra_large_buy_amount": _safe_float(row.get("buy_elg_amount")),
            "extra_large_sell_amount": _safe_float(row.get("sell_elg_amount")),
        }
        for row in rows
    ]
    parsed = [row for row in parsed if row.get("date")]
    parsed.sort(key=lambda row: str(row.get("date")))
    return {"symbol": symbol, "source": TUSHARE_SOURCE, "rows": parsed[-days:], "upstream_provider": "tushare"}


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


def fetch_financials_tushare(symbol: str, periods: int = 4) -> dict:
    code = tushare_provider.normalize_ts_code(symbol)
    statements: dict[str, list[dict]] = {}
    errors: list[str] = []
    queries = {
        "income": (
            "income",
            "ts_code,ann_date,f_ann_date,end_date,report_type,total_revenue,revenue,total_cogs,operate_profit,n_income,n_income_attr_p,basic_eps,diluted_eps",
        ),
        "balance": (
            "balancesheet",
            "ts_code,ann_date,end_date,total_assets,total_liab,total_hldr_eqy_exc_min_int,money_cap,accounts_receiv,inventories,total_cur_assets,total_cur_liab",
        ),
        "cashflow": (
            "cashflow",
            "ts_code,ann_date,end_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,c_fr_sale_sg,free_cashflow",
        ),
        "indicators": (
            "fina_indicator",
            "ts_code,ann_date,end_date,eps,roe,roe_waa,roa,grossprofit_margin,netprofit_margin,debt_to_assets,or_yoy,netprofit_yoy",
        ),
        "forecast": (
            "forecast",
            "ts_code,ann_date,end_date,type,p_change_min,p_change_max,net_profit_min,net_profit_max",
        ),
        "express": (
            "express",
            "ts_code,ann_date,end_date,revenue,n_income,total_assets,diluted_eps",
        ),
        "dividend": (
            "dividend",
            "ts_code,end_date,ann_date,div_proc,cash_div,record_date,ex_date,pay_date",
        ),
    }
    for key, (api_name, fields) in queries.items():
        result = tushare_provider.query(api_name, {"ts_code": code}, fields, limit=periods)
        if result.get("status") in {"ok", "ok_empty"}:
            statements[key] = result.get("rows", []) if isinstance(result.get("rows"), list) else []
        else:
            statements[key] = []
            errors.append(f"{key}: {result.get('status')}: {result.get('error', '')}")
    if not any(statements.values()):
        raise RuntimeError(f"Tushare financials returned no usable rows for {symbol}: {'; '.join(errors)}")
    return {"symbol": symbol, "ts_code": code, "source": TUSHARE_SOURCE, "upstream_provider": "tushare", "statements": statements, "errors": errors}


def fetch_dragon_tiger_tushare(symbol: str, date: str | None = None) -> dict:
    params = {"trade_date": date.replace("-", "") if date else datetime.now().strftime("%Y%m%d")}
    rows = _tushare_rows_or_raise(
        tushare_provider.query(
            "top_list",
            params,
            "trade_date,ts_code,name,close,pct_change,turnover_rate,amount,l_sell,l_buy,l_amount,net_amount,reason",
            limit=120,
        ),
        "top_list",
    )
    code = tushare_provider.normalize_ts_code(symbol)
    rows = [row for row in rows if row.get("ts_code") == code]
    return {"symbol": symbol, "source": TUSHARE_SOURCE, "rows": rows[:10], "upstream_provider": "tushare"}


def fetch_market_activity_tushare(symbol: str) -> dict:
    code = tushare_provider.normalize_ts_code(symbol)
    bundle = tushare_provider.fetch_market_activity(symbol, trade_date=datetime.now().strftime("%Y%m%d"))
    rows = {
        key: value.get("rows", [])
        for key, value in bundle.get("results", {}).items()
        if isinstance(value, dict)
    }
    if not any(rows.values()):
        raise RuntimeError(f"Tushare market activity empty for {symbol}")
    return {
        "symbol": symbol,
        "ts_code": code,
        "source": TUSHARE_SOURCE,
        "upstream_provider": "tushare",
        "rows": rows.get("margin_detail", []),
        "sections": rows,
        "errors": _tushare_bundle_errors(bundle, "market_activity"),
    }


def fetch_stock_supplement_tushare(symbol: str) -> dict:
    result: dict[str, object] = {
        "symbol": symbol,
        "provider": PROVIDER_NAME,
        "provider_submodule": PROVIDER_SUBMODULE,
        "source": TUSHARE_SOURCE,
        "upstream_provider": "tushare",
        "fundamental": {},
        "announcements": {},
        "fund_flow": {},
        "price_history": {},
        "dragon_tiger": {},
        "financials": {},
        "research_reports": {},
        "margin_trading": {},
        "concept_blocks": {},
        "valuation_percentile": {},
        "capital_actions": {},
        "catalysts": [],
        "risks": [],
        "errors": [],
    }
    for key, fetcher in (
        ("fundamental", fetch_basic_info_tushare),
        ("fund_flow", fetch_liquidity_tushare),
        ("price_history", fetch_price_history_tushare),
        ("dragon_tiger", fetch_dragon_tiger_tushare),
        ("financials", fetch_financials_tushare),
        ("margin_trading", fetch_market_activity_tushare),
    ):
        try:
            result[key] = fetcher(symbol)
        except Exception as exc:  # noqa: BLE001 - provider boundary
            result["errors"].append(f"tushare_{key}: {exc!r}")  # type: ignore[index]
    try:
        bundle = tushare_provider.fetch_capital_actions(
            symbol,
            period=datetime.now().strftime("%Y") + "0331",
            start_date=(datetime.now() - timedelta(days=540)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
        )
        result["capital_actions"] = bundle
        result["errors"].extend(_tushare_bundle_errors(bundle, "capital_actions"))  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"tushare_capital_actions: {exc!r}")  # type: ignore[index]
    if not stock_supplement_usable(result):
        raise RuntimeError(f"Tushare supplement unusable for {symbol}: {result.get('errors')}")
    _write_supplement_cache(symbol, result)
    return result


def fetch_stock_supplement_public_backfill(symbol: str) -> dict:
    result: dict[str, object] = {
        "symbol": symbol,
        "provider": PROVIDER_NAME,
        "provider_submodule": PROVIDER_SUBMODULE,
        "source": "public_backfill",
        "announcements": {},
        "research_reports": {},
        "concept_blocks": {},
        "valuation_percentile": {},
        "errors": [],
    }
    for key, fetcher in (
        ("announcements", fetch_announcements),
        ("research_reports", fetch_stock_research_reports),
        ("concept_blocks", fetch_concept_blocks_vibe),
        ("valuation_percentile", fetch_valuation_percentile_vibe),
    ):
        try:
            result[key] = fetcher(symbol)
        except Exception as exc:  # noqa: BLE001 - non-blocking backfill
            result["errors"].append(f"public_backfill_{key}: {exc!r}")  # type: ignore[index]
    return result


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


def fetch_concept_blocks_vibe(symbol: str) -> dict:
    module = _vibe_astock()
    payload = module.concept_blocks(symbol)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Vibe-Research concept blocks unusable for {symbol}")
    return {
        "symbol": symbol,
        "source": "vibe_research_concept_blocks",
        "total": payload.get("total", 0),
        "rows": payload.get("boards", []) if isinstance(payload.get("boards"), list) else [],
        "concept_tags": payload.get("concept_tags", []) if isinstance(payload.get("concept_tags"), list) else [],
        "provider": "Vibe-Research",
        "source_submodule": "external/Vibe-Research/backend/astock.py",
    }


def fetch_valuation_percentile_vibe(symbol: str) -> dict:
    module = _vibe_astock()
    payload = module.valuation_percentile(symbol)
    if not isinstance(payload, dict) or not payload.get("metrics"):
        raise RuntimeError(f"Vibe-Research valuation percentile unavailable for {symbol}")
    payload = dict(payload)
    payload.update(
        {
            "symbol": symbol,
            "source": "vibe_research_valuation_percentile",
            "provider": "Vibe-Research",
            "source_submodule": "external/Vibe-Research/backend/astock.py",
        }
    )
    return payload


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
        "margin_trading": {},
        "concept_blocks": {},
        "valuation_percentile": {},
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
            result["fund_flow"] = fetch_liquidity_fallback(symbol)
        except Exception as fallback_exc:
            result["errors"].append(f"fund_flow_fallback: {fallback_exc!r}")  # type: ignore[index]
    try:
        result["price_history"] = fetch_price_history(symbol)
    except Exception as exc:
        result["errors"].append(f"price_history: {exc!r}")  # type: ignore[index]
        for label, fetcher in (
            ("price_history_tencent", fetch_price_history_tencent),
            ("price_history_efinance", fetch_price_history_efinance),
            ("price_history_baostock", fetch_price_history_baostock),
            ("price_history_fallback", fetch_price_history_fallback),
        ):
            try:
                result["price_history"] = fetcher(symbol)
                break
            except Exception as fallback_exc:
                result["errors"].append(f"{label}: {fallback_exc!r}")  # type: ignore[index]
    try:
        result["dragon_tiger"] = fetch_dragon_tiger(symbol)
    except Exception as exc:
        result["errors"].append(f"dragon_tiger: {exc!r}")  # type: ignore[index]
    try:
        result["margin_trading"] = fetch_margin_trading_vibe(symbol)
    except Exception as exc:
        result["errors"].append(f"margin_trading: {exc!r}")  # type: ignore[index]
    try:
        result["concept_blocks"] = fetch_concept_blocks_vibe(symbol)
    except Exception as exc:
        result["errors"].append(f"concept_blocks: {exc!r}")  # type: ignore[index]
    try:
        result["valuation_percentile"] = fetch_valuation_percentile_vibe(symbol)
    except Exception as exc:
        result["errors"].append(f"valuation_percentile: {exc!r}")  # type: ignore[index]
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
    _write_supplement_cache(symbol, result)
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
                "adapter_strategy": "tushare -> tencent/eastmoney -> efinance/baostock -> configured local a-data cache",
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
