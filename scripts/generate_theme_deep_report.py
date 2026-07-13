from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loop_os.report_router import BENCHMARK_REPORT_SECTIONS, resolve_theme_key  # noqa: E402
from providers.open_source import a_stock_data, pdf_text  # noqa: E402


KNOWN_A_SHARE_SYMBOLS = {
    "兴森科技": "002436",
    "安集科技": "688019",
    "通富微电": "002156",
    "寒武纪": "688256",
    "深南电路": "002916",
    "中际旭创": "300308",
    "新易盛": "300502",
    "英维克": "002837",
    "沪电股份": "002463",
    "胜宏科技": "300476",
    "工业富联": "601138",
    "华特气体": "688268",
    "彤程新材": "603650",
    "光迅科技": "002281",
    "天孚通信": "300394",
    "浪潮信息": "000977",
    "紫光股份": "000938",
    "中科曙光": "603019",
    "申菱环境": "301018",
    "高澜股份": "300499",
    "海光信息": "688041",
    "龙芯中科": "688047",
    "长电科技": "600584",
    "华天科技": "002185",
    "绿的谐波": "688017",
    "双环传动": "002472",
    "中大力德": "002896",
    "秦川机床": "000837",
    "贝斯特": "300580",
    "五洲新春": "603667",
    "鸣志电器": "603728",
    "汇川技术": "300124",
    "雷赛智能": "002979",
    "禾川科技": "688320",
    "埃斯顿": "002747",
    "机器人": "300024",
    "华中数控": "300161",
    "华辰装备": "300809",
    "日发精机": "002520",
    "科大讯飞": "002230",
    "金山办公": "688111",
    "用友网络": "600588",
    "泛微网络": "603039",
    "三六零": "601360",
    "启明星辰": "002439",
    "深信服": "300454",
    "安恒信息": "688023",
    "药明康德": "603259",
    "迈瑞医疗": "300760",
    "联影医疗": "688271",
    "中控技术": "688777",
    "柏楚电子": "688188",
    "赛意信息": "300687",
    "焦点科技": "002315",
    "昆仑万维": "300418",
    "三人行": "605168",
    "中无人机": "688297",
    "航天彩虹": "002389",
    "万丰奥威": "002085",
    "宗申动力": "001696",
    "国盾量子": "688027",
    "科大国创": "300520",
    "神州信息": "000555",
    "航天宏图": "688066",
    "中科星图": "688568",
    "恒生电子": "600570",
    "同花顺": "300033",
    "东方财富": "300059",
    "指南针": "300803",
    "拉卡拉": "300773",
    "新大陆": "000997",
    "四方精创": "300468",
    "恒宝股份": "002104",
}


AI_COMPUTE_INFRA_BLUEPRINT = {
    "chain_map": {
        "upstream": ["高速光芯片/光器件", "高端PCB/封装基板", "液冷/供配电"],
        "midstream": ["CPO/光模块", "AI服务器/交换机", "先进封装/国产算力芯片"],
        "downstream": ["云厂商资本开支", "大模型训练/推理集群", "国产替代与自主可控"],
    },
    "bottleneck_candidates": [
        {
            "link": "CPO/高速光模块",
            "companies": "中际旭创、新易盛、天孚通信",
            "catalyst": "800G/1.6T 光模块订单、CPO渗透、北美云厂商资本开支上修",
            "invalidation": "海外AI capex放缓、价格下行、硅光替代节奏低于预期或客户集中度风险",
        },
        {
            "link": "AI服务器PCB/交换机PCB",
            "companies": "沪电股份、胜宏科技、深南电路",
            "catalyst": "AI服务器/交换机板订单、高多层板ASP提升、产能利用率和毛利率上行",
            "invalidation": "扩产过快、普通PCB价格回落、AI板收入占比无法验证",
        },
        {
            "link": "AI服务器组装与供应链管理",
            "companies": "工业富联、浪潮信息、中科曙光",
            "catalyst": "AI服务器收入占比提升、云厂商订单、整机交付节奏加快",
            "invalidation": "代工利润率受压、客户砍单、估值只反映出货不反映利润",
        },
        {
            "link": "液冷/数据中心温控",
            "companies": "英维克、申菱环境、高澜股份",
            "catalyst": "液冷渗透率提升、机柜功率密度上行、数据中心温控订单确认",
            "invalidation": "风冷仍可满足、价格竞争加剧、液冷收入占比披露不足",
        },
        {
            "link": "先进封装/封测与材料",
            "companies": "通富微电、长电科技、华天科技",
            "catalyst": "先进封装资本开支、封装基板/材料国产替代、客户认证进展",
            "invalidation": "封装产能过剩、材料认证慢于预期、收入弹性弱于CPO/PCB",
        },
        {
            "link": "国产算力芯片",
            "companies": "寒武纪、海光信息、龙芯中科",
            "catalyst": "国产训练/推理集群招标、软件生态适配、收入高增延续",
            "invalidation": "生态迁移慢、交付/毛利不及预期、估值透支多年增长",
        },
    ],
    "core_value_distribution": [
        {"产业链环节": "上游/中游", "细分领域/关键产品": "CPO/高速光模块", "核心技术壁垒": "高速率、良率、海外大客户认证", "卡脖子程度": "High", "代表A股公司": "中际旭创、新易盛、天孚通信"},
        {"产业链环节": "上游", "细分领域/关键产品": "AI服务器PCB/交换机PCB", "核心技术壁垒": "高多层板、材料、良率、ASP", "卡脖子程度": "High", "代表A股公司": "沪电股份、胜宏科技、深南电路"},
        {"产业链环节": "中游", "细分领域/关键产品": "AI服务器组装", "核心技术壁垒": "大客户交付、供应链协同、规模效率", "卡脖子程度": "Medium", "代表A股公司": "工业富联、浪潮信息、中科曙光"},
        {"产业链环节": "配套", "细分领域/关键产品": "液冷/温控", "核心技术壁垒": "机柜功率密度、数据中心验证、交付能力", "卡脖子程度": "Medium", "代表A股公司": "英维克、申菱环境、高澜股份"},
        {"产业链环节": "上游", "细分领域/关键产品": "先进封装/封测与材料", "核心技术壁垒": "制程、认证、材料配方、资本开支", "卡脖子程度": "Medium", "代表A股公司": "通富微电、长电科技、华天科技"},
        {"产业链环节": "核心芯片", "细分领域/关键产品": "国产算力芯片", "核心技术壁垒": "芯片架构、软件生态、交付能力", "卡脖子程度": "High", "代表A股公司": "寒武纪、海光信息、龙芯中科"},
    ],
}

AI_COMPUTE_ABSOLUTE_CORE = {
    "中际旭创",
    "新易盛",
    "天孚通信",
    "沪电股份",
    "胜宏科技",
    "深南电路",
    "寒武纪",
}

AI_COMPUTE_HIGH_BETA = {
    "工业富联",
    "浪潮信息",
    "中科曙光",
    "英维克",
    "申菱环境",
    "高澜股份",
    "通富微电",
    "长电科技",
    "华天科技",
    "海光信息",
    "龙芯中科",
}

GENERIC_THEME_COMPANIES = {
    "datacenter-power": "英维克、申菱环境、高澜股份、工业富联",
    "agentic-ai": "科大讯飞、金山办公、用友网络、泛微网络",
    "sovereign-ai": "寒武纪、海光信息、龙芯中科、中科曙光",
    "ai-security-governance": "三六零、启明星辰、深信服、安恒信息",
    "edge-ai": "工业富联、紫光股份、浪潮信息、龙芯中科",
    "ai-healthcare": "药明康德、迈瑞医疗、联影医疗、科大讯飞",
    "ai-industrial-software": "汇川技术、中控技术、柏楚电子、赛意信息",
    "ai-commercialization": "金山办公、焦点科技、昆仑万维、三人行",
    "autonomous-low-altitude": "中无人机、航天彩虹、万丰奥威、宗申动力",
    "quantum-computing": "国盾量子、科大国创、神州信息、光迅科技",
    "space-defense-ai": "航天宏图、中科星图、航天彩虹、中无人机",
    "ai-fintech-infra": "恒生电子、同花顺、东方财富、指南针",
    "blockchain-ai-payments": "拉卡拉、新大陆、四方精创、恒宝股份",
}

GENERIC_THEME_NODES = {
    "datacenter-power": ["电力接入/变压器", "液冷/温控", "UPS/储能/燃气轮机", "数据中心运维"],
    "agentic-ai": ["多智能体编排", "企业工作流", "知识库/RAG", "办公自动化"],
    "sovereign-ai": ["国产AI芯片", "国产CPU/GPU", "服务器整机", "软件生态适配"],
    "ai-security-governance": ["身份权限", "模型安全", "内容溯源/水印", "数据合规审计"],
    "edge-ai": ["AI PC/手机", "车端推理", "NPU/SoC", "端侧模型部署"],
    "ai-healthcare": ["AI制药", "医疗影像", "多组学", "合成生物/医疗服务"],
    "ai-industrial-software": ["工业软件", "工业Copilot", "机器视觉", "PLC/自动化"],
    "ai-commercialization": ["垂直行业模型", "企业SaaS", "营销/内容生产", "ROI/留存"],
    "autonomous-low-altitude": ["智能驾驶", "eVTOL/无人机", "感知/控制", "低空基础设施"],
    "quantum-computing": ["量子芯片", "低温/测控", "量子通信", "算法/云平台"],
    "space-defense-ai": ["卫星遥感", "商业航天", "军工AI", "无人系统"],
    "ai-fintech-infra": ["智能投研", "风控/反欺诈", "金融IT", "数据合规"],
    "blockchain-ai-payments": ["稳定币/支付", "Agent支付", "链上身份", "清结算基础设施"],
}

HARD_FACT_KEYWORDS = {
    "订单/客户": ("订单", "中标", "定点", "客户", "认证", "供应", "交付", "出货", "招标"),
    "价格/涨价": ("涨价", "提价", "价格", "ASP", "报价", "涨幅"),
    "产能/扩产": ("产能", "扩产", "投产", "满产", "利用率", "锁定", "供给"),
    "良率/交期": ("良率", "交期", "爬坡", "验证", "测试", "周期"),
    "财务兑现": ("营收", "净利", "毛利率", "收入占比", "同比", "预测PE", "EPS"),
    "资本开支": ("资本开支", "capex", "Capex", "CAPEX", "投资", "建设"),
}

HARD_FACT_NUM_RE = __import__("re").compile(
    r"(\d{4}[-年]\d{1,2}[-月]?\d{0,2}日?|20\d{2}Q[1-4]|\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s*(?:亿|万|元|G|T|P|MW|GW|倍))"
)

AI_PDF_INCLUDE_TERMS = ("AI", "算力", "光模块", "CPO", "PCB", "服务器", "液冷", "封装", "算力芯片", "交换机")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def draft_slug_from_payload(payload_file: Path) -> str:
    try:
        cycle_dir = payload_file.resolve().parent
        cycle = cycle_dir.name
        run_id = cycle_dir.parent.name
        if cycle.startswith("cycle-") and run_id:
            return f"{run_id}-{cycle}"
        if cycle_dir.parent.name == "themes":
            theme_key = cycle_dir.name
            cycle_dir = cycle_dir.parent.parent
            run_dir = cycle_dir.parent
            if cycle_dir.name.startswith("cycle-") and run_dir.name:
                return f"{run_dir.name}-{cycle_dir.name}-{theme_key}"
    except Exception:
        pass
    return f"manual-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"


def theme_meta(theme_key: str) -> dict[str, Any]:
    pool = read_json(ROOT / "config" / "theme_pool.json")
    themes = pool.get("themes", {}) if isinstance(pool.get("themes"), dict) else {}
    meta = themes.get(theme_key, {})
    return meta if isinstance(meta, dict) else {}


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", "<br>") for cell in row) + " |")
    return "\n".join(lines)


def compact(value: Any, limit: int = 54) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "NA"


def fmt_num(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "NA"


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, "", "--", "-"):
            return None
        return float(value)
    except Exception:
        return None


