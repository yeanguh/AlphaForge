from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable

from loop_os.schemas.provider import ProviderResult


PROVIDER_NAME = "tushare"
TOKEN_ENV = "TUSHARE_TOKEN"

_PRO = None

API_CATALOG: dict[str, list[str]] = {
    "company": [
        "stock_basic",
        "stock_company",
        "namechange",
        "trade_cal",
        "hs_const",
        "new_share",
        "bak_basic",
    ],
    "market": [
        "pro_bar",
        "daily",
        "weekly",
        "monthly",
        "adj_factor",
        "daily_basic",
        "moneyflow",
        "suspend_d",
    ],
    "financial": [
        "income",
        "balancesheet",
        "cashflow",
        "fina_indicator",
        "fina_mainbz",
        "disclosure_date",
        "fina_audit",
        "forecast",
        "express",
        "dividend",
    ],
    "ownership": [
        "top10_holders",
        "top10_floatholders",
        "stk_holdernumber",
        "stk_holdertrade",
        "pledge_stat",
        "pledge_detail",
        "repurchase",
    ],
    "activity": [
        "margin",
        "margin_detail",
        "block_trade",
        "top_list",
        "top_inst",
    ],
    "index_fund": [
        "index_basic",
        "index_daily",
        "index_weight",
        "fund_basic",
        "fund_daily",
        "fund_adj",
        "fund_share",
        "fund_nav",
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _import_tushare():
    try:
        import tushare as ts  # type: ignore
    except Exception as exc:  # noqa: BLE001 - optional provider dependency
        raise RuntimeError("tushare package is not installed; run with project dependencies") from exc
    return ts


def is_configured() -> bool:
    return bool(os.environ.get(TOKEN_ENV))


def _get_pro():
    global _PRO
    if _PRO is not None:
        return _PRO
    token = os.environ.get(TOKEN_ENV)
    if not token:
        raise RuntimeError(f"{TOKEN_ENV} is not configured")
    ts = _import_tushare()
    ts.set_token(token)
    _PRO = ts.pro_api()
    return _PRO


def _df_to_rows(df: Any, *, limit: int | None = None) -> list[dict[str, Any]]:
    if df is None:
        return []
    if hasattr(df, "to_dict"):
        records = df.to_dict("records")
    elif isinstance(df, list):
        records = df
    else:
        return []
    if not isinstance(records, list):
        return []
    rows = [row for row in records if isinstance(row, dict)]
    return rows[:limit] if limit is not None else rows


def _row_count(df: Any) -> int:
    try:
        return int(len(df))
    except Exception:
        return len(_df_to_rows(df))


def normalize_ts_code(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if not raw:
        return raw
    if "." in raw:
        return raw
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != 6:
        return raw
    if digits.startswith(("6", "9")):
        return f"{digits}.SH"
    if digits.startswith(("0", "1", "2", "3")):
        return f"{digits}.SZ"
    if digits.startswith(("4", "8")):
        return f"{digits}.BJ"
    return raw


def _call(api_name: str, params: dict[str, Any] | None = None, fields: str | None = None):
    pro = _get_pro()
    params = dict(params or {})
    if fields:
        params["fields"] = fields
    method = getattr(pro, api_name, None)
    if callable(method):
        return method(**params)
    return pro.query(api_name, **params)


def query(
    api_name: str,
    params: dict[str, Any] | None = None,
    fields: str | None = None,
    *,
    limit: int | None = None,
    safe: bool = True,
) -> dict[str, Any]:
    """Call a Tushare Pro API and return a portable dictionary.

    The adapter intentionally does not cache outside the repository and does
    not expose tokens. Permission/IP/empty-data cases are returned as data so
    callers can degrade gracefully.
    """
    try:
        df = _call(api_name, params, fields)
        rows = _df_to_rows(df, limit=limit)
        return {
            "provider": PROVIDER_NAME,
            "api": api_name,
            "status": "ok" if _row_count(df) else "ok_empty",
            "row_count": _row_count(df),
            "rows": rows,
            "fields": list(rows[0].keys()) if rows else [],
            "params": dict(params or {}),
            "checked_at": _now_iso(),
        }
    except Exception as exc:  # noqa: BLE001 - provider boundary
        if not safe:
            raise
        message = str(exc)
        if "没有接口" in message or "访问权限" in message:
            status = "permission_denied"
        elif "IP数量超限" in message:
            status = "ip_limited"
        elif TOKEN_ENV in message:
            status = "not_configured"
        else:
            status = "error"
        return {
            "provider": PROVIDER_NAME,
            "api": api_name,
            "status": status,
            "row_count": 0,
            "rows": [],
            "fields": [],
            "params": dict(params or {}),
            "error": message,
            "checked_at": _now_iso(),
        }


def query_pro_bar(
    ts_code: str,
    *,
    start_date: str,
    end_date: str,
    adj: str = "qfq",
    limit: int | None = None,
    safe: bool = True,
) -> dict[str, Any]:
    try:
        token = os.environ.get(TOKEN_ENV)
        if not token:
            raise RuntimeError(f"{TOKEN_ENV} is not configured")
        ts = _import_tushare()
        ts.set_token(token)
        df = ts.pro_bar(ts_code=normalize_ts_code(ts_code), start_date=start_date, end_date=end_date, adj=adj)
        rows = _df_to_rows(df, limit=limit)
        return {
            "provider": PROVIDER_NAME,
            "api": "pro_bar",
            "status": "ok" if _row_count(df) else "ok_empty",
            "row_count": _row_count(df),
            "rows": rows,
            "fields": list(rows[0].keys()) if rows else [],
            "params": {"ts_code": normalize_ts_code(ts_code), "start_date": start_date, "end_date": end_date, "adj": adj},
            "checked_at": _now_iso(),
        }
    except Exception as exc:  # noqa: BLE001 - provider boundary
        if not safe:
            raise
        return {
            "provider": PROVIDER_NAME,
            "api": "pro_bar",
            "status": "error",
            "row_count": 0,
            "rows": [],
            "fields": [],
            "params": {"ts_code": normalize_ts_code(ts_code), "start_date": start_date, "end_date": end_date, "adj": adj},
            "error": str(exc),
            "checked_at": _now_iso(),
        }


def capabilities() -> dict[str, Any]:
    """Return the provider's portable capability map without touching the SDK."""
    return {
        "provider": PROVIDER_NAME,
        "token_env": TOKEN_ENV,
        "configured": is_configured(),
        "api_catalog": {group: list(apis) for group, apis in API_CATALOG.items()},
        "notes": [
            "Tushare Pro is an optional enhancement source.",
            "Missing tokens, permission gaps, IP limits, or empty data are returned as provider statuses.",
        ],
    }


def _bundle(items: list[tuple[str, Callable[[], dict[str, Any]]]]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    errors: list[str] = []
    ok = 0
    for name, fn in items:
        result = fn()
        results[name] = result
        status = result.get("status")
        if status in {"ok", "ok_empty"}:
            ok += 1
        elif status not in {"not_configured"}:
            errors.append(f"{name}:{status}:{result.get('error', '')}")
    if ok == len(items):
        status = "ok"
    elif ok > 0:
        status = "partial"
    else:
        status = "error"
    return {
        "provider": PROVIDER_NAME,
        "status": status,
        "results": results,
        "errors": errors,
        "checked_at": _now_iso(),
    }


def fetch_company_profile(ts_code: str) -> dict[str, Any]:
    code = normalize_ts_code(ts_code)
    return _bundle(
        [
            (
                "stock_company",
                lambda: query(
                    "stock_company",
                    {"ts_code": code},
                    "ts_code,chairman,manager,secretary,reg_capital,setup_date,province,city,main_business,business_scope",
                    limit=5,
                ),
            ),
            (
                "namechange",
                lambda: query("namechange", {"ts_code": code}, "ts_code,name,start_date,end_date,change_reason", limit=20),
            ),
        ]
    )


def fetch_listing_reference(*, trade_date: str | None = None) -> dict[str, Any]:
    return _bundle(
        [
            (
                "stock_basic",
                lambda: query(
                    "stock_basic",
                    {"list_status": "L"},
                    "ts_code,symbol,name,area,industry,market,exchange,list_date,is_hs",
                    limit=6000,
                ),
            ),
            (
                "trade_cal",
                lambda: query(
                    "trade_cal",
                    {"exchange": "SSE", **({"cal_date": trade_date} if trade_date else {})},
                    "exchange,cal_date,is_open,pretrade_date",
                    limit=366,
                ),
            ),
            (
                "hs_const",
                lambda: query("hs_const", {"hs_type": "SH"}, "ts_code,hs_type,in_date,out_date,is_new", limit=600),
            ),
            (
                "new_share",
                lambda: query(
                    "new_share",
                    {"start_date": trade_date, "end_date": trade_date} if trade_date else {},
                    "ts_code,sub_code,name,ipo_date,issue_date,amount,market_amount,price,pe,limit_amount",
                    limit=120,
                ),
            ),
        ]
    )


def fetch_market_snapshot(ts_code: str, *, start_date: str, end_date: str) -> dict[str, Any]:
    code = normalize_ts_code(ts_code)
    return _bundle(
        [
            ("daily", lambda: query("daily", {"ts_code": code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,open,high,low,close,vol,amount,pct_chg", limit=260)),
            ("weekly", lambda: query("weekly", {"ts_code": code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,open,high,low,close,vol,amount,pct_chg", limit=120)),
            ("monthly", lambda: query("monthly", {"ts_code": code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,open,high,low,close,vol,amount,pct_chg", limit=120)),
            ("adj_factor", lambda: query("adj_factor", {"ts_code": code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,adj_factor", limit=260)),
            ("daily_basic", lambda: query("daily_basic", {"ts_code": code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,close,pe,pe_ttm,pb,ps,ps_ttm,total_mv,circ_mv,turnover_rate", limit=260)),
            ("moneyflow", lambda: query("moneyflow", {"ts_code": code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_lg_amount,sell_lg_amount,net_mf_amount", limit=260)),
            ("suspend_d", lambda: query("suspend_d", {"ts_code": code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,suspend_timing,suspend_type", limit=120)),
        ]
    )


def fetch_financial_bundle(ts_code: str, *, period: str) -> dict[str, Any]:
    code = normalize_ts_code(ts_code)
    return _bundle(
        [
            ("income", lambda: query("income", {"ts_code": code, "period": period}, "ts_code,ann_date,f_ann_date,end_date,report_type,total_revenue,revenue,total_cogs,operate_profit,n_income,n_income_attr_p,basic_eps,diluted_eps", limit=20)),
            ("balancesheet", lambda: query("balancesheet", {"ts_code": code, "period": period}, "ts_code,ann_date,end_date,total_assets,total_liab,total_hldr_eqy_exc_min_int,money_cap,accounts_receiv,inventories,total_cur_assets,total_cur_liab", limit=20)),
            ("cashflow", lambda: query("cashflow", {"ts_code": code, "period": period}, "ts_code,ann_date,end_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,c_fr_sale_sg,free_cashflow", limit=20)),
            ("fina_indicator", lambda: query("fina_indicator", {"ts_code": code, "period": period}, "ts_code,ann_date,end_date,eps,roe,roe_waa,roa,grossprofit_margin,netprofit_margin,debt_to_assets,or_yoy,netprofit_yoy", limit=20)),
            ("fina_mainbz", lambda: query("fina_mainbz", {"ts_code": code, "period": period[:4] + "1231", "type": "P"}, "ts_code,end_date,bz_item,bz_sales,bz_profit,bz_cost,curr_type", limit=80)),
            ("disclosure_date", lambda: query("disclosure_date", {"ts_code": code, "end_date": period}, "ts_code,ann_date,end_date,pre_date,actual_date,modify_date", limit=20)),
            ("fina_audit", lambda: query("fina_audit", {"ts_code": code, "period": period[:4] + "1231"}, "ts_code,ann_date,end_date,audit_result,audit_fees,audit_agency", limit=20)),
        ]
    )


def fetch_capital_actions(ts_code: str, *, period: str, start_date: str, end_date: str) -> dict[str, Any]:
    code = normalize_ts_code(ts_code)
    return _bundle(
        [
            ("forecast", lambda: query("forecast", {"ts_code": code, "period": period}, "ts_code,ann_date,end_date,type,p_change_min,p_change_max,net_profit_min,net_profit_max", limit=30)),
            ("express", lambda: query("express", {"ts_code": code, "period": period}, "ts_code,ann_date,end_date,revenue,n_income,total_assets,diluted_eps", limit=30)),
            ("dividend", lambda: query("dividend", {"ts_code": code}, "ts_code,end_date,ann_date,div_proc,cash_div,record_date,ex_date,pay_date", limit=80)),
            ("top10_holders", lambda: query("top10_holders", {"ts_code": code, "period": period}, "ts_code,ann_date,end_date,holder_name,hold_amount,hold_ratio", limit=30)),
            ("top10_floatholders", lambda: query("top10_floatholders", {"ts_code": code, "period": period}, "ts_code,ann_date,end_date,holder_name,hold_amount,hold_ratio", limit=30)),
            ("stk_holdernumber", lambda: query("stk_holdernumber", {"ts_code": code, "enddate": period}, "ts_code,ann_date,end_date,holder_num", limit=40)),
            ("stk_holdertrade", lambda: query("stk_holdertrade", {"ts_code": code, "start_date": start_date, "end_date": end_date}, "ts_code,ann_date,holder_name,in_de,change_vol,change_ratio,after_share", limit=80)),
            ("pledge_stat", lambda: query("pledge_stat", {"ts_code": code}, "ts_code,end_date,pledge_count,unrest_pledge,p_total_ratio", limit=80)),
            ("pledge_detail", lambda: query("pledge_detail", {"ts_code": code}, "ts_code,ann_date,holder_name,pledge_amount,start_date,end_date", limit=80)),
            ("repurchase", lambda: query("repurchase", {"ts_code": code}, "ts_code,ann_date,end_date,proc,vol,amount", limit=80)),
        ]
    )


def fetch_market_activity(ts_code: str, *, trade_date: str) -> dict[str, Any]:
    code = normalize_ts_code(ts_code)
    return _bundle(
        [
            ("margin", lambda: query("margin", {"trade_date": trade_date}, "trade_date,exchange_id,rzye,rzmre,rqyl,rqye,rzrqye", limit=10)),
            ("margin_detail", lambda: query("margin_detail", {"ts_code": code, "trade_date": trade_date}, "trade_date,ts_code,name,rzye,rqyl,rzrqye", limit=20)),
            ("block_trade", lambda: query("block_trade", {"ts_code": code}, "ts_code,trade_date,price,vol,amount,buyer,seller", limit=80)),
            ("top_list", lambda: query("top_list", {"trade_date": trade_date}, "trade_date,ts_code,name,close,pct_change,turnover_rate,amount", limit=120)),
            ("top_inst", lambda: query("top_inst", {"trade_date": trade_date}, "trade_date,ts_code,exalter,buy,buy_rate,sell,sell_rate,net_buy", limit=120)),
        ]
    )


def fetch_index_fund_bundle(*, index_code: str = "000300.SH", fund_code: str = "510300.SH", start_date: str, end_date: str) -> dict[str, Any]:
    return _bundle(
        [
            ("index_basic", lambda: query("index_basic", {"market": "SSE"}, "ts_code,name,market,publisher,category,base_date,base_point,list_date", limit=300)),
            ("index_daily", lambda: query("index_daily", {"ts_code": index_code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,open,high,low,close,vol,amount", limit=260)),
            ("index_weight", lambda: query("index_weight", {"index_code": index_code, "start_date": start_date, "end_date": end_date}, "index_code,con_code,trade_date,weight", limit=600)),
            ("fund_basic", lambda: query("fund_basic", {"market": "E"}, "ts_code,name,management,custodian,fund_type,found_date,market,type", limit=5000)),
            ("fund_daily", lambda: query("fund_daily", {"ts_code": fund_code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,open,high,low,close,vol,amount", limit=260)),
            ("fund_adj", lambda: query("fund_adj", {"ts_code": fund_code, "end_date": end_date}, "ts_code,trade_date,adj_factor", limit=260)),
            ("fund_share", lambda: query("fund_share", {"ts_code": fund_code, "start_date": start_date, "end_date": end_date}, "ts_code,trade_date,fd_share", limit=260)),
            ("fund_nav", lambda: query("fund_nav", {"ts_code": fund_code, "end_date": end_date}, "ts_code,end_date,unit_nav,accum_nav,adj_nav", limit=260)),
        ]
    )


def smoke(live: bool = False) -> ProviderResult:
    if not is_configured():
        return ProviderResult(PROVIDER_NAME, "warn", f"{TOKEN_ENV} not configured; Tushare enhancement disabled")
    try:
        _import_tushare()
    except RuntimeError as exc:
        return ProviderResult(PROVIDER_NAME, "error", "tushare package missing", errors=[str(exc)])
    if not live:
        return ProviderResult(
            PROVIDER_NAME,
            "ok",
            "Tushare SDK available; live calls require TUSHARE_TOKEN permissions",
            {"configured": True, "key_gated": True},
        )
    probes = {
        "stock_basic": query("stock_basic", {"list_status": "L"}, "ts_code,name,industry,list_date", limit=3),
        "daily_basic": query("daily_basic", {"ts_code": "002837.SZ", "start_date": "20260701", "end_date": "20260710"}, "ts_code,trade_date,pe,pb,total_mv", limit=3),
        "income": query("income", {"ts_code": "002837.SZ", "period": "20260331"}, "ts_code,ann_date,end_date,total_revenue,n_income_attr_p", limit=3),
    }
    ok_count = sum(1 for item in probes.values() if item.get("status") in {"ok", "ok_empty"})
    status = "ok" if ok_count == len(probes) else "warn" if ok_count else "error"
    errors = [f"{name}:{item.get('status')}:{item.get('error', '')}" for name, item in probes.items() if item.get("status") not in {"ok", "ok_empty"}]
    return ProviderResult(
        PROVIDER_NAME,
        status,
        f"Tushare live probes succeeded {ok_count}/{len(probes)}",
        {"probes": {name: {"status": item.get("status"), "row_count": item.get("row_count")} for name, item in probes.items()}},
        errors=errors,
    )