def _font(size: int, *, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            if candidate and Path(candidate).exists():
                return ImageFont.truetype(candidate, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_wrapped(
    draw: Any,
    xy: tuple[int, int],
    text: str,
    font: Any,
    fill: str,
    max_width: int,
    *,
    line_gap: int = 6,
    max_lines: int = 3,
) -> int:
    x, y = xy
    text = str(text or "")
    lines: list[str] = []
    current = ""
    for ch in text:
        candidate = current + ch
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = ch
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    rendered = "".join(lines)
    for idx, line in enumerate(lines[:max_lines]):
        if idx == max_lines - 1 and len(rendered) < len(text):
            line = line[:-1] + "..." if line else "..."
        draw.text((x, y), line, font=font, fill=fill)
        y += getattr(font, "size", 14) + line_gap
    return y


def enrich_theme_selected(theme_key: str, selected: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(selected)
    blueprint = theme_blueprint(theme_key)
    if theme_key != "ai-compute-infra":
        enriched["chain_map"] = blueprint["chain_map"]
        enriched["core_value_distribution"] = blueprint["core_value_distribution"]
    if not isinstance(enriched.get("chain_map"), dict) or not enriched.get("chain_map"):
        enriched["chain_map"] = blueprint["chain_map"]
    existing = enriched.get("bottleneck_candidates", [])
    existing = [x for x in existing if isinstance(x, dict)] if isinstance(existing, list) else []
    node_terms = {
        term
        for item in blueprint["bottleneck_candidates"]
        for term in str(item.get("link") or "").replace("/", "、").split("、")
        if len(term.strip()) >= 2
    }
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in blueprint["bottleneck_candidates"] + existing:
        if item in existing and theme_key != "ai-compute-infra":
            link_text = str(item.get("link") or "")
            if not any(term and term in link_text for term in node_terms):
                continue
        key = str(item.get("link") or item.get("companies") or "")
        if key and key not in seen:
            merged.append(item)
            seen.add(key)
    enriched["bottleneck_candidates"] = merged
    if not isinstance(enriched.get("core_value_distribution"), list) or len(enriched.get("core_value_distribution", [])) < 4:
        enriched["core_value_distribution"] = blueprint["core_value_distribution"]
    return enriched


def theme_blueprint(theme_key: str) -> dict[str, Any]:
    if theme_key == "ai-compute-infra":
        return AI_COMPUTE_INFRA_BLUEPRINT
    meta = theme_meta(theme_key)
    label = str(meta.get("label") or theme_key)
    keywords = [str(x) for x in meta.get("discovery_keywords", []) if isinstance(x, str)]
    nodes = GENERIC_THEME_NODES.get(theme_key) or keywords[:4] or [label, "上游基础设施", "中游产品化", "下游场景"]
    companies = GENERIC_THEME_COMPANIES.get(theme_key, "待验证核心公司A、待验证核心公司B、待验证核心公司C")
    upstream = nodes[:2] or [label + "上游"]
    midstream = nodes[2:4] or [label + "产品化"]
    downstream = ["客户验证/订单", "收入占比", "监管/合规", "商业化ROI"]
    bottlenecks = []
    for idx, node in enumerate(nodes[:5]):
        bottlenecks.append(
            {
                "link": node,
                "companies": companies,
                "catalyst": "订单/客户认证/收入占比/政策或监管里程碑出现公告级证据",
                "invalidation": "商业化ROI不足、客户验证低于预期、收入暴露不足或监管约束增强",
            }
        )
    value_rows = [
        {
            "产业链环节": "上游" if idx < 2 else "中游" if idx < 4 else "下游",
            "细分领域/关键产品": node,
            "核心技术壁垒": "客户认证、数据闭环、工程化交付、合规和成本控制",
            "卡脖子程度": "High" if idx < 2 else "Medium",
            "代表A股公司": companies,
        }
        for idx, node in enumerate(nodes[:6])
    ]
    return {
        "chain_map": {"upstream": upstream, "midstream": midstream, "downstream": downstream},
        "bottleneck_candidates": bottlenecks,
        "core_value_distribution": value_rows,
    }


def price_history_rows(supplement: dict[str, Any]) -> list[dict[str, Any]]:
    history = supplement.get("price_history", {}) if isinstance(supplement, dict) else {}
    rows = history.get("rows", []) if isinstance(history, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def technical_snapshot(quote: dict[str, Any], supplement: dict[str, Any]) -> dict[str, Any]:
    rows = price_history_rows(supplement)
    closes = [_float_or_none(row.get("close")) for row in rows]
    closes = [x for x in closes if x is not None]
    highs = [_float_or_none(row.get("high")) for row in rows]
    highs = [x for x in highs if x is not None]
    lows = [_float_or_none(row.get("low")) for row in rows]
    lows = [x for x in lows if x is not None]
    price = _float_or_none(quote.get("price")) or (closes[-1] if closes else None)
    prev_close = _float_or_none(quote.get("prev_close"))
    change_pct = _float_or_none(quote.get("change_pct"))
    ma5 = _avg(closes[-5:])
    ma10 = _avg(closes[-10:])
    ma20 = _avg(closes[-20:])
    ma60 = _avg(closes[-60:])
    low20 = min(lows[-20:]) if len(lows) >= 5 else None
    high20 = max(highs[-20:]) if len(highs) >= 5 else None
    low60 = min(lows[-60:]) if len(lows) >= 20 else low20
    high60 = max(highs[-60:]) if len(highs) >= 20 else high20
    support_candidates = [x for x in (low20, ma20, prev_close) if x is not None]
    pressure_candidates = [x for x in (high20, high60) if x is not None]
    support = max([x for x in support_candidates if price is None or x <= price], default=(low20 or prev_close))
    pressure = min([x for x in pressure_candidates if price is None or x >= price], default=(high20 or high60))
    if price is not None and support is None:
        support = price * 0.92
    if price is not None and pressure is None:
        pressure = price * 1.12
    rr = None
    if price and support and pressure and price > support:
        rr = (pressure - price) / (price - support)
    trend_parts = []
    if price and ma20 and ma60:
        if price > ma20 > ma60:
            trend_parts.append("多头趋势")
        elif price < ma20 < ma60:
            trend_parts.append("空头趋势")
        else:
            trend_parts.append("震荡分歧")
    elif price and change_pct is not None:
        trend_parts.append("短线强势" if change_pct >= 5 else "短线回落" if change_pct <= -3 else "短线震荡")
    else:
        trend_parts.append("趋势待验证K线")
    if price and high20 and low20 and high20 > low20:
        box_pos = (price - low20) / (high20 - low20) * 100
        trend_parts.append(f"20日箱体位置{box_pos:.0f}%")
    if rr is not None:
        trend_parts.append(f"风险收益比{rr:.2f}")
    entry = "等待回踩支撑不破后放量转强" if price and support and price > support else "等待站回短中期均线"
    stop = f"跌破{fmt_num(support)}且订单/业绩无增量" if support else "跌破关键均线且证据无增量"
    target = f"{fmt_num(pressure)}压力位；强势突破后看{fmt_num((pressure or price or 0) * 1.12)}" if pressure else "压力位待K线补充"
    return {
        "price": price,
        "change_pct": change_pct,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "low20": low20,
        "high20": high20,
        "low60": low60,
        "high60": high60,
        "support": support,
        "pressure": pressure,
        "risk_reward": rr,
        "trend": "；".join(trend_parts),
        "entry": entry,
        "stop": stop,
        "target": target,
        "history_points": len(rows),
    }


def evidence_ref(payload: dict[str, Any], prefix: str, fallback: str = "本轮结构化证据") -> str:
    ids = [str(x) for x in payload.get("evidence_ids", []) if isinstance(x, str)]
    match = next((x for x in ids if x.startswith(prefix)), None)
    return match or (ids[0] if ids else fallback)


def public_provider_text(text: Any) -> str:
    value = str(text or "")
    replacements = {
        "Vibe-Research workbench": "公开数据工作台",
        "Vibe-Research": "公开数据工作台",
        "Vibe-Trading strategy adapter": "策略路由复核",
        "Vibe-Trading": "策略路由复核",
        "TradingAgents-astock": "组合复核",
        "backend/astock.py data workbench pattern": "A股行情/财务数据清洗",
        "report/dashboard evidence organization": "报告证据组织",
        "data-routing source priority": "数据源优先级",
        "eastmoney disclosure/fundamental contract": "公告/财务数据契约",
        "strategy risk gating": "交易风险门槛",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def provider_insight_rows(payload: dict[str, Any]) -> list[list[Any]]:
    insights = payload.get("provider_insights", {})
    providers = insights.get("providers", {}) if isinstance(insights, dict) else {}
    if not isinstance(providers, dict):
        return []
    labels = {
        "vibe_research": "公开数据工作台",
        "vibe_trading": "策略路由复核",
        "tradingagents_astock": "投委会复核",
    }
    evidence_id = evidence_ref(payload, "ev-provider")
    rows: list[list[Any]] = []
    for key in ("vibe_research", "vibe_trading", "tradingagents_astock"):
        item = providers.get(key)
        if not isinstance(item, dict):
            continue
        claims = [str(x) for x in item.get("claims", []) if str(x).strip()]
        capabilities = [str(x) for x in item.get("capabilities_reused", []) if str(x).strip()]
        errors = [str(x) for x in item.get("errors", []) if str(x).strip()]
        rows.append(
            [
                public_provider_text(labels.get(key, item.get("provider", key))),
                item.get("status", "NA"),
                public_provider_text("、".join(capabilities[:3])) or "公开数据/策略复核",
                public_provider_text("；".join(claims[:2])) or "本轮未产出可写入正文的新增观点",
                "不阻塞；" + (compact(errors[0], 32) if errors else "可用"),
                evidence_id,
            ]
        )
    return rows


def chain(payload: dict[str, Any]) -> dict[str, Any]:
    pipeline = payload.get("research_pipeline", {})
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    value = pipeline.get("selected_industry_chain", {})
    return value if isinstance(value, dict) else {}


def stock_analyzers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pipeline = payload.get("research_pipeline", {})
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    rows = pipeline.get("stock_analyzer", [])
    return [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []


def decisions(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pipeline = payload.get("research_pipeline", {})
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    engine = pipeline.get("trade_decision_engine", {})
    rows = engine.get("decisions", []) if isinstance(engine, dict) else []
    out: dict[str, dict[str, Any]] = {}
    for item in rows if isinstance(rows, list) else []:
        if isinstance(item, dict) and item.get("symbol"):
            out[str(item["symbol"])] = item
    return out


BUYABLE_DECISION_ACTIONS = {"paper_candidate", "buy", "buy_candidate"}


def buyable_decision_action(action: Any) -> bool:
    return str(action or "").strip().lower() in BUYABLE_DECISION_ACTIONS


def usable_trade_technical(tech: dict[str, Any], *, min_rr: float = 1.8) -> bool:
    price = _float_or_none(tech.get("price"))
    support = _float_or_none(tech.get("support"))
    pressure = _float_or_none(tech.get("pressure"))
    rr = _float_or_none(tech.get("risk_reward"))
    history_points = int(tech.get("history_points") or 0)
    trend = str(tech.get("trend") or "")
    return (
        price is not None
        and support is not None
        and pressure is not None
        and pressure > price >= support
        and rr is not None
        and rr >= min_rr
        and history_points >= 40
        and "空头" not in trend
    )


def current_buy_candidate(record: dict[str, Any]) -> bool:
    tech = record.get("technical", {}) if isinstance(record.get("technical"), dict) else {}
    decision = record.get("decision", {}) if isinstance(record.get("decision"), dict) else {}
    min_rr = _float_or_none(decision.get("min_risk_reward")) or 1.8
    if record.get("decision_scope_present") and not record.get("has_trade_decision"):
        return False
    if record.get("has_trade_decision"):
        return buyable_decision_action(decision.get("action")) and usable_trade_technical(tech, min_rr=min_rr)
    return usable_trade_technical(tech, min_rr=min_rr)


def buy_entry_text(record: dict[str, Any]) -> str:
    tech = record.get("technical", {}) if isinstance(record.get("technical"), dict) else {}
    if current_buy_candidate(record):
        return (
            f"建议买点：{fmt_num(tech.get('support'))}附近缩量企稳，或放量突破"
            f"{fmt_num(tech.get('pressure'))}后回踩确认；{record.get('entry', '等待证据补强')}"
        )
    return (
        "等待买入触发：当前未进入买入候选；需先满足交易决策、风险收益比、"
        "K线企稳和订单/价格/客户认证增量证据"
    )


def sell_target_text(record: dict[str, Any]) -> str:
    tech = record.get("technical", {}) if isinstance(record.get("technical"), dict) else {}
    if current_buy_candidate(record):
        return f"建议卖点/减仓：接近{fmt_num(tech.get('pressure'))}先兑现一档；{tech.get('target', '目标位待K线补充')}"
    return "未设技术目标：尚未进入买入候选，先观察证据和价格结构是否修复"


def write_chain_svg(path: Path, label: str, chain_map: dict[str, Any], bottlenecks: list[dict[str, Any]]) -> None:
    upstream = chain_map.get("upstream") or ["上游材料/设备", "关键元器件", "制造工艺"]
    midstream = chain_map.get("midstream") or ["核心产品", "系统集成", "供应链交付"]
    downstream = chain_map.get("downstream") or ["终端应用", "资本开支", "客户订单"]
    key_bottleneck = compact((bottlenecks[0] or {}).get("link") if bottlenecks else "待验证卡口", 24)
    node_cards = []
    for idx, item in enumerate(bottlenecks[:6]):
        x = 70 + (idx % 3) * 405
        y = 500 + (idx // 3) * 118
        companies = [c.strip() for c in str(item.get("companies") or "").replace("、", ",").replace("，", ",").split(",") if c.strip()]
        company_text = " / ".join(companies[:3]) or "待验证"
        node_cards.append(
            f'<rect x="{x}" y="{y}" width="350" height="88" rx="14" fill="#f8fafc" stroke="#94a3b8" stroke-width="1.6"/>'
            f'<text x="{x+18}" y="{y+30}" class="h2">{compact(item.get("link"), 18)}</text>'
            f'<text x="{x+18}" y="{y+61}" class="s2">{compact(company_text, 38)}</text>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="760" viewBox="0 0 1280 760">
<style>
text{{font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif}} .title{{font-size:34px;font-weight:800;fill:#111827}} .h{{font-size:22px;font-weight:800;fill:#111827}} .h2{{font-size:17px;font-weight:800;fill:#111827}} .s{{font-size:17px;fill:#374151}} .s2{{font-size:14px;fill:#334155}} .box{{rx:14;stroke-width:2}} .u{{fill:#eef2ff;stroke:#4f46e5}} .m{{fill:#ecfdf5;stroke:#059669}} .d{{fill:#fff7ed;stroke:#ea580c}} .arrow{{stroke:#475569;stroke-width:3;marker-end:url(#a)}}
</style>
<defs><marker id="a" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M2,2 L10,6 L2,10 Z" fill="#475569"/></marker></defs>
<rect width="1280" height="760" fill="#ffffff"/>
<text x="54" y="62" class="title">{label}：产业链、卡口与证据链</text>
<text x="54" y="100" class="s">方法：大趋势 -> 供应链 -> 物理约束 -> 瓶颈卡口 -> 稀缺供应商 -> 交易纪律</text>
<rect x="70" y="150" width="320" height="250" class="box u"/><text x="98" y="190" class="h">上游供给约束</text>
<text x="98" y="235" class="s">1. {compact(upstream[0], 20)}</text><text x="98" y="275" class="s">2. {compact(upstream[1] if len(upstream)>1 else '', 20)}</text><text x="98" y="315" class="s">3. {compact(upstream[2] if len(upstream)>2 else '', 20)}</text>
<rect x="480" y="150" width="320" height="250" class="box m"/><text x="508" y="190" class="h">中游价值承接</text>
<text x="508" y="235" class="s">1. {compact(midstream[0], 20)}</text><text x="508" y="275" class="s">2. {compact(midstream[1] if len(midstream)>1 else '', 20)}</text><text x="508" y="315" class="s">3. {compact(midstream[2] if len(midstream)>2 else '', 20)}</text>
<rect x="890" y="150" width="320" height="250" class="box d"/><text x="918" y="190" class="h">下游需求验证</text>
<text x="918" y="235" class="s">1. {compact(downstream[0], 20)}</text><text x="918" y="275" class="s">2. {compact(downstream[1] if len(downstream)>1 else '', 20)}</text><text x="918" y="315" class="s">3. {compact(downstream[2] if len(downstream)>2 else '', 20)}</text>
<line x1="395" y1="305" x2="475" y2="305" class="arrow"/><line x1="805" y1="305" x2="885" y2="305" class="arrow"/>
<text x="70" y="452" class="h">核心节点与三家核心受益公司</text>
{''.join(node_cards)}
</svg>"""
    path.write_text(svg, encoding="utf-8")


def write_bottleneck_svg(path: Path, label: str, rows: list[dict[str, Any]]) -> None:
    labels = [compact(str(x.get("link") or x.get("细分领域/关键产品") or "候选卡口"), 18) for x in rows[:5]]
    if not labels:
        labels = ["核心供给约束", "产品化交付", "下游需求验证"]
    width, height = 1180, 560
    max_score = max(len(labels), 1)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="46" y="48" font-size="28" font-weight="800" fill="#111827">{label}：卡口候选优先级</text>',
        '<text x="46" y="86" font-size="16" fill="#4b5563">评分为研究优先级，不代表已验证收入弹性；每个状态变化仍需 evidence id 支撑。</text>',
    ]
    for idx, name in enumerate(labels):
        y = 135 + idx * 76
        score = max_score - idx
        bar_w = 180 + score / max_score * 700
        color = ["#4f46e5", "#059669", "#ea580c", "#0891b2", "#7c3aed"][idx % 5]
        lines.append(f'<text x="58" y="{y+26}" font-size="18" font-weight="700" fill="#111827">{idx+1}. {name}</text>')
        lines.append(f'<rect x="280" y="{y}" width="{bar_w:.1f}" height="38" rx="8" fill="{color}" opacity="0.88"/>')
        lines.append(f'<text x="{bar_w+300:.1f}" y="{y+26}" font-size="16" fill="#111827">优先级 {score}/{max_score}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_stock_snapshot_svg(path: Path, label: str, rows: list[dict[str, Any]]) -> None:
    width, height = 1200, 660
    chart_rows = [r for r in rows if isinstance(r.get("pe"), (int, float))]
    if not chart_rows:
        chart_rows = rows[:6]
    max_pe = max([float(r.get("pe") or 0) for r in chart_rows] or [1])
    max_pe = max(max_pe, 1.0)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="48" y="48" font-size="28" font-weight="800" fill="#111827">{label}：A股候选估值与证据状态</text>',
        '<text x="48" y="86" font-size="16" fill="#4b5563">PE/PB来自公开行情或补充数据；缺失时保留为待验证，不用估算值填充。</text>',
    ]
    y0 = 138
    for idx, row in enumerate(chart_rows[:12]):
        y = y0 + idx * 74
        name = compact(row.get("name"), 14)
        symbol = compact(row.get("symbol"), 8)
        pe = row.get("pe")
        pb = row.get("pb")
        pe_val = float(pe) if isinstance(pe, (int, float)) else 0.0
        bar_w = 60 + pe_val / max_pe * 760 if pe_val else 140
        color = "#dc2626" if pe_val >= 120 else "#ea580c" if pe_val >= 60 else "#059669"
        display = f"PE {pe_val:.1f}" if pe_val else "PE 待验证"
        pb_display = f"PB {float(pb):.1f}" if isinstance(pb, (int, float)) else "PB 待验证"
        lines.append(f'<text x="56" y="{y+25}" font-size="17" font-weight="700" fill="#111827">{name}</text>')
        lines.append(f'<text x="56" y="{y+51}" font-size="14" fill="#6b7280">{symbol}</text>')
        lines.append(f'<rect x="210" y="{y}" width="{bar_w:.1f}" height="34" rx="7" fill="{color}" opacity="0.84"/>')
        lines.append(f'<text x="{bar_w+225:.1f}" y="{y+24}" font-size="15" fill="#111827">{display} / {pb_display}</text>')
        lines.append(f'<text x="210" y="{y+57}" font-size="14" fill="#4b5563">{compact(row.get("evidence_note"), 70)}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_trade_map_svg(path: Path, label: str, rows: list[dict[str, Any]]) -> None:
    width, height = 1280, 720
    chart_rows = rows[:12]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="46" y="52" font-size="30" font-weight="800" fill="#111827">{label}：核心标的交易结构</text>',
        '<text x="46" y="90" font-size="16" fill="#4b5563">横轴为支撑-现价-压力的相对位置；没有完整K线时用现价/前收降级估算，需后续证据校正。</text>',
        '<line x1="260" y1="132" x2="1130" y2="132" stroke="#cbd5e1" stroke-width="2"/>',
        '<text x="252" y="118" font-size="14" fill="#64748b">支撑</text><text x="672" y="118" font-size="14" fill="#64748b">现价</text><text x="1112" y="118" font-size="14" fill="#64748b">压力</text>',
    ]
    for idx, row in enumerate(chart_rows):
        tech = row.get("technical", {}) if isinstance(row.get("technical"), dict) else {}
        y = 170 + idx * 62
        support = _float_or_none(tech.get("support"))
        price = _float_or_none(tech.get("price"))
        pressure = _float_or_none(tech.get("pressure"))
        if support is None or price is None or pressure is None or pressure <= support:
            support = price * 0.92 if price else 0
            pressure = price * 1.12 if price else 1
        px = 260 + max(0, min(1, ((price or support) - support) / (pressure - support))) * 870
        lines.append(f'<text x="46" y="{y+7}" font-size="16" font-weight="700" fill="#111827">{compact(row.get("name"), 12)}</text>')
        lines.append(f'<text x="46" y="{y+31}" font-size="13" fill="#64748b">{row.get("symbol", "")} · {compact(row.get("link"), 18)}</text>')
        lines.append(f'<line x1="260" y1="{y}" x2="1130" y2="{y}" stroke="#e2e8f0" stroke-width="10" stroke-linecap="round"/>')
        lines.append(f'<circle cx="{px:.1f}" cy="{y}" r="12" fill="#2563eb"/>')
        lines.append(f'<text x="260" y="{y+30}" font-size="12" fill="#64748b">{fmt_num(support)}</text>')
        lines.append(f'<text x="{px+16:.1f}" y="{y+5}" font-size="13" fill="#111827">{fmt_num(price)}</text>')
        lines.append(f'<text x="1090" y="{y+30}" font-size="12" fill="#64748b">{fmt_num(pressure)}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_chain_png(path: Path, label: str, chain_map: dict[str, Any], bottlenecks: list[dict[str, Any]]) -> None:
    from PIL import Image, ImageDraw

    upstream = chain_map.get("upstream") or ["上游材料/设备", "关键元器件", "制造工艺"]
    midstream = chain_map.get("midstream") or ["核心产品", "系统集成", "供应链交付"]
    downstream = chain_map.get("downstream") or ["终端应用", "资本开支", "客户订单"]
    width, height = 1500, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(32, bold=True)
    head_font = _font(23, bold=True)
    body_font = _font(18)
    small_font = _font(15)
    draw.text((54, 36), f"{label}：产业链、卡口与证据链", font=title_font, fill="#111827")
    draw.text((54, 82), "方法：大趋势 -> 供应链 -> 物理约束 -> 瓶颈卡口 -> 稀缺供应商 -> 交易纪律", font=body_font, fill="#475569")
    cards = [
        ("上游供给约束", upstream, "#eef2ff", "#4f46e5"),
        ("中游价值承接", midstream, "#ecfdf5", "#059669"),
        ("下游需求验证", downstream, "#fff7ed", "#ea580c"),
    ]
    for idx, (title, items, fill, stroke) in enumerate(cards):
        x = 70 + idx * 475
        draw.rounded_rectangle((x, 140, x + 380, 430), radius=18, fill=fill, outline=stroke, width=3)
        draw.text((x + 28, 178), title, font=head_font, fill="#111827")
        for row_idx, item in enumerate(items[:3]):
            _draw_wrapped(draw, (x + 28, 230 + row_idx * 58), f"{row_idx + 1}. {item}", body_font, "#334155", 320, max_lines=2)
    draw.line((450, 285, 540, 285), fill="#64748b", width=4)
    draw.line((925, 285, 1015, 285), fill="#64748b", width=4)
    draw.text((70, 500), "核心节点与三家核心受益公司", font=head_font, fill="#111827")
    for idx, item in enumerate(bottlenecks[:6]):
        x = 70 + (idx % 3) * 475
        y = 545 + (idx // 3) * 160
        companies = [c.strip() for c in str(item.get("companies") or "").replace("、", ",").replace("，", ",").split(",") if c.strip()]
        draw.rounded_rectangle((x, y, x + 410, y + 122), radius=16, fill="#f8fafc", outline="#94a3b8", width=2)
        draw.text((x + 20, y + 20), compact(item.get("link"), 18), font=head_font, fill="#111827")
        _draw_wrapped(draw, (x + 20, y + 58), " / ".join(companies[:3]) or "待验证", body_font, "#334155", 350, max_lines=2)
    draw.text((70, 900), "图表由本地 PNG 渲染器生成；报告正文不依赖外部 SVG 渲染能力。", font=small_font, fill="#64748b")
    image.save(path)


def write_bottleneck_png(path: Path, label: str, rows: list[dict[str, Any]]) -> None:
    from PIL import Image, ImageDraw

    labels = [compact(str(x.get("link") or x.get("细分领域/关键产品") or "候选卡口"), 18) for x in rows[:6]]
    if not labels:
        labels = ["核心供给约束", "产品化交付", "下游需求验证"]
    width, height = 1280, 700
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(30, bold=True)
    body_font = _font(18)
    draw.text((48, 38), f"{label}：卡口候选优先级", font=title_font, fill="#111827")
    draw.text((48, 82), "评分为研究优先级，不代表已验证收入弹性；每个状态变化仍需 evidence id 支撑。", font=body_font, fill="#475569")
    max_score = max(len(labels), 1)
    palette = ["#4f46e5", "#059669", "#ea580c", "#0891b2", "#7c3aed", "#dc2626"]
    for idx, name in enumerate(labels):
        y = 135 + idx * 82
        score = max_score - idx
        bar_w = 180 + score / max_score * 800
        draw.text((58, y + 28), f"{idx + 1}. {name}", font=body_font, fill="#111827")
        draw.rounded_rectangle((300, y, 300 + bar_w, y + 42), radius=9, fill=palette[idx % len(palette)])
        draw.text((315 + bar_w, y + 27), f"优先级 {score}/{max_score}", font=body_font, fill="#111827")
    image.save(path)


def write_stock_snapshot_png(path: Path, label: str, rows: list[dict[str, Any]]) -> None:
    from PIL import Image, ImageDraw

    chart_rows = [r for r in rows if isinstance(r.get("pe"), (int, float))]
    if not chart_rows:
        chart_rows = rows[:8]
    width, height = 1350, 860
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(30, bold=True)
    body_font = _font(17)
    small_font = _font(14)
    draw.text((48, 36), f"{label}：A股候选估值与证据状态", font=title_font, fill="#111827")
    draw.text((48, 82), "PE/PB来自公开行情或补充数据；缺失时保留为待验证，不用估算值填充。", font=body_font, fill="#475569")
    max_pe = max([float(r.get("pe") or 0) for r in chart_rows] or [1])
    max_pe = max(max_pe, 1.0)
    for idx, row in enumerate(chart_rows[:10]):
        y = 130 + idx * 70
        pe = _float_or_none(row.get("pe"))
        pb = _float_or_none(row.get("pb"))
        pe_val = max(pe or 0.0, 0.0)
        bar_w = 70 + pe_val / max_pe * 740 if pe_val else 150
        color = "#dc2626" if pe_val >= 120 else "#ea580c" if pe_val >= 60 else "#059669"
        draw.text((56, y + 22), compact(row.get("name"), 12), font=body_font, fill="#111827")
        draw.text((56, y + 48), str(row.get("symbol", "")), font=small_font, fill="#64748b")
        draw.rounded_rectangle((210, y, 210 + bar_w, y + 34), radius=7, fill=color)
        display = f"PE {pe_val:.1f}" if pe else "PE 待验证"
        pb_display = f"PB {pb:.1f}" if pb else "PB 待验证"
        draw.text((225 + bar_w, y + 24), f"{display} / {pb_display}", font=body_font, fill="#111827")
        _draw_wrapped(draw, (210, y + 44), compact(row.get("evidence_note"), 88), small_font, "#475569", 990, max_lines=1)
    image.save(path)


def _panel_candles(draw: Any, box: tuple[int, int, int, int], row: dict[str, Any]) -> None:
    x0, y0, x1, y1 = box
    tech = row.get("technical", {}) if isinstance(row.get("technical"), dict) else {}
    supplement = row.get("supplement", {}) if isinstance(row.get("supplement"), dict) else {}
    history = price_history_rows(supplement)[-90:]
    clean = [
        r for r in history
        if _float_or_none(r.get("open")) is not None
        and _float_or_none(r.get("close")) is not None
        and _float_or_none(r.get("high")) is not None
        and _float_or_none(r.get("low")) is not None
    ]
    title_font = _font(18, bold=True)
    small_font = _font(12)
    draw.text((x0, y0 - 28), f"{row.get('name')} {row.get('symbol')}", font=title_font, fill="#111827")
    draw.rectangle((x0, y0, x1, y1), outline="#cbd5e1", width=1)
    if len(clean) < 2:
        draw.text((x0 + 18, y0 + 50), "历史K线数据不足", font=small_font, fill="#64748b")
        return
    highs = [float(r["high"]) for r in clean]
    lows = [float(r["low"]) for r in clean]
    closes = [float(r["close"]) for r in clean]
    markers = [_float_or_none(tech.get(k)) for k in ("support", "pressure")]
    marker_vals = [v for v in markers if v is not None]
    min_v = min(lows + marker_vals)
    max_v = max(highs + marker_vals)
    span = max(max_v - min_v, 1e-9)
    inner_left, inner_right = x0 + 50, x1 - 20
    inner_top, inner_bottom = y0 + 18, y1 - 38

    def yy(v: float) -> float:
        return inner_top + (max_v - v) / span * (inner_bottom - inner_top)

    for i in range(4):
        y = inner_top + i * (inner_bottom - inner_top) / 3
        draw.line((inner_left, y, inner_right, y), fill="#e5e7eb", width=1)
    candle_gap = (inner_right - inner_left) / max(len(clean), 1)
    candle_w = max(3, min(8, candle_gap * 0.55))
    for idx, item in enumerate(clean):
        o = float(item["open"])
        c = float(item["close"])
        h = float(item["high"])
        l = float(item["low"])
        x = inner_left + idx * candle_gap + candle_gap / 2
        color = "#dc2626" if c >= o else "#16a34a"
        draw.line((x, yy(h), x, yy(l)), fill=color, width=1)
        top_body, bottom_body = yy(max(o, c)), yy(min(o, c))
        if bottom_body - top_body < 2:
            draw.line((x - candle_w / 2, top_body, x + candle_w / 2, top_body), fill=color, width=2)
        else:
            draw.rectangle((x - candle_w / 2, top_body, x + candle_w / 2, bottom_body), outline=color, fill="#fee2e2" if c >= o else "#dcfce7")
    for label, key, color in (("支撑", "support", "#15803d"), ("压力", "pressure", "#b91c1c")):
        value = _float_or_none(tech.get(key))
        if value is not None:
            y = yy(value)
            draw.line((inner_left, y, inner_right, y), fill=color, width=2)
            draw.text((inner_right - 78, y - 15), f"{label} {value:.2f}", font=small_font, fill=color)
    draw.text((inner_left, y1 - 25), str(clean[0].get("date", "")), font=small_font, fill="#64748b")
    draw.text((inner_right - 68, y1 - 25), str(clean[-1].get("date", "")), font=small_font, fill="#64748b")
    draw.text((x0 + 8, y0 + 10), f"{max_v:.2f}", font=small_font, fill="#64748b")
    draw.text((x0 + 8, y1 - 54), f"{min_v:.2f}", font=small_font, fill="#64748b")
    draw.text((x0 + 8, y1 - 24), f"最新 {closes[-1]:.2f}", font=small_font, fill="#111827")


def write_trade_kline_png(path: Path, label: str, rows: list[dict[str, Any]]) -> None:
    from PIL import Image, ImageDraw

    width, height = 1500, 1100
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(30, bold=True)
    body_font = _font(16)
    draw.text((48, 34), f"{label}：现阶段买入候选K线与关键位", font=title_font, fill="#111827")
    draw.text((48, 78), "仅展示通过交易决策和风险收益比门槛的候选；每个面板为近90个交易日OHLC、支撑和压力。", font=body_font, fill="#475569")
    chart_rows = rows[:6]
    for idx, row in enumerate(chart_rows):
        col = idx % 2
        r = idx // 2
        x0 = 70 + col * 710
        y0 = 150 + r * 300
        _panel_candles(draw, (x0, y0, x0 + 650, y0 + 235), row)
    image.save(path)


def png_has_chart_content(path: Path) -> bool:
    try:
        from PIL import Image

        image = Image.open(path).convert("RGB").resize((240, 160))
        pixels = list(image.getdata())
        nonwhite = sum(1 for r, g, b in pixels if not (r > 248 and g > 248 and b > 248))
        return nonwhite / max(len(pixels), 1) >= 0.06 and len(set(pixels)) >= 32
    except Exception:
        return False


def stock_rows(payload: dict[str, Any]) -> list[list[Any]]:
    quotes = {str(x.get("symbol")): x for x in payload.get("a_share_quotes", []) if isinstance(x, dict)}
    decision_map = decisions(payload)
    rows: list[list[Any]] = []
    for item in stock_analyzers(payload):
        symbol = str(item.get("symbol") or "")
        quote = quotes.get(symbol, {})
        valuation = item.get("valuation", {}) if isinstance(item.get("valuation"), dict) else {}
        decision = decision_map.get(symbol, {})
        rows.append(
            [
                item.get("name") or quote.get("name") or symbol,
                symbol,
                compact(item.get("business_model"), 32),
                f"PE {valuation.get('pe', quote.get('pe', 'NA'))} / PB {valuation.get('pb', quote.get('pb', 'NA'))}",
                f"涨跌幅 {fmt_pct(quote.get('change_pct'))}; 价格 {quote.get('price', 'NA')}",
                decision.get("action", "watch"),
                f"通过 {decision.get('passed_conditions', 'NA')}/5; RR>={decision.get('min_risk_reward', 'NA')}",
                "收入/订单暴露无法验证或估值赔率不足",
            ]
        )
    return rows or [["待验证", "-", "本轮无可用公司映射", "NA", "NA", "watch", "本轮未取得可靠公开证据", "无证据不升级"]]


def latest_financial_note(supplement: dict[str, Any]) -> str:
    financials = supplement.get("financials", {}) if isinstance(supplement, dict) else {}
    statements = financials.get("statements", {}) if isinstance(financials, dict) else {}
    indicators = statements.get("indicators", []) if isinstance(statements, dict) else []
    if not indicators:
        return "财务指标未取得可靠公开数据"
    latest = indicators[0] if isinstance(indicators[0], dict) else {}
    revenue = latest.get("TOTALOPERATEREVE")
    profit = latest.get("PARENTNETPROFIT")
    revenue_yoy = latest.get("TOTALOPERATEREVETZ")
    profit_yoy = latest.get("PARENTNETPROFITTZ")
    gross_margin = latest.get("XSMLL")
    parts = []
    if latest.get("REPORT_DATE_NAME"):
        parts.append(str(latest["REPORT_DATE_NAME"]))
    if revenue_yoy is not None:
        parts.append(f"营收同比 {fmt_pct(revenue_yoy)}")
    elif revenue is not None:
        parts.append(f"营收 {compact(revenue, 12)}")
    if profit_yoy is not None:
        parts.append(f"归母净利同比 {fmt_pct(profit_yoy)}")
    elif profit is not None:
        parts.append(f"归母净利 {compact(profit, 12)}")
    if gross_margin is not None:
        parts.append(f"毛利率 {fmt_pct(gross_margin)}")
    return "；".join(parts) if parts else "财务指标未取得可靠公开数据"


def latest_research_note(supplement: dict[str, Any]) -> str:
    reports = supplement.get("research_reports", {}) if isinstance(supplement, dict) else {}
    rows = reports.get("rows", []) if isinstance(reports, dict) else []
    if rows and isinstance(rows[0], dict):
        first = rows[0]
        title = compact(first.get("title"), 32)
        pe_forecast = first.get("pe_forecast")
        pe_text = ""
        if isinstance(pe_forecast, dict):
            this_year = pe_forecast.get("this_year")
            next_year = pe_forecast.get("next_year")
            if this_year or next_year:
                pe_text = f"；预测PE {this_year or 'NA'}/{next_year or 'NA'}"
        return f"{first.get('org', '研报')}《{title}》{pe_text}"
    announcements = supplement.get("announcements", {}) if isinstance(supplement, dict) else {}
    ann_rows = announcements.get("rows", []) if isinstance(announcements, dict) else []
    if ann_rows and isinstance(ann_rows[0], dict):
        return f"公告《{compact(ann_rows[0].get('title'), 36)}》"
        return "公告/研报未取得可靠公开数据"


def fact_category(text: str) -> str | None:
    for category, keywords in HARD_FACT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return None


def fact_strength(source_kind: str, text: str) -> str:
    if source_kind == "announcement":
        return "公告级/High"
    if source_kind == "financial":
        return "财报级/High"
    if source_kind == "research_report":
        return "研报级/Medium"
    if source_kind == "pdf_body":
        return "PDF正文级/Medium-High"
    if source_kind == "industry_report":
        return "标题级/Medium-Low"
    if source_kind == "news":
        return "新闻级/Low"
    return "线索级/Low"


def fact_numbers(text: str) -> str:
    matches = HARD_FACT_NUM_RE.findall(text)
    return "、".join(dict.fromkeys(matches[:5])) or "未披露明确数值/日期"


def fact_node(text: str) -> str:
    mapping = (
        ("CPO/高速光模块", ("CPO", "光模块", "800G", "1.6T", "硅光")),
        ("AI服务器PCB/交换机PCB", ("PCB", "高多层板", "交换机", "服务器板", "基板")),
        ("AI服务器组装与供应链管理", ("服务器", "整机", "云厂商", "交付")),
        ("液冷/数据中心温控", ("液冷", "温控", "数据中心", "机柜")),
        ("先进封装/封测与材料", ("先进封装", "封测", "HBM", "封装", "材料")),
        ("国产算力芯片", ("国产算力", "芯片", "CPU", "GPU", "推理", "训练")),
    )
    for node, keywords in mapping:
        if any(keyword in text for keyword in keywords):
            return node
    return "跨节点/待定位"


def fact_companies(text: str, records: list[dict[str, Any]]) -> str:
    names = [str(item.get("name")) for item in records if item.get("name") and str(item.get("name")) in text]
    if names:
        return "、".join(dict.fromkeys(names[:4]))
    fallback = []
    for name in KNOWN_A_SHARE_SYMBOLS:
        if name in text:
            fallback.append(name)
    return "、".join(dict.fromkeys(fallback[:4])) or "未指向单一A股公司"


def hard_fact_candidates(payload: dict[str, Any], records: list[dict[str, Any]], *, pdf_text_live: bool = False) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    relevant_names = {str(item.get("name")) for item in records if item.get("name")}
    relevant_names.update(AI_COMPUTE_ABSOLUTE_CORE)
    relevant_names.update(AI_COMPUTE_HIGH_BETA)
    relevant_symbols = {KNOWN_A_SHARE_SYMBOLS[name] for name in relevant_names if name in KNOWN_A_SHARE_SYMBOLS}

    def add(source_kind: str, title: Any, source: Any = "", date: Any = "") -> None:
        text = " ".join(str(title or "").split())
        if not text:
            return
        category = fact_category(text)
        if not category:
            return
        items.append(
            {
                "category": category,
                "fact": text,
                "node": fact_node(text),
                "companies": fact_companies(text, records),
                "numbers": fact_numbers(text),
                "source": compact(source or source_kind, 28),
                "date": date or payload.get("finished_at", "NA"),
                "strength": fact_strength(source_kind, text),
            }
        )

    for report in payload.get("industry_reports", []) or []:
        if isinstance(report, dict):
            add("industry_report", report.get("title"), report.get("org"), report.get("publish_date") or report.get("date"))
    industry_pdf_rows = [r for r in (payload.get("industry_reports", []) or []) if isinstance(r, dict)]
    for fact in pdf_text.enrich_pdf_facts(industry_pdf_rows, live=pdf_text_live, max_docs=6, snippets_per_doc=3, include_terms=AI_PDF_INCLUDE_TERMS):
        if fact.get("snippet"):
            add("pdf_body", f"{fact.get('title')}：{fact.get('snippet')}", f"{fact.get('source')} PDF正文", fact.get("date"))
    headlines = payload.get("news", {}).get("headlines", []) if isinstance(payload.get("news"), dict) else []
    for headline in headlines or []:
        if isinstance(headline, dict):
            add("news", headline.get("title"), headline.get("source"), headline.get("published_at"))

    supplements = payload.get("stock_supplements", {})
    supplements = supplements if isinstance(supplements, dict) else {}
    if pdf_text_live:
        # PDF 正文增强只拉研报列表，不触发完整行情/历史K线补充，避免生成器被外部源拖死。
        for name in list(AI_COMPUTE_ABSOLUTE_CORE)[:7]:
            symbol = KNOWN_A_SHARE_SYMBOLS.get(name)
            if not symbol or symbol in supplements:
                continue
            try:
                supplements[symbol] = {"research_reports": a_stock_data.fetch_stock_research_reports(symbol, limit=3)}
            except Exception:
                continue
    for symbol, supplement in supplements.items():
        if not isinstance(supplement, dict):
            continue
        if relevant_symbols and str(symbol) not in relevant_symbols:
            continue
        company = next(
            (str(r.get("name")) for r in records if str(r.get("symbol")) == str(symbol)),
            next((name for name, code in KNOWN_A_SHARE_SYMBOLS.items() if code == str(symbol)), str(symbol)),
        )
        announcements = supplement.get("announcements", {})
        for row in (announcements.get("rows", []) if isinstance(announcements, dict) else [])[:6]:
            if isinstance(row, dict):
                add("announcement", f"{company}：{row.get('title')}", row.get("source") or "公告", row.get("date"))
        reports = supplement.get("research_reports", {})
        report_rows = reports.get("rows", []) if isinstance(reports, dict) else []
        for fact in pdf_text.enrich_pdf_facts([r for r in report_rows if isinstance(r, dict)], live=pdf_text_live, max_docs=3, snippets_per_doc=2):
            if fact.get("snippet"):
                add("pdf_body", f"{company}：{fact.get('snippet')}", f"{fact.get('source')} PDF正文", fact.get("date"))
        for row in report_rows[:5]:
            if isinstance(row, dict):
                pe = row.get("pe_forecast")
                eps = row.get("eps_forecast")
                add(
                    "research_report",
                    f"{company}：{row.get('title')}；预测PE{pe if isinstance(pe, dict) else ''}；EPS{eps if isinstance(eps, dict) else ''}",
                    row.get("org") or "券商研报",
                    row.get("publish_date"),
                )
        financials = supplement.get("financials", {})
        statements = financials.get("statements", {}) if isinstance(financials, dict) else {}
        indicators = statements.get("indicators", []) if isinstance(statements, dict) else []
        if indicators and isinstance(indicators[0], dict):
            latest = indicators[0]
            add(
                "financial",
                (
                    f"{company}：{latest.get('REPORT_DATE_NAME') or latest.get('REPORT_DATE')} "
                    f"营收同比{fmt_pct(latest.get('TOTALOPERATEREVETZ'))}，"
                    f"归母净利同比{fmt_pct(latest.get('PARENTNETPROFITTZ'))}，"
                    f"毛利率{fmt_pct(latest.get('XSMLL'))}"
                ),
                "公开财务接口",
                latest.get("REPORT_DATE_NAME") or latest.get("REPORT_DATE"),
            )

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    strength_order = {
        "公告级/High": 0,
        "财报级/High": 1,
        "PDF正文级/Medium-High": 2,
        "研报级/Medium": 3,
        "标题级/Medium-Low": 4,
        "新闻级/Low": 5,
        "线索级/Low": 6,
    }
    for item in sorted(items, key=lambda x: (strength_order.get(str(x.get("strength")), 9), str(x.get("date") or "")), reverse=False):
        key = str(item.get("fact"))[:80]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:18]


def hard_fact_rows(payload: dict[str, Any], records: list[dict[str, Any]], *, pdf_text_live: bool = False) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in hard_fact_candidates(payload, records, pdf_text_live=pdf_text_live):
        implication = {
            "订单/客户": "可直接提升收入兑现置信度；优先核验公告原文和客户名称",
            "价格/涨价": "若与订单共振，说明瓶颈有定价权；单独出现只作为观察",
            "产能/扩产": "判断供给缺口能否持续；扩产过快也可能压制价格",
            "良率/交期": "良率/交期越硬，越接近标杆文里的瓶颈逻辑",
            "财务兑现": "财务已兑现优先于概念映射，但要看收入是否来自目标节点",
            "资本开支": "需求侧强度线索，需要落到供应商订单",
        }.get(str(item.get("category")), "只进入观察池，等待更强证据")
        rows.append(
            [
                item.get("category"),
                compact(item.get("fact"), 88),
                item.get("node"),
                item.get("companies"),
                item.get("numbers"),
                f"{item.get('source')} / {item.get('date')}",
                item.get("strength"),
                implication,
            ]
        )
    if rows:
        return rows
    return [["证据缺口", "本轮未抽到订单、涨价、产能、良率或客户认证的硬事实", "全链路", "未指向", "无", "full-loop", "Low", "不升级交易结论，下一轮优先补证"]]


def evidence_density_rows(fact_rows: list[list[Any]], records: list[dict[str, Any]]) -> list[list[Any]]:
    strengths = [str(row[6]) for row in fact_rows]
    high = sum(1 for x in strengths if "High" in x)
    medium = sum(1 for x in strengths if "Medium" in x)
    low = sum(1 for x in strengths if "Low" in x)
    categories = {str(row[0]) for row in fact_rows if str(row[0]) != "证据缺口"}
    company_hits = {name for row in fact_rows for name in str(row[3]).split("、") if name and name != "未指向单一A股公司"}
    score = min(100, high * 18 + medium * 10 + low * 3 + len(categories) * 6 + len(company_hits) * 4)
    conclusion = "接近标杆文事实密度" if score >= 75 and high >= 3 else "结构完整但硬事实不足" if score >= 45 else "仍以线索和框架为主"
    return [
        ["公告/财报级硬证据", high, "订单、财报、公告风险提示、客户认证等", "越多越接近可交易结论"],
        ["研报/标题级中等证据", medium, "券商研报、行业研报标题、预测PE/EPS", "用于形成假设，不能单独下结论"],
        ["新闻/线索级证据", low, "新闻标题和主题线索", "只进观察，不覆盖强报告"],
        ["覆盖事实类型", len(categories), "订单/价格/产能/良率/财务/capex", "类型越全，越像标杆深度文"],
        ["证据密度评分", score, conclusion, "低于75分时不自称已对标"],
    ]


def fact_summary_bullets(fact_rows: list[list[Any]], *, limit: int = 6) -> str:
    priority = {"订单/客户": 0, "产能/扩产": 1, "价格/涨价": 2, "良率/交期": 3, "资本开支": 4, "财务兑现": 5}
    picked = sorted(
        [row for row in fact_rows if "PDF正文级" in str(row[6])],
        key=lambda row: (priority.get(str(row[0]), 9), len(str(row[1]))),
    )
    if not picked:
        picked = sorted(fact_rows, key=lambda row: priority.get(str(row[0]), 9))
    bullets = []
    for row in picked[:limit]:
        bullets.append(f"- **{row[0]}**：{row[1]}（{row[5]}，{row[6]}）。交易含义：{row[7]}")
    return "\n".join(bullets) if bullets else "- 本轮未取得可写入正文的硬事实。"


def quote_from_payload(payload: dict[str, Any], name: str, symbol: str) -> dict[str, Any]:
    quotes = payload.get("a_share_quotes", [])
    quotes = quotes if isinstance(quotes, list) else []
    for quote in quotes:
        if isinstance(quote, dict) and (str(quote.get("symbol")) == symbol or str(quote.get("name")) == name):
            return quote
    supplements = payload.get("stock_supplements", {})
    supplement = supplements.get(symbol) if isinstance(supplements, dict) else None
    if isinstance(supplement, dict) and isinstance(supplement.get("fundamental"), dict):
        fundamental = dict(supplement["fundamental"])
        fundamental.setdefault("symbol", symbol)
        fundamental.setdefault("name", name)
        return fundamental
    return {}


def supplement_from_payload(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    supplements = payload.get("stock_supplements", {})
    supplement = supplements.get(symbol) if isinstance(supplements, dict) else None
    if a_stock_data.stock_supplement_usable(supplement):
        return supplement
    try:
        return a_stock_data.fetch_stock_supplement_fallback(symbol)
    except Exception:
        return {}


def ensure_price_history(supplement: dict[str, Any], symbol: str, *, live_fetch: bool) -> None:
    if not symbol:
        return
    if price_history_rows(supplement):
        return
    errors = supplement.setdefault("errors", [])
    if not live_fetch:
        try:
            history = a_stock_data.fetch_price_history_fallback(symbol)
            if isinstance(history, dict) and history.get("rows"):
                supplement["price_history"] = history
        except Exception as exc:  # noqa: BLE001
            if isinstance(errors, list):
                errors.append(f"price_history_local:{symbol}:{exc!r}")
        return
    for label, fetcher in (
        ("price_history_live", a_stock_data.fetch_price_history),
        ("price_history_tencent", a_stock_data.fetch_price_history_tencent),
        ("price_history_efinance", a_stock_data.fetch_price_history_efinance),
        ("price_history_baostock", a_stock_data.fetch_price_history_baostock),
        ("price_history_local", a_stock_data.fetch_price_history_fallback),
    ):
        try:
            history = fetcher(symbol)
            if isinstance(history, dict) and history.get("rows"):
                supplement["price_history"] = history
                return
        except Exception as exc:  # noqa: BLE001
            if isinstance(errors, list):
                errors.append(f"{label}:{symbol}:{exc!r}")


def live_company_data(name: str, symbol: str, *, live_fetch: bool) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    errors: list[str] = []
    if not symbol:
        return {}, {}, errors
    quote: dict[str, Any] = {}
    supplement: dict[str, Any] = {}
    if not live_fetch:
        try:
            quote = a_stock_data.fetch_quote_fallback(symbol)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"quote_local:{name}:{symbol}:{exc!r}")
        try:
            supplement = a_stock_data.fetch_stock_supplement_fallback(symbol)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"supplement_local:{name}:{symbol}:{exc!r}")
        return quote, supplement, errors
    try:
        quote = a_stock_data.fetch_quote(symbol)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"quote:{name}:{symbol}:{exc!r}")
    try:
        supplement = a_stock_data.fetch_stock_supplement_resilient(symbol)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"supplement:{name}:{symbol}:{exc!r}")
    return quote, supplement, errors


def bottleneck_company_records(selected: dict[str, Any], payload: dict[str, Any], *, live_fetch: bool = False) -> list[dict[str, Any]]:
    quote_by_name = {str(x.get("name")): x for x in payload.get("a_share_quotes", []) if isinstance(x, dict)}
    analyzer_by_name = {str(x.get("name")): x for x in stock_analyzers(payload)}
    analyzer_by_symbol = {str(x.get("symbol")): x for x in stock_analyzers(payload)}
    decision_map = decisions(payload)
    records: list[dict[str, Any]] = []
    bottlenecks = selected.get("bottleneck_candidates", [])
    bottlenecks = [x for x in bottlenecks if isinstance(x, dict)] if isinstance(bottlenecks, list) else []
    for item in bottlenecks[:6]:
        companies = str(item.get("companies") or "")
        for raw_name in companies.replace("、", ",").replace("，", ",").split(","):
            name = raw_name.strip()
            if not name:
                continue
            symbol = KNOWN_A_SHARE_SYMBOLS.get(name, "")
            quote = quote_from_payload(payload, name, symbol) or quote_by_name.get(name, {})
            supplement = supplement_from_payload(payload, symbol)
            if not quote or not supplement:
                live_quote, live_supplement, errors = live_company_data(name, symbol, live_fetch=live_fetch)
                quote = quote or live_quote
                supplement = supplement or live_supplement
                if errors:
                    supplement = dict(supplement)
                    supplement.setdefault("errors", []).extend(errors)
            symbol = str(quote.get("symbol") or symbol)
            ensure_price_history(supplement, symbol, live_fetch=live_fetch)
            analyzer = analyzer_by_name.get(name) or analyzer_by_symbol.get(symbol) or {}
            valuation = analyzer.get("valuation", {}) if isinstance(analyzer.get("valuation"), dict) else {}
            decision = decision_map.get(symbol, {})
            pe = valuation.get("pe", quote.get("pe"))
            pb = valuation.get("pb", quote.get("pb"))
            technical = technical_snapshot(quote, supplement)
            records.append(
                {
                    "name": name,
                    "symbol": symbol or "未匹配行情代码",
                    "link": item.get("link", "卡口候选"),
                    "price": quote.get("price"),
                    "change_pct": quote.get("change_pct"),
                    "pe": pe,
                    "pb": pb,
                    "quote": quote,
                    "supplement": supplement,
                    "valuation": f"PE {pe if pe is not None else '未取得可靠公开数据'} / PB {pb if pb is not None else '未取得可靠公开数据'}",
                    "financial_note": latest_financial_note(supplement),
                    "research_note": latest_research_note(supplement),
                    "catalyst": item.get("catalyst", "订单/公告/研报正文或客户验证"),
                    "entry": f"{technical['entry']}；同时需要订单、价格或客户认证增量证据",
                    "invalidation": item.get("invalidation", "收入暴露不足"),
                    "evidence_note": f"{latest_financial_note(supplement)}；{latest_research_note(supplement)}",
                    "action": decision.get("action", "watch"),
                    "decision": decision,
                    "has_trade_decision": bool(decision),
                    "decision_scope_present": bool(decision_map),
                    "passed_conditions": decision.get("passed_conditions"),
                    "technical": technical,
                }
            )
    if records:
        return records
    return []


def bottleneck_stock_rows(selected: dict[str, Any], payload: dict[str, Any], *, live_fetch: bool = False) -> list[list[Any]]:
    records = bottleneck_company_records(selected, payload, live_fetch=live_fetch)
    if records:
        return bottleneck_records_to_rows(records)
    return stock_rows(payload)


def bottleneck_records_to_rows(records: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            item["name"],
            item["symbol"],
            item["link"],
            item["valuation"],
            f"{item['financial_note']}；{item['research_note']}",
            item["catalyst"],
            buy_entry_text(item),
            item["invalidation"],
        ]
        for item in records
    ]


def company_mapping_rows_from_records(records: list[dict[str, Any]], evidence_id: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in records:
        name = str(item.get("name") or "NA")
        symbol = str(item.get("symbol") or "NA")
        link = str(item.get("link") or "待验证")
        key = (name, symbol, link)
        if key in seen:
            continue
        seen.add(key)
        financial_note = compact(item.get("financial_note"), 42)
        research_note = compact(item.get("research_note"), 42)
        rows.append(
            [
                name,
                symbol,
                link,
                link,
                "待公告/财报核验收入、订单或客户认证占比",
                link,
                "High/待验证" if any(term in link for term in ("液冷", "电力", "变压器", "UPS", "储能", "CPO", "PCB", "芯片", "封装")) else "Medium/待验证",
                "核心卡口候选" if any(term in link for term in ("液冷", "电力", "变压器", "CPO", "PCB", "芯片")) else "重要配套/待验证",
                f"证据：{evidence_id}；{financial_note}；{research_note}；反证/失效：{item.get('invalidation', '收入暴露不足')}",
            ]
        )
    return rows


def stock_deep_rows(records: list[dict[str, Any]]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in records:
        tech = item.get("technical", {}) if isinstance(item.get("technical"), dict) else {}
        trend = (
            f"现价 {fmt_num(tech.get('price'))}；涨跌幅 {fmt_pct(tech.get('change_pct'))}；"
            f"MA5/10/20/60={fmt_num(tech.get('ma5'))}/{fmt_num(tech.get('ma10'))}/{fmt_num(tech.get('ma20'))}/{fmt_num(tech.get('ma60'))}；"
            f"20日箱体 {fmt_num(tech.get('low20'))}-{fmt_num(tech.get('high20'))}；{tech.get('trend', '趋势待验证')}"
        )
        rows.append(
            [
                item.get("name", "NA"),
                item.get("symbol", "NA"),
                item.get("link", "NA"),
                item.get("valuation", "估值未取得可靠公开数据"),
                item.get("financial_note", "财务待验证"),
                trend,
                f"支撑 {fmt_num(tech.get('support'))}；压力 {fmt_num(tech.get('pressure'))}",
                buy_entry_text(item),
                f"{tech.get('stop', '跌破关键位')}；{item.get('invalidation', '收入暴露不足')}",
                sell_target_text(item),
            ]
        )
    return rows


def competition_rows(records: list[dict[str, Any]], fallback_company_rows: list[list[Any]]) -> list[list[Any]]:
    if not records:
        return [
            [
                row[0] if len(row) > 0 else "NA",
                row[1] if len(row) > 1 else "NA",
                row[2] if len(row) > 2 else "NA",
                row[7] if len(row) > 7 else "待验证",
                row[4] if len(row) > 4 else "财务待验证",
                row[8] if len(row) > 8 else "研报/公告待验证",
                "待验证",
                "收入暴露不足",
            ]
            for row in fallback_company_rows
        ]
    rows: list[list[Any]] = []
    for item in records:
        pe = item.get("pe")
        if isinstance(pe, (int, float)):
            valuation_pressure = "极高" if float(pe) >= 180 else "高" if float(pe) >= 80 else "中"
        else:
            valuation_pressure = "待验证"
        link_text = str(item.get("link") or "")
        directness = (
            "核心卡口候选"
            if any(term in link_text for term in ("CPO", "光模块", "PCB", "服务器", "液冷", "国产算力", "先进封装", "封测"))
            else "重要配套"
        )
        rows.append(
            [
                item.get("name", "NA"),
                item.get("symbol", "NA"),
                item.get("link", "NA"),
                directness,
                item.get("financial_note", "财务待验证"),
                item.get("research_note", "研报待验证"),
                valuation_pressure,
                item.get("invalidation", "收入暴露不足"),
            ]
        )
    return rows


def _growth_score(note: str) -> int:
    score = 0
    for marker in ("营收同比", "归母净利同比", "毛利率"):
        if marker in note:
            score += 1
    for hot in ("100", "150", "200", "262", "568"):
        if hot in note:
            score += 1
            break
    return score


def leadership_tier_rows(records: list[dict[str, Any]]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in records:
        tech = item.get("technical", {}) if isinstance(item.get("technical"), dict) else {}
        pe = _float_or_none(item.get("pe"))
        rr = _float_or_none(tech.get("risk_reward"))
        note = str(item.get("financial_note") or "")
        link = str(item.get("link") or "")
        direct = any(term in link for term in ("CPO", "光模块", "PCB", "服务器", "液冷", "先进封装", "国产算力"))
        score = (3 if direct else 1) + _growth_score(note)
        if rr is not None and rr >= 2:
            score += 1
        if pe is not None and pe >= 180:
            score -= 1
        name = str(item.get("name") or "")
        if name in AI_COMPUTE_ABSOLUTE_CORE:
            tier = "绝对核心龙头"
        elif name in AI_COMPUTE_HIGH_BETA or score >= 3:
            tier = "高弹性二线"
        else:
            tier = "主题观察"
        why = []
        why.append("卡在硬件瓶颈" if direct else "配套/相邻链路")
        if _growth_score(note) >= 2:
            why.append("财务增速可见")
        if rr is not None:
            why.append(f"风险收益比{rr:.2f}")
        if pe is not None:
            why.append(f"PE {pe:.1f}")
        rows.append(
            [
                tier,
                name or "NA",
                item.get("symbol", "NA"),
                item.get("link", "NA"),
                "；".join(why),
                item.get("catalyst", "订单/价格/客户认证"),
                item.get("invalidation", "收入暴露不足"),
            ]
        )
    order = {"绝对核心龙头": 0, "高弹性二线": 1, "主题观察": 2}
    return sorted(rows, key=lambda row: (order.get(str(row[0]), 9), str(row[1])))


def bottleneck_battle_rows(records: list[dict[str, Any]]) -> list[list[Any]]:
    by_link: dict[str, list[dict[str, Any]]] = {}
    for item in records:
        by_link.setdefault(str(item.get("link") or "未分类"), []).append(item)
    rows: list[list[Any]] = []
    for link, items in by_link.items():
        leaders = sorted(
            items,
            key=lambda item: (
                _growth_score(str(item.get("financial_note") or "")),
                _float_or_none(item.get("technical", {}).get("risk_reward") if isinstance(item.get("technical"), dict) else None) or 0,
            ),
            reverse=True,
        )
        names = "、".join(str(x.get("name")) for x in leaders[:3])
        catalysts = "；".join(dict.fromkeys(str(x.get("catalyst") or "订单/价格/客户认证") for x in leaders[:2]))
        invalidations = "；".join(dict.fromkeys(str(x.get("invalidation") or "收入暴露不足") for x in leaders[:2]))
        rows.append(
            [
                link,
                names,
                "供给刚性/认证周期/良率爬坡" if any(t in link for t in ("PCB", "CPO", "先进封装", "液冷")) else "需求放量与国产替代",
                catalysts,
                invalidations,
                "绝对核心" if len(leaders) >= 3 else "样本不足，留观察",
            ]
        )
    return rows


def event_trigger_rows(records: list[dict[str, Any]], payload: dict[str, Any]) -> list[list[Any]]:
    top = records[:8]
    rows: list[list[Any]] = []
    for item in top:
        tech = item.get("technical", {}) if isinstance(item.get("technical"), dict) else {}
        rows.append(
            [
                item.get("name", "NA"),
                item.get("link", "NA"),
                item.get("catalyst", "订单/价格/客户认证"),
                buy_entry_text(item),
                sell_target_text(item),
                item.get("invalidation", "收入暴露不足"),
            ]
        )
    if rows:
        return rows
    return [["待验证", "待验证", "订单/价格/客户认证", "支撑位企稳", "压力位兑现", "收入暴露不足"]]


def build_report(payload: dict[str, Any], theme_key: str, out_dir: Path, *, live_fetch: bool = False, pdf_text_live: bool = False) -> str:
    selected = enrich_theme_selected(theme_key, chain(payload))
    meta = theme_meta(theme_key)
    label = str(meta.get("label") or theme_key)
    chain_map = selected.get("chain_map", {}) if isinstance(selected.get("chain_map"), dict) else {}
    bottlenecks = selected.get("bottleneck_candidates", [])
    bottlenecks = [x for x in bottlenecks if isinstance(x, dict)] if isinstance(bottlenecks, list) else []
    value_rows_raw = selected.get("core_value_distribution", [])
    value_rows_raw = [x for x in value_rows_raw if isinstance(x, dict)] if isinstance(value_rows_raw, list) else []
    company_map = selected.get("company_mapping", [])
    company_map = [x for x in company_map if isinstance(x, dict)] if isinstance(company_map, list) else []

    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    chain_svg = assets / "theme-chain-map.svg"
    bottleneck_svg = assets / "theme-bottleneck-priority.svg"
    chain_png = assets / "theme-chain-map.png"
    bottleneck_png = assets / "theme-bottleneck-priority.png"
    write_chain_svg(chain_svg, label, chain_map, bottlenecks)
    write_bottleneck_svg(bottleneck_svg, label, bottlenecks or value_rows_raw)
    company_records = bottleneck_company_records(selected, payload, live_fetch=live_fetch)
    stock_svg = assets / "theme-stock-valuation.svg"
    stock_png = assets / "theme-stock-valuation.png"
    write_stock_snapshot_svg(stock_svg, label, company_records)
    trade_svg = assets / "theme-trade-map.svg"
    trade_png = assets / "theme-trade-map.png"
    write_trade_map_svg(trade_svg, label, company_records)
    write_chain_png(chain_png, label, chain_map, bottlenecks)
    write_bottleneck_png(bottleneck_png, label, bottlenecks or value_rows_raw)
    write_stock_snapshot_png(stock_png, label, company_records)
    trade_candidates = [record for record in company_records if current_buy_candidate(record)]
    if trade_candidates:
        write_trade_kline_png(trade_png, label, trade_candidates)

    chain_ev = evidence_ref(payload, "ev-chain")
    report_ev = evidence_ref(payload, "ev-report")
    market_ev = evidence_ref(payload, "ev-market-cn")
    review_ev = evidence_ref(payload, "ev-review")

    top_names = "、".join(item.get("name", "") for item in company_records[:5] if item.get("name")) or "待验证公司"
    first_link = compact((bottlenecks[0] or {}).get("link") if bottlenecks else f"{label}核心卡口", 30)
    battle_rows = bottleneck_battle_rows(company_records)
    tier_rows = leadership_tier_rows(company_records)
    trigger_rows = event_trigger_rows(company_records, payload)
    fact_rows = hard_fact_rows(payload, company_records, pdf_text_live=pdf_text_live)
    density_rows = evidence_density_rows(fact_rows, company_records)
    provider_rows = provider_insight_rows(payload)
    absolute_leaders = "、".join(str(row[1]) for row in tier_rows if row[0] == "绝对核心龙头") or top_names
    focus_links = " + ".join(str(item.get("link") or "") for item in bottlenecks[:2] if item.get("link")) or first_link
    bottleneck_scope = "、".join(str(item.get("link") or "") for item in bottlenecks[:5] if item.get("link")) or label
    trade_image_md = (
        "\n\n![现阶段买入候选K线结构](assets/theme-trade-map.png)"
        if trade_candidates
        else "\n\n> 本轮没有通过交易决策与风险收益比门槛的现阶段买入候选，K线支撑/压力图不展开；产业链核心公司仍保留在估值和证据观察表。"
    )
    confidence = "中高" if len(company_records) >= 12 and len(bottlenecks) >= 5 else "中等"

    tech_breakthroughs = [
        f"本轮主题池选中 `{selected.get('selected_theme', theme_key)}`，产业链分数 {selected.get('score', 'NA')}，说明 `{label}` 仍是需持续跟踪的主题。证据：{chain_ev}。",
        f"{label} 的边际变量应落在 {bottleneck_scope} 这些能被订单、客户、收入占比、价格或监管里程碑验证的瓶颈环节。证据：" + chain_ev + "。",
    ]
    market_review = [
        "当前证据仍以结构化产业链分析、公开研报标题和行情快照为主，尚不足以直接确认订单或收入兑现；因此报告结论为“研究主线升级”，不是交易买入结论。",
        f"对标深度研究文章，本报告把核心问题从“AI 是否景气”收敛为“{label} 哪些环节最可能形成真实瓶颈、订单确认或收入兑现”。",
    ]

    key_data_rows = [
        ["本轮 evidence id 数量", len(payload.get("evidence_ids", []) or []), "full-loop result", payload.get("finished_at", "NA"), "High"],
        ["选中主题分数", selected.get("score", "NA"), chain_ev, payload.get("finished_at", "NA"), "Medium"],
        ["第一卡口候选", compact((bottlenecks[0] or {}).get("link") if bottlenecks else "待验证", 28), chain_ev, payload.get("finished_at", "NA"), "Medium"],
        ["卡口公司补充样本", len(company_records), "a-stock-data / public fallback", payload.get("finished_at", "NA"), "Medium"],
    ]
    for item in company_records[:4]:
        key_data_rows.append(
            [
                f"{item.get('name')} 估值/财务",
                f"{item.get('valuation')}；{compact(item.get('financial_note'), 40)}",
                "a-stock-data / eastmoney public",
                payload.get("finished_at", "NA"),
                "Medium",
            ]
        )

    chain_rows = []
    value_distribution_rows = []
    for item in value_rows_raw[:8]:
        value_distribution_rows.append(
            [
                item.get("产业链环节", "NA"),
                item.get("细分领域/关键产品", "NA"),
                item.get("BOM成本占比/价值占比", "待验证"),
                item.get("核心技术壁垒", "NA"),
                item.get("卡脖子程度", "待验证"),
                item.get("代表A股公司", "NA"),
                item.get("公司环节地位", "待验证"),
                item.get("证据口径/备注", chain_ev),
            ]
        )
        chain_rows.append(
            [
                item.get("产业链环节", "NA"),
                item.get("细分领域/关键产品", "NA"),
                "上行" if item.get("卡脖子程度") in {"High", "Medium"} else "待验证",
                item.get("核心技术壁垒") or item.get("卡脖子程度", "NA"),
                item.get("代表A股公司", "NA"),
            ]
        )
    if not chain_rows:
        for item in bottlenecks[:4]:
            chain_rows.append([item.get("link", "NA"), item.get("standards", "待验证"), "待验证", item.get("invalidation", "NA"), item.get("companies", "NA")])
    node_core_rows = []
    for item in bottlenecks[:6]:
        companies = [c.strip() for c in str(item.get("companies") or "").replace("、", ",").replace("，", ",").split(",") if c.strip()]
        padded = (companies + ["待验证核心公司", "待验证核心公司", "待验证核心公司"])[:3]
        node_core_rows.append(
            [
                item.get("link", "NA"),
                padded[0],
                padded[1],
                padded[2],
                item.get("catalyst", "订单/价格/客户验证"),
                item.get("invalidation", "收入暴露不足"),
            ]
        )
    bottleneck_standard_rows = []
    for item in bottlenecks[:6]:
        standards = str(item.get("standards") or item.get("why") or "")
        bottleneck_standard_rows.append(
            [
                item.get("link", "NA"),
                "是" if "不可替代" in standards else "待验证",
                "是" if ("供给刚性" in standards or "良率" in standards or "认证" in standards) else "待验证",
                "是" if "寡头垄断" in standards else "待验证",
                "是" if "机构低配" in standards else "待验证",
                item.get("invalidation", "收入暴露不足"),
            ]
        )

    company_rows = [
        [
            x.get("公司", "NA"),
            x.get("代码", "NA"),
            x.get("环节", "NA"),
            x.get("细分领域", "NA"),
            x.get("产业占比/暴露度", "待公告验证"),
            x.get("核心技术/产品", "NA"),
            x.get("卡脖子相关性", "NA"),
            x.get("环节地位", "NA"),
            x.get("证据与备注", chain_ev),
        ]
        for x in company_map[:8]
    ]
    if not company_rows and company_records:
        company_rows = company_mapping_rows_from_records(company_records, chain_ev)

    source_rows = []
    for item in company_records[:6]:
        source_rows.append(
            [
                f"{item.get('name')} 行情、财务、研报补充",
                "a-stock-data / eastmoney public",
                payload.get("finished_at", "NA"),
                "公开数据/Medium",
                market_ev,
            ]
        )
    for report in (payload.get("industry_reports", []) or [])[:6]:
        if isinstance(report, dict):
            source_rows.append([compact(report.get("title"), 42), report.get("org", "公开研报"), report.get("publish_date") or report.get("date") or "latest", "标题级/Medium", report_ev])
    for headline in (payload.get("news", {}) or {}).get("headlines", [])[:4]:
        if isinstance(headline, dict):
            source_rows.append([compact(headline.get("title"), 42), headline.get("source", "公开资讯"), headline.get("published_at") or "latest", "线索级/Low", evidence_ref(payload, "ev-news")])
    source_rows.extend(
        [
            ["产业链结构化分析", "industry-chain-analysis retained skill", payload.get("finished_at", "NA"), "Medium", chain_ev],
            ["Agent/投委会复核", "loop review", payload.get("finished_at", "NA"), "Medium", review_ev],
        ]
    )
    for row in provider_rows:
        source_rows.append([row[0], row[2], payload.get("finished_at", "NA"), f"外部复核/{row[1]}", row[5]])

    return "\n\n".join(
        [
            f"# {label}主题最终报告",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n> 对标框架：深度研究/每日深度调研式写法；所有可执行结论必须回到 evidence id、订单、产能、价格、估值和反证条件。",
            "## 研究课题\n\n"
            f"本主题研究的问题不是“AI 是否继续发展”，而是 `{label}` 是否已经从叙事进入供需、订单、价格、资本开支、监管合规或国产替代的可证伪阶段。当前主线聚焦 {bottleneck_scope}。研究排序遵循三步：先看谁直接承接真实需求，再看谁有短期供给/认证/交付约束，最后看估值和股价结构是否允许入场。",
            "## 一句话结论\n\n"
            f"强命题：{label} 的研究价值不在泛 AI 标签，而在 `{focus_links}` 是否出现订单、价格、客户认证、收入占比或监管里程碑的硬证据。方向谨慎看多，置信度{confidence}；当前绝对核心候选收敛为：{absolute_leaders}。但只要订单、价格、收入占比或客户认证没有新增证据，就只保持观察，不追高。证据：{chain_ev}。",
            "## 市场盘点\n\n"
            "### 技术突破\n\n- " + "\n- ".join(tech_breakthroughs)
            + f"\n\n### 产能变化\n\n- {label} 的研究价值来自供给刚性、认证周期、数据/工程闭环、客户导入和资本开支共同决定瓶颈能否持续。当前本轮数据只证明“应跟踪”，尚未证明“已紧缺”。证据：" + chain_ev + "。"
            + "\n\n### 订单确认\n\n- 本轮尚未读到可直接证明 A股公司新增订单的公告正文；订单确认仍列为下一轮优先验证项。若后续只有研报标题或概念标签，不升级为正文结论。"
            + "\n\n### 政策 / 监管 / 地缘\n\n- 国产算力、自主可控和供应链安全仍是中期背景变量，但不能替代公司级收入、客户认证和供需数据。"
            + "\n\n### 市场观点\n\n- " + "\n- ".join(market_review),
            "## 核心逻辑\n\n"
            f"1. 需求侧：AI 应用和模型迭代继续推高 `{label}` 相关需求，但需求强度必须通过订单、客户认证、收入占比、价格趋势或政策里程碑验证。\n"
            f"2. 供给侧：利润更可能集中在短期难扩产、认证周期长、替代路线慢、合规壁垒高或工程化交付难的环节，例如 {bottleneck_scope}。\n"
            "3. A股映射：先判断产业链位置，再核验收入/订单暴露，最后才进入估值和交易条件；不能把行情样本或主题标签直接当作核心标的。",
            "## 关键数据\n\n" + md_table(["数据", "数值/变化", "来源", "日期", "置信度"], key_data_rows)
            + "\n\n### 硬事实台账\n\n"
            + "硬事实台账只承认能改变供需、订单、价格、产能、良率、客户认证或财务兑现判断的信息；标题级线索会显式降级，不用于覆盖更强旧结论。\n\n"
            + "### 正文级事实摘要\n\n"
            + fact_summary_bullets(fact_rows)
            + "\n\n"
            + md_table(["事实类型", "硬事实/线索", "涉及节点", "涉及公司", "数值/时间", "来源", "证据强度", "交易含义"], fact_rows)
            + "\n\n### 证据密度评分\n\n"
            + md_table(["维度", "数量/评分", "口径", "含义"], density_rows)
            + ("\n\n### 外部复核与数据路由\n\n" + md_table(["来源", "状态", "复用能力", "本轮信息", "降级策略", "证据id"], provider_rows) if provider_rows else ""),
            "## 产业链跟踪\n\n![产业链图谱](assets/theme-chain-map.png)\n\n"
            + "### 产业链核心环节价值分布\n\n"
            + md_table(
                ["产业链环节", "细分领域/关键产品", "BOM成本占比/价值占比", "核心技术壁垒", "卡脖子程度", "代表A股公司", "公司环节地位", "证据口径/备注"],
                value_distribution_rows,
            )
            + "\n\n### 供需链路跟踪\n\n"
            + md_table(["环节", "事实映射", "供需变化方向", "瓶颈/卡口", "A股映射"], chain_rows)
            + "\n\n### 核心节点三公司校验\n\n"
            + "每个产业链节点至少保留三家处于当前节点绝对核心地位、且能通过行情/财务/研报进一步跟踪的 A 股公司；少于三家则不得升级为成熟节点。\n\n"
            + md_table(["产业链节点", "核心公司1", "核心公司2", "核心公司3", "升级催化", "失效条件"], node_core_rows)
            + "\n\n### 瓶颈战斗地图\n\n"
            + md_table(["瓶颈节点", "当前三家核心公司", "为什么卡", "升级信号", "反证信号", "节点结论"], battle_rows)
            + "\n\n### 瓶颈四标准校验\n\n"
            + md_table(["候选环节", "不可替代", "供给刚性", "寡头垄断", "机构低配", "反证条件"], bottleneck_standard_rows),
            "## 投资机会挖掘\n\n"
            "### 瓶颈识别\n\n![卡口优先级](assets/theme-bottleneck-priority.png)\n\n"
            + "\n".join(f"- {idx + 1}. {item.get('link', '候选卡口')}：代表公司 {item.get('companies', '待验证')}；催化 {item.get('catalyst', '订单/公告/客户验证')}；失效条件 {item.get('invalidation', '收入暴露不足')}。证据：{chain_ev}。" for idx, item in enumerate(bottlenecks[:5]))
            + "\n\n### 可交易标的筛选\n\n- 直接暴露优先于相邻链路；公告/财报证明优先于研报标题；估值赔率优先于短期涨幅。当前所有候选仍需“收入占比/订单/客户认证”三项中的至少一项补强。",
            "## A股可交易标的估值对比\n\n![A股候选估值图](assets/theme-stock-valuation.png)"
            + trade_image_md
            + "\n\n"
            + md_table(["公司", "代码", "产业链位置", "当前估值", "财务/订单信号", "催化", "买点条件", "失效条件"], bottleneck_records_to_rows(company_records) if company_records else stock_rows(payload)),
            "## 核心个股交易跟踪\n\n"
            + md_table(
                ["公司", "代码", "产业链位置", "估值", "财务质量", "趋势结构", "关键位", "买入条件", "止损/失效", "卖出/目标"],
                stock_deep_rows(company_records) if company_records else [],
            )
            + "\n\n这张表的作用是把产业逻辑落到交易纪律：现价接近压力位且风险收益比不足时，即便产业逻辑强，也只能等待回踩或新的订单证据；现价回到支撑区但订单/毛利/收入占比无验证，同样不能升级。",
            "## 产业链 / 竞争格局\n\n"
            + "### A股公司映射与核心地位判断\n\n"
            + md_table(["公司", "代码", "环节", "细分领域", "产业占比/暴露度", "核心技术/产品", "卡脖子相关性", "环节地位", "证据与备注"], company_rows)
            + "\n\n### 竞争格局与反证条件\n\n"
            + md_table(["公司", "代码", "卡口环节", "直接性", "财务信号", "研报/公告信号", "估值压力", "反证条件"], competition_rows(company_records, company_rows))
            + f"\n\n竞争判断：{label} 中具备客户认证、数据闭环、合规壁垒、良率/交付和产能约束的环节更接近“瓶颈资产”；但若估值已经处在高压区，只有订单、价格、客户认证或收入占比继续补强，才能从“产业链好公司”升级为“可执行机会”。缺少差异化的概念映射容易只获得主题估值而非利润传导。",
            "## 标的分层与入场条件\n\n"
            "### 龙头分层\n\n"
            + md_table(["层级", "公司", "代码", "节点", "入选原因", "升级触发器", "降级/剔除条件"], tier_rows)
            + "\n\n"
            f"- 核心环节龙头：{bottleneck_scope} 等直接受益且收入暴露可验证的公司；入场条件是订单、价格或客户认证出现增量证据。\n"
            "- 关键技术突破者：国产替代、工程化交付、合规/数据壁垒或关键产品性能有明确突破的公司；入场条件是从研报线索升级到公告/财报/客户证据。\n"
            "- 重要配套：基础设施、渠道、交付和生态配套；入场条件是资本开支、客户数和交付量持续确认。\n"
            "- 待验证概念：仅有 AI 标签或行情异动但缺少收入暴露的公司；默认留在观察池。\n\n"
            "### 事件-交易触发器\n\n"
            + md_table(["公司", "节点", "需要等待的硬证据", "买入触发", "卖出/减仓触发", "反证退出"], trigger_rows),
            "## 风险、反证与退出条件\n\n"
            "- 订单反证：公告、年报或调研无法验证新增订单、客户认证或收入占比。\n"
            "- 供给反证：替代路线成熟、扩产过快或价格回落，导致卡口缓解。\n"
            "- 估值反证：估值和成交拥挤先于基本面兑现，风险收益比低于 2:1。\n"
            "- 主题反证：新闻/研报热度上升但公司财务、订单和价格信号没有同步改善。",
            "## 数据来源与证据强度\n\n" + md_table(["结论/数据", "来源", "日期", "置信度", "证据id"], source_rows[:14]),
        ]
    ) + "\n"


def write_theme_outputs(report: str, payload_file: Path, theme_key: str) -> tuple[Path, Path, bool]:
    out_dir = ROOT / "reports" / "themes" / theme_key
    drafts_dir = out_dir / "drafts"
    out_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    slug = draft_slug_from_payload(payload_file)
    draft_path = out_dir / f"report.cycle-draft-{slug}.md"
    draft_path.write_text(report, encoding="utf-8")
    (drafts_dir / f"{slug}.md").write_text(report, encoding="utf-8")
    canonical_path = out_dir / "report.md"
    return canonical_path, draft_path, False


def quality(report: str) -> dict[str, Any]:
    missing = [section for section in BENCHMARK_REPORT_SECTIONS if section not in report]
    image_count = report.count("![")
    todo_count = report.count("待补")
    passed = not missing and image_count >= 3 and todo_count <= 1 and len(report) >= 3000
    return {
        "passed": passed,
        "missing_sections": missing,
        "image_count": image_count,
        "todo_count": todo_count,
        "char_count": len(report),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-file", default="data/raw/latest-full-loop.json")
    parser.add_argument("--theme-key", default="", help="Override selected theme with a config/theme_pool.json key.")
    parser.add_argument("--live-fetch", action="store_true", help="Fetch missing quote/supplement data from public providers; off by default to keep loop bounded.")
    parser.add_argument("--pdf-text", action="store_true", help="Download/extract selected report PDF text for hard-fact mining; cached text is reused in later bounded runs.")
    args = parser.parse_args()
    payload_file = ROOT / args.payload_file
    payload = read_json(payload_file)
    if args.theme_key:
        payload = json.loads(json.dumps(payload, ensure_ascii=False))
        pipeline = payload.setdefault("research_pipeline", {})
        if isinstance(pipeline, dict):
            selected = pipeline.setdefault("selected_industry_chain", {})
            if isinstance(selected, dict):
                selected["selected_theme"] = args.theme_key
                selected.setdefault("score", 0)
    selected = chain(payload)
    theme_key = resolve_theme_key(str(selected.get("selected_theme") or ""), ROOT) or "uncategorized"
    out_dir = ROOT / "reports" / "themes" / theme_key
    report = build_report(payload, theme_key, out_dir, live_fetch=args.live_fetch, pdf_text_live=args.pdf_text)
    canonical_path, draft_path, seeded = write_theme_outputs(report, payload_file, theme_key)
    q = quality(report)
    source_data = {
        "generated_at": datetime.now().isoformat(),
        "payload_file": rel(payload_file),
        "theme_key": theme_key,
        "selected_theme": selected.get("selected_theme"),
        "evidence_ids": payload.get("evidence_ids", []),
        "quality": q,
    }
    (out_dir / "source_data.json").write_text(json.dumps(source_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": rel(canonical_path),
                "draft": rel(draft_path),
                "theme_key": theme_key,
                "seeded_canonical": seeded,
                "quality": q,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if q["passed"] else 1)


if __name__ == "__main__":
    main()
