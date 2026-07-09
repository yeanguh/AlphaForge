from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from providers.open_source import a_stock_data, wen_cai  # noqa: E402

REPORT_DATE = datetime.now().strftime("%Y-%m-%d")
OUT = ROOT / "reports" / "industry" / f"physical-ai-chain-analysis-{REPORT_DATE}"
ASSETS = OUT / "assets"

SELECTED_SYMBOLS: dict[str, dict[str, str]] = {
    "688017": {
        "name": "绿的谐波",
        "chain_position": "减速器/精密传动",
        "chain_thesis": "上游精密传动主研究位；若机器人订单兑现，卡口属性最直接",
        "financial_note": "核心看机器人相关订单、客户认证、毛利率和产能利用率",
        "evidence_note": "已有财报高增长和研报覆盖，但订单/收入占比仍需公告验证",
    },
    "000837": {
        "name": "秦川机床",
        "chain_position": "丝杠/机床/精密加工",
        "chain_thesis": "丝杠和精密机床是运动执行链的重要配套，弹性取决于机器人业务直接暴露",
        "financial_note": "核心看滚动功能部件、机床订单和机器人链客户验证",
        "evidence_note": "保留为关键技术突破者，需继续核验收入占比和客户名单",
    },
    "603728": {
        "name": "鸣志电器",
        "chain_position": "电机/控制",
        "chain_thesis": "电机与运动控制是机器人执行单元的重要环节，壁垒低于减速器但应用广",
        "financial_note": "核心看高端电机/控制产品放量、毛利率和海外/机器人客户",
        "evidence_note": "保留为重要配套，需验证人形机器人订单和收入弹性",
    },
}


def fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def money(value: Any) -> str:
    if value is None:
        return "NA"
    try:
        num = float(value)
    except Exception:
        return str(value)
    if abs(num) >= 100_000_000:
        return f"{num / 100_000_000:.2f}亿"
    if abs(num) >= 10_000:
        return f"{num / 10_000:.2f}万"
    return f"{num:.2f}"


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", "<br>") for cell in row) + " |")
    return "\n".join(lines)


def compact(value: Any, limit: int = 42) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def source_url(item: dict[str, Any]) -> str:
    for key in ("url", "pdf_url", "link"):
        value = item.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
    info_code = item.get("info_code") or item.get("infoCode")
    if not info_code and isinstance(item.get("raw"), dict):
        info_code = item["raw"].get("infoCode")
    return f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf" if info_code else ""


def wencai_summary_rows(enrichment: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for row in wen_cai.summarize_enrichment(enrichment):
        if row.get("status") == "skipped":
            continue
        usage = {
            "sector_hotspots": "板块热度/资金面交叉验证",
            "robotics_reports": "行业研报线索补充",
            "robotics_news": "产业催化与新闻事件补充",
        }.get(str(row.get("key")), "公司经营/评级/事件证据补充")
        rows.append(
            [
                row.get("key"),
                row.get("qtype"),
                compact(row.get("query"), 36),
                row.get("status"),
                row.get("count"),
                compact(row.get("sample") or "字段：" + ",".join(row.get("fields") or []), 46),
                usage,
            ]
        )
    return rows


def svg_to_png(svg: Path) -> Path:
    png = svg.with_suffix(".png")
    subprocess.run(["rsvg-convert", str(svg), "-o", str(png)], check=True)
    return png


def write_chain_svg(path: Path) -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1500" viewBox="0 0 1200 1500">
<style>
text{font-family:'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',Arial,sans-serif}
.title{font-size:34px;font-weight:800;fill:#111827}.h{font-size:24px;font-weight:800;fill:#0f172a}
.n{font-size:19px;font-weight:700;fill:#111827}.s{font-size:15px;fill:#374151}
.box{rx:18;stroke-width:2}.main{fill:#eff6ff;stroke:#2563eb}.up{fill:#ecfdf5;stroke:#16a34a}
.mid{fill:#fff7ed;stroke:#ea580c}.down{fill:#f5f3ff;stroke:#7c3aed}.risk{fill:#fff1f2;stroke:#e11d48;stroke-dasharray:10 8}
.arrow{stroke:#2563eb;stroke-width:4;marker-end:url(#arrow)}
</style>
<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M2,2 L10,6 L2,10 Z" fill="#2563eb"/></marker></defs>
<rect width="1200" height="1500" fill="#ffffff"/>
<text x="60" y="70" class="title">1分钟拆解产业链：物理AI/人形机器人核心零部件</text>
<text x="60" y="112" class="s">研究主线：企业AI扩散 + 人形机器人量产爬坡 -> 物理世界执行系统 -> 上游精密传动/控制/传感卡口</text>

<rect x="60" y="150" width="250" height="110" class="box main"/><text x="82" y="188" class="n">需求触发</text><text x="82" y="220" class="s">企业AI进入工作流</text><text x="82" y="246" class="s">具身智能从演示到量产</text>
<rect x="335" y="150" width="250" height="110" class="box main"/><text x="357" y="188" class="n">价格信号</text><text x="357" y="220" class="s">绿的谐波单日-15.93%</text><text x="357" y="246" class="s">市场惩罚远期叙事</text>
<rect x="610" y="150" width="250" height="110" class="box main"/><text x="632" y="188" class="n">研究焦点</text><text x="632" y="220" class="s">不买主题，找卡口</text><text x="632" y="246" class="s">订单/客户/良率验证</text>
<rect x="885" y="150" width="250" height="110" class="box main"/><text x="907" y="188" class="n">核心标的</text><text x="907" y="220" class="s">绿的谐波：主研究位</text><text x="907" y="246" class="s">宁德时代：相邻验证位</text>

<text x="520" y="325" class="h">上游卡口</text>
<rect x="170" y="360" width="260" height="120" class="box up"/><text x="195" y="400" class="n">减速器/丝杠</text><text x="195" y="432" class="s">运动精度、寿命、负载</text><text x="195" y="458" class="s">代表：绿的谐波/秦川机床</text>
<rect x="470" y="360" width="260" height="120" class="box up"/><text x="495" y="400" class="n">伺服电机/控制器</text><text x="495" y="432" class="s">响应速度、控制精度</text><text x="495" y="458" class="s">代表：鸣志电器/汇川技术</text>
<rect x="770" y="360" width="260" height="120" class="box up"/><text x="795" y="400" class="n">传感器/精密加工</text><text x="795" y="432" class="s">感知、良率、检测</text><text x="795" y="458" class="s">代表：待验证配套链</text>
<line x1="600" y1="500" x2="600" y2="585" class="arrow"/>

<text x="510" y="635" class="h">中游制造</text>
<rect x="250" y="670" width="300" height="125" class="box mid"/><text x="280" y="712" class="n">人形机器人本体</text><text x="280" y="746" class="s">BOM集成、工程交付</text><text x="280" y="772" class="s">验证：量产爬坡/客户订单</text>
<rect x="650" y="670" width="300" height="125" class="box mid"/><text x="680" y="712" class="n">工程机械/通用设备</text><text x="680" y="746" class="s">电动化、智能化设备</text><text x="680" y="772" class="s">验证：销量/出口/资本开支</text>
<line x1="600" y1="815" x2="600" y2="900" class="arrow"/>

<text x="520" y="950" class="h">下游应用</text>
<rect x="170" y="985" width="260" height="120" class="box down"/><text x="195" y="1026" class="n">工厂自动化</text><text x="195" y="1058" class="s">替代人工、柔性生产</text><text x="195" y="1084" class="s">看订单和ROI</text>
<rect x="470" y="985" width="260" height="120" class="box down"/><text x="495" y="1026" class="n">物流搬运</text><text x="495" y="1058" class="s">仓储、装卸、配送</text><text x="495" y="1084" class="s">看场景复制</text>
<rect x="770" y="985" width="260" height="120" class="box down"/><text x="795" y="1026" class="n">服务/施工场景</text><text x="795" y="1058" class="s">工程机械、服务机器人</text><text x="795" y="1084" class="s">看销量和客户验证</text>

<rect x="120" y="1190" width="960" height="135" class="box risk"/><text x="150" y="1232" class="n">反证退出</text><text x="150" y="1266" class="s">1. 无订单/客户认证/收入占比证据；2. 高估值继续杀跌且无基本面修复；3. 替代路线成熟或扩产过快压低毛利。</text>
<text x="150" y="1300" class="s">结论：当前不是“买AI主题”，而是验证精密传动等上游卡口能否从概念变成订单和利润。</text>
</svg>"""
    path.write_text(svg, encoding="utf-8")


def _series_xy(values: list[float | None], *, min_v: float, max_v: float, left: int, right: int, top: int, bottom: int, width: int, height: int) -> str:
    span = max(max_v - min_v, 1e-9)
    pts = []
    count = len(values)
    for i, value in enumerate(values):
        if value is None:
            continue
        x = left + i / max(count - 1, 1) * (width - left - right)
        y = top + (max_v - value) / span * (height - top - bottom)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def _rolling(values: list[float], window: int) -> list[float | None]:
    output: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            output.append(None)
        else:
            part = values[idx + 1 - window : idx + 1]
            output.append(sum(part) / window)
    return output


def write_line_svg(path: Path, rows: list[dict[str, Any]], title: str, tech: dict[str, Any] | None = None) -> None:
    data = [r for r in rows if isinstance(r.get("close"), (int, float))]
    data = data[-90:]
    width, height = 1100, 640
    left, right, top, bottom = 75, 30, 55, 55
    if len(data) < 2:
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><text x="40" y="80">历史价格数据不足</text></svg>', encoding="utf-8")
        return
    closes = [float(r["close"]) for r in data]
    ma20 = _rolling(closes, 20)
    ma60 = _rolling(closes, 60)
    marker_values = []
    if tech:
        for key in ("support1", "support2", "resistance1", "resistance2"):
            if isinstance(tech.get(key), (int, float)):
                marker_values.append(float(tech[key]))
    min_v, max_v = min(closes + marker_values), max(closes + marker_values)
    span = max(max_v - min_v, 1e-9)
    close_pts = _series_xy(closes, min_v=min_v, max_v=max_v, left=left, right=right, top=top, bottom=bottom, width=width, height=height)
    ma20_pts = _series_xy(ma20, min_v=min_v, max_v=max_v, left=left, right=right, top=top, bottom=bottom, width=width, height=height)
    ma60_pts = _series_xy(ma60, min_v=min_v, max_v=max_v, left=left, right=right, top=top, bottom=bottom, width=width, height=height)
    grid = []
    for i in range(5):
        y = top + i * (height - top - bottom) / 4
        val = max_v - i * span / 4
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        grid.append(f'<text x="18" y="{y+5:.1f}" font-size="14" fill="#4b5563">{val:.1f}</text>')
    markers = []
    if tech:
        for label, key, color in (
            ("S1", "support1", "#16a34a"),
            ("S2", "support2", "#15803d"),
            ("R1", "resistance1", "#dc2626"),
            ("R2", "resistance2", "#991b1b"),
        ):
            value = tech.get(key)
            if isinstance(value, (int, float)):
                y = top + (max_v - float(value)) / span * (height - top - bottom)
                markers.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{color}" stroke-width="1.8" stroke-dasharray="8 7"/>')
                markers.append(f'<text x="{width-right-82}" y="{y-7:.1f}" font-size="13" font-weight="700" fill="{color}">{label} {float(value):.2f}</text>')
    svg = "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="32" font-size="22" font-weight="800" fill="#111827">{title}</text>',
        *grid,
        *markers,
        f'<polyline fill="none" stroke="#2563eb" stroke-width="3" points="{close_pts}"/>',
        f'<polyline fill="none" stroke="#f59e0b" stroke-width="2" points="{ma20_pts}"/>',
        f'<polyline fill="none" stroke="#7c3aed" stroke-width="2" points="{ma60_pts}"/>',
        f'<text x="{left}" y="{height-18}" font-size="14" fill="#374151">{data[0].get("date")}</text>',
        f'<text x="{width-right-100}" y="{height-18}" font-size="14" fill="#374151">{data[-1].get("date")}</text>',
        f'<text x="{width-right-190}" y="32" font-size="15" fill="#111827">最新 {closes[-1]:.2f}</text>',
        f'<text x="{left+245}" y="32" font-size="14" fill="#2563eb">收盘</text>',
        f'<text x="{left+300}" y="32" font-size="14" fill="#f59e0b">MA20</text>',
        f'<text x="{left+365}" y="32" font-size="14" fill="#7c3aed">MA60</text>',
        "</svg>",
    ])
    path.write_text(svg, encoding="utf-8")


def write_bar_svg(path: Path, rows: list[tuple[str, float, str]], title: str) -> None:
    width, height = 1100, 640
    left, top, bar_h, gap = 240, 70, 34, 22
    max_v = max([abs(v) for _, v, _ in rows] or [1])
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="35" y="36" font-size="22" font-weight="800" fill="#111827">{title}</text>',
    ]
    for i, (label, value, display) in enumerate(rows[:7]):
        y = top + i * (bar_h + gap)
        w = max(3, abs(value) / max_v * (width - left - 140))
        color = "#16a34a" if value >= 0 else "#dc2626"
        lines.append(f'<text x="35" y="{y+23}" font-size="15" fill="#374151">{label}</text>')
        lines.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="6" fill="{color}" opacity="0.85"/>')
        lines.append(f'<text x="{left+w+12:.1f}" y="{y+23}" font-size="15" fill="#111827">{display}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def ensure_history(supp: dict[str, Any], symbol: str) -> None:
    rows = supp.get("price_history", {}).get("rows", []) if isinstance(supp.get("price_history"), dict) else []
    if rows:
        return
    try:
        supp["price_history"] = a_stock_data.fetch_price_history(symbol)
    except Exception as exc:  # noqa: BLE001
        supp.setdefault("errors", []).append(f"price_history_live: {exc!r}")
        try:
            supp["price_history"] = a_stock_data.fetch_price_history_fallback(symbol)
        except Exception as fallback_exc:  # noqa: BLE001
            supp.setdefault("errors", []).append(f"price_history_live_fallback: {fallback_exc!r}")


def _last(values: list[float], n: int) -> list[float]:
    return values[-n:] if len(values) >= n else values


def _ma(values: list[float], n: int) -> float | None:
    part = _last(values, n)
    return sum(part) / len(part) if len(part) == n else None


def _round_price(value: float | None) -> float | None:
    return round(value, 2) if isinstance(value, (int, float)) else None


def technical_structure(quote: dict[str, Any], supp: dict[str, Any]) -> dict[str, Any]:
    history = supp.get("price_history", {}).get("rows", []) if isinstance(supp.get("price_history"), dict) else []
    clean = [r for r in history if isinstance(r.get("close"), (int, float)) and isinstance(r.get("high"), (int, float)) and isinstance(r.get("low"), (int, float))]
    closes = [float(r["close"]) for r in clean]
    highs_all = [float(r["high"]) for r in clean]
    lows_all = [float(r["low"]) for r in clean]
    volumes = [float(r["volume"]) for r in clean if isinstance(r.get("volume"), (int, float))]
    price = quote.get("price")
    if not isinstance(price, (int, float)) and closes:
        price = closes[-1]
    price = float(price) if isinstance(price, (int, float)) else None
    ma5 = _ma(closes, 5)
    ma10 = _ma(closes, 10)
    ma20 = _ma(closes, 20)
    ma60 = _ma(closes, 60)
    high20 = max(_last(highs_all, 20)) if len(highs_all) >= 20 else None
    low20 = min(_last(lows_all, 20)) if len(lows_all) >= 20 else None
    high60 = max(_last(highs_all, 60)) if len(highs_all) >= 60 else None
    low60 = min(_last(lows_all, 60)) if len(lows_all) >= 60 else None
    high120 = max(_last(highs_all, 120)) if len(highs_all) >= 120 else high60
    low120 = min(_last(lows_all, 120)) if len(lows_all) >= 120 else low60
    ma20_prev = None
    if len(closes) >= 30:
        ma20_prev = sum(closes[-30:-10]) / 20
    ma20_slope = (ma20 - ma20_prev) / ma20_prev * 100 if ma20 and ma20_prev else None
    position60 = (price - low60) / (high60 - low60) if price is not None and high60 and low60 and high60 > low60 else None
    avg_vol20 = sum(_last(volumes, 20)) / 20 if len(volumes) >= 20 else None
    avg_vol5 = sum(_last(volumes, 5)) / 5 if len(volumes) >= 5 else None
    volume_state = "量能放大" if avg_vol20 and avg_vol5 and avg_vol5 > avg_vol20 * 1.25 else "量能收敛/常态" if avg_vol20 and avg_vol5 else "量能数据不足"

    support_candidates = [v for v in (ma5, ma10, ma20, ma60, low20, low60, low120) if isinstance(v, (int, float)) and price is not None and v <= price]
    resistance_candidates = [v for v in (ma5, ma10, ma20, ma60, high20, high60, high120) if isinstance(v, (int, float)) and price is not None and v >= price]
    support_candidates = sorted(set(round(v, 4) for v in support_candidates), reverse=True)
    resistance_candidates = sorted(set(round(v, 4) for v in resistance_candidates))
    support1 = support_candidates[0] if support_candidates else low20
    support2 = support_candidates[1] if len(support_candidates) > 1 else low60
    resistance1 = resistance_candidates[0] if resistance_candidates else high20
    resistance2 = resistance_candidates[1] if len(resistance_candidates) > 1 else high60

    score = 0.0
    if price is not None and ma20 and price > ma20:
        score += 1.0
    if ma20 and ma60 and ma20 > ma60:
        score += 1.0
    if ma20_slope is not None and ma20_slope > 0:
        score += 1.0
    if position60 is not None and 0.25 <= position60 <= 0.85:
        score += 0.75
    if avg_vol20 and avg_vol5 and avg_vol5 >= avg_vol20 * 0.8:
        score += 0.75
    if price is not None and low20 and price > low20:
        score += 0.5
    score = round(min(score, 5.0), 2)

    if price is None:
        trend = "价格数据不足"
    elif ma20 and ma60 and price > ma20 > ma60 and (ma20_slope or 0) > 0:
        trend = "多头趋势修复/延续"
    elif ma20 and ma60 and price < ma20 < ma60:
        trend = "空头压制/破位后修复前"
    elif ma20 and abs(price / ma20 - 1) <= 0.04:
        trend = "围绕MA20震荡，等待方向选择"
    elif ma60 and abs(price / ma60 - 1) <= 0.06:
        trend = "回踩中期均线，观察承接"
    else:
        trend = "宽幅震荡，需突破确认"

    if price is not None and support1 and resistance1:
        buy_zone = f"左侧只看{support1:.2f}附近缩量企稳；右侧需放量站回/突破{resistance1:.2f}"
    else:
        buy_zone = "数据不足，暂不设买点"
    if support2:
        stop_loss = f"有效跌破{support2:.2f}且两日不能收回，技术结构失效"
    elif low60:
        stop_loss = f"跌破60日箱体下沿{low60:.2f}，技术结构失效"
    else:
        stop_loss = "数据不足"
    pressure = f"{fmt(resistance1)}/{fmt(resistance2)}" if resistance1 or resistance2 else "数据不足"

    reports = supp.get("research_reports", {}).get("rows", []) if isinstance(supp.get("research_reports"), dict) else []
    eps = []
    pe_forecasts = []
    for r in reports:
        if isinstance(r.get("eps_forecast"), dict):
            for k in ("next_year", "next_two_year", "this_year"):
                v = r["eps_forecast"].get(k)
                if isinstance(v, (int, float)):
                    eps.append(float(v))
                    break
        if isinstance(r.get("pe_forecast"), dict):
            v = r["pe_forecast"].get("next_two_year") or r["pe_forecast"].get("next_year")
            if isinstance(v, (int, float)):
                pe_forecasts.append(float(v))
    eps_anchor = sorted(eps)[len(eps) // 2] if eps else None
    return {
        "price": price,
        "last_history_date": clean[-1].get("date") if clean else "",
        "ma5": _round_price(ma5),
        "ma10": _round_price(ma10),
        "ma20": _round_price(ma20),
        "ma60": _round_price(ma60),
        "ma20_slope_pct": _round_price(ma20_slope),
        "high20": _round_price(high20),
        "low20": _round_price(low20),
        "high60": _round_price(high60),
        "low60": _round_price(low60),
        "high120": _round_price(high120),
        "low120": _round_price(low120),
        "position60": _round_price(position60 * 100 if position60 is not None else None),
        "support1": _round_price(support1),
        "support2": _round_price(support2),
        "resistance1": _round_price(resistance1),
        "resistance2": _round_price(resistance2),
        "trend": trend,
        "volume_state": volume_state,
        "institutional_trend_score": score,
        "buy_zone": buy_zone,
        "stop_loss": stop_loss,
        "pressure": pressure,
        "eps_anchor": eps_anchor,
        "target_low": eps_anchor * 100 if eps_anchor else None,
        "target_mid": eps_anchor * 140 if eps_anchor else None,
        "target_high": eps_anchor * 180 if eps_anchor else None,
        "sellside_pe_median": sorted(pe_forecasts)[len(pe_forecasts) // 2] if pe_forecasts else None,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    payload = json.loads((ROOT / "data/raw/latest-full-loop.json").read_text(encoding="utf-8"))
    quotes = {q["symbol"]: q for q in payload.get("a_share_quotes", [])}
    supplements = payload.get("stock_supplements", {})

    selected: dict[str, dict[str, Any]] = {}
    for symbol, meta in SELECTED_SYMBOLS.items():
        quote = quotes.get(symbol)
        if not quote:
            try:
                quote = a_stock_data.fetch_quote(symbol)
            except Exception as exc:  # noqa: BLE001
                quote = {"symbol": symbol, "name": meta["name"], "errors": [repr(exc)]}
        quotes[symbol] = quote
        supp = supplements.setdefault(symbol, {})
        if not supp or not isinstance(supp.get("financials"), dict):
            try:
                fetched = a_stock_data.fetch_stock_supplement(symbol)
                fetched.update({k: v for k, v in supp.items() if v})
                supp = fetched
                supplements[symbol] = supp
            except Exception as exc:  # noqa: BLE001
                supp.setdefault("errors", []).append(f"stock_supplement: {exc!r}")
        ensure_history(supp, symbol)
        tech = technical_structure(quote, supp)
        selected[symbol] = {"meta": meta, "quote": quote, "supplement": supp, "tech": tech}

    focus = "688017"
    focus_supp = selected[focus]["supplement"]
    focus_quote = selected[focus]["quote"]
    lv = selected[focus]["tech"]
    wencai_enrichment = wen_cai.fetch_research_enrichment({symbol: item["meta"]["name"] for symbol, item in selected.items()})
    wencai_rows = wencai_summary_rows(wencai_enrichment)

    chain_svg = ASSETS / "physical-ai-chain-map.svg"
    write_chain_svg(chain_svg)
    chain_png = svg_to_png(chain_svg)
    price_pngs: dict[str, Path] = {}
    for symbol, item in selected.items():
        meta = item["meta"]
        price_svg = ASSETS / f"{symbol}-technical-structure.svg"
        write_line_svg(
            price_svg,
            item["supplement"].get("price_history", {}).get("rows", []),
            f"{meta['name']} {symbol} 90日趋势/支撑压力",
            item["tech"],
        )
        price_pngs[symbol] = svg_to_png(price_svg)

    indicators = focus_supp.get("financials", {}).get("statements", {}).get("indicators", [])
    fin_rows = []
    for row in indicators[:6]:
        label = str(row.get("REPORT_DATE_NAME") or row.get("REPORT_DATE", ""))[:10]
        yoy = row.get("TOTALOPERATEREVETZ")
        if isinstance(yoy, (int, float)):
            fin_rows.append((label, float(yoy), f"营收同比 {float(yoy):.1f}%"))
    finance_png = None
    if fin_rows:
        finance_svg = ASSETS / "green-harmonic-revenue-growth.svg"
        write_bar_svg(finance_svg, fin_rows, "绿的谐波营收同比变化")
        finance_png = svg_to_png(finance_svg)

    reports = focus_supp.get("research_reports", {}).get("rows", [])
    announcements = focus_supp.get("announcements", {}).get("rows", [])
    latest_fin = indicators[0] if indicators else {}
    industry_reports = payload.get("industry_reports", [])
    news = payload.get("news", {}).get("headlines", [])

    value_rows = [
        ["上游", "减速器/丝杠/伺服系统", "定性高", "精密加工、寿命、客户认证", "高", "绿的谐波、秦川机床、鸣志电器", "卡口候选/重要配套", "需订单和收入占比验证"],
        ["中游", "本体与系统集成", "中高", "工程交付、成本控制、场景数据", "中", "埃斯顿、汇川技术", "核心/重要", "需区分机器人业务收入占比"],
        ["相邻", "新能源/储能/工程机械电动化", "中", "电池、电驱、设备电动化客户", "低-中", "宁德时代", "相邻基础设施", "不能替代机器人核心链证据"],
    ]
    company_rows = [
        ["绿的谐波", "688017", "上游", "减速器/核心零部件", "未披露；产品与精密传动直接相关", "谐波减速器/精密传动", "高/待公告验证", "主研究位/卡口候选", "2026Q1营收同比42.96%、归母净利同比61.17%；最新风险提示公告需重视"],
        ["秦川机床", "000837", "上游", "丝杠/机床/核心零部件", "待核验", "精密机床与传动部件", "中-高", "重要配套", "需补公告、订单、机器人收入占比"],
        ["鸣志电器", "603728", "上游", "电机/控制", "待核验", "步进/伺服电机", "中", "重要配套", "需验证人形机器人客户与收入弹性"],
        ["埃斯顿", "002747", "中游", "工业机器人/系统集成", "待核验", "机器人本体、运动控制", "中", "本体侧候选", "中游竞争更拥挤，利润弹性需验证"],
        ["宁德时代", "300750", "相邻", "新能源/储能/工程机械电动化", "非机器人主链", "动力电池与储能系统", "低", "相邻基础设施", "用于验证电动化资本开支，不作为核心卡口"],
    ]
    opportunity_rows = [
        ["核心环节龙头/卡口候选", "机器人量产带动精密传动需求，上游认证和寿命壁垒决定价值捕获", "绿的谐波", "订单/客户认证/收入占比披露；毛利率稳定；价格止跌", "估值过高、公告无法验证订单、替代路线成熟"],
        ["关键技术突破者", "丝杠、机床和精密加工能力决定运动执行部件良率和扩产", "秦川机床", "机器人客户、滚动功能部件订单、收入占比", "仅有概念标签，无法确认产业占比"],
        ["重要配套/高弹性", "伺服、电机、控制环节受益于关节数量和执行单元增多，但竞争更分散", "鸣志电器", "高端电机产品规格、客户认证、毛利率", "技术壁垒和客户粘性弱于减速器"],
        ["相邻基础设施", "工程机械电动化、储能和制造业资本开支提供侧面验证", "宁德时代", "工程机械电动化订单、储能需求", "不是机器人核心部件，不能上升为主线标的"],
    ]

    def latest_financial_summary(symbol: str, item: dict[str, Any]) -> str:
        indicators = item["supplement"].get("financials", {}).get("statements", {}).get("indicators", [])
        row = indicators[0] if indicators else {}
        if row:
            return (
                f"{str(row.get('REPORT_DATE_NAME') or row.get('REPORT_DATE') or '')[:10]}营收{money(row.get('TOTALOPERATEREVE'))}"
                f"，同比{fmt(row.get('TOTALOPERATEREVETZ'))}%；归母净利{money(row.get('PARENTNETPROFIT'))}"
                f"，同比{fmt(row.get('PARENTNETPROFITTZ'))}%"
            )
        return SELECTED_SYMBOLS[symbol]["financial_note"]

    def target_space_text(tech: dict[str, Any]) -> str:
        if tech.get("eps_anchor"):
            return f"EPS锚{fmt(tech.get('eps_anchor'))}；100/140/180x情景价 {fmt(tech.get('target_low'))}/{fmt(tech.get('target_mid'))}/{fmt(tech.get('target_high'))}；压力位 {tech.get('pressure')}"
        return f"缺少一致EPS预测，先看压力位 {tech.get('pressure')} 与60日箱体上沿 {fmt(tech.get('high60'))}"

    trading_rows = []
    for symbol, item in selected.items():
        meta = item["meta"]
        quote = item["quote"]
        tech = item["tech"]
        score = tech.get("institutional_trend_score")
        action = "可跟踪候选" if isinstance(score, (int, float)) and score >= 3.5 else "观察名单，等待结构修复"
        trading_rows.append(
            [
                meta["name"],
                symbol,
                f"{meta['chain_position']}；{meta['chain_thesis']}",
                latest_financial_summary(symbol, item),
                f"现价{fmt(tech.get('price'))}，PE {fmt(quote.get('pe'))}，PB {fmt(quote.get('pb'))}；券商远期PE中位数{fmt(tech.get('sellside_pe_median'))}",
                (
                    f"{tech.get('trend')}；MA5/10/20/60={fmt(tech.get('ma5'))}/{fmt(tech.get('ma10'))}/{fmt(tech.get('ma20'))}/{fmt(tech.get('ma60'))}；"
                    f"20日箱体{fmt(tech.get('low20'))}-{fmt(tech.get('high20'))}，60日箱体{fmt(tech.get('low60'))}-{fmt(tech.get('high60'))}；"
                    f"箱体位置{fmt(tech.get('position60'))}%；{tech.get('volume_state')}；趋势分{fmt(score, 1)}/5"
                ),
                tech.get("buy_zone"),
                f"{tech.get('stop_loss')}；产业证据失效：{meta['evidence_note']}",
                target_space_text(tech),
                action,
            ]
        )

    source_rows = []
    for item in news[:3] + industry_reports[:6] + reports[:4] + announcements[:3]:
        title = item.get("title")
        if not title:
            continue
        source_rows.append([
            title,
            item.get("source") or item.get("org") or item.get("category") or "公开来源",
            item.get("published_at") or item.get("publish_date") or item.get("date") or "",
            "高" if item in announcements else "中-高",
            source_url(item),
        ])

    source_entries = [
        {
            "claim": "绿的谐波最新公告包含股票交易风险提示，是高估值核心候选需要等待证据的关键反证线索",
            "source": "东方财富公告",
            "tool": "filing",
            "status": "ok",
            "confidence": "High",
            "url": announcements[1].get("url") if len(announcements) > 1 else "",
        },
        {
            "claim": "绿的谐波2026Q1营收和归母净利同比高增长",
            "source": "东方财富财务报表接口",
            "tool": "akshare",
            "status": "ok",
            "confidence": "High",
            "url": "",
        },
        {
            "claim": "绿的谐波券商研报给出人形机器人优势持续巩固和EPS预测",
            "source": reports[0].get("org") if reports else "东方财富研报",
            "tool": "web",
            "status": "ok",
            "confidence": "High",
            "url": source_url(reports[0]) if reports else "",
        },
        {
            "claim": "人形机器人进入量产爬坡阶段，核心供应链值得跟踪",
            "source": "华源证券行业研报",
            "tool": "web",
            "status": "ok",
            "confidence": "Medium",
            "url": next((source_url(r) for r in industry_reports if "人形机器人" in str(r.get("title"))), ""),
        },
        {
            "claim": "工程机械销量延续高增，是物理AI相邻设备链的需求验证",
            "source": "华源证券/太平洋行业研报",
            "tool": "web",
            "status": "ok",
            "confidence": "Medium",
            "url": next((source_url(r) for r in industry_reports if "工程机械" in str(r.get("title"))), ""),
        },
        {
            "claim": "企业AI和云端基础设施仍在扩散，提供物理AI长期需求背景",
            "source": "OpenAI/Hugging Face公开资讯",
            "tool": "web",
            "status": "ok",
            "confidence": "Medium",
            "url": source_url(news[0]) if news else "",
        },
        {
            "claim": "绿的谐波当前价格、PE/PB和日内跌幅来自公开行情快照",
            "source": "腾讯行情/东方财富fallback",
            "tool": "akshare",
            "status": "fallback",
            "confidence": "Medium",
            "url": "",
        },
    ]

    selected_price_images = "\n\n".join(
        f"![{item['meta']['name']}技术结构](assets/{price_pngs[symbol].name})" for symbol, item in selected.items() if symbol in price_pngs
    )
    selected_names = "、".join(item["meta"]["name"] for item in selected.values())
    wencai_section = ""
    if wencai_rows:
        wencai_section = "\n\n### 问财增强数据交叉验证\n\n" + md_table(
            ["查询项", "类型", "查询语句", "状态", "返回条数", "样本/字段", "用途"],
            wencai_rows[:18],
        )
    elif wencai_enrichment.get("skipped"):
        wencai_section = "\n\n### 问财增强数据交叉验证\n\n当前运行进程未读取到 IWENCAI_API_KEY，问财增强源未启用；不影响本报告使用公开行情、公告和研报 fallback 数据生成。"

    report = "\n\n".join([
        "# 物理AI/人形机器人核心零部件产业链与A股公司分析报告",
        f"> 分析日期：{REPORT_DATE}  \n> 研究范围：中国A股可映射的物理AI/人形机器人核心零部件链；重点验证上游精密传动卡口和核心标的买点。  \n> 报告性质：产业链深度挖掘 + 股票层面跟踪框架，不构成真实交易建议。",
        "## 0. 核心结论\n\n"
        "1. 本轮不是简单的 AI 主题交易，而是物理 AI 产业链进入订单和估值双重验证期。真正的价值集中在上游精密传动、丝杠、伺服与控制等瓶颈卡口，尤其是能被客户认证、订单、收入占比和毛利率证明的公司。\n"
        "2. 绿的谐波是当前样本里的核心研究标的：它处在机器人精密传动核心环节，2026Q1营收同比 42.96%、归母净利同比 61.17%，但当前 PE 仍高达 524.17，且近期出现股票交易风险提示公告，说明“卡口机会”和“估值安全”正在剧烈拉扯。\n"
        f"3. 核心跟踪标的不应只剩一只。本报告把 {selected_names} 作为三条上游主线分别跟踪：减速器/精密传动、丝杠/机床、伺服电机/控制。排序先看卡口价值和产业证据，再看技术结构是否给出可执行位置。\n"
        "4. 买点不能靠一句“机器人量产”判断，必须同时满足三件事：订单/客户/收入证据补强、估值消化到可解释区间、价格结构从单边下跌转为企稳修复。否则只是主题波动，不是产业链买点，风险收益比不成立。\n"
        "5. 宁德时代、贵州茅台等样本不能被混入主线。宁德时代可作为工程机械电动化和储能资本开支的侧面验证，贵州茅台只能作为市场风险偏好温度计，不能提供物理 AI 产业链证据。",
        "## 1. 研究对象、边界与口径\n\n" + md_table(
            ["项目", "定义"],
            [
                ["分析对象", "物理AI/人形机器人核心零部件，重点是精密传动、丝杠、伺服、电机、控制器和系统集成"],
                ["纳入主线", "减速器、丝杠、伺服电机、控制器、传感器、精密加工与检测设备、人形机器人本体"],
                ["相邻链路", "工程机械电动化、新能源/储能、工业软件、视觉传感、算力基础设施"],
                ["排除/弱相关", "只有AI概念标签、无机器人收入/订单/客户认证披露的公司；消费品和非产业链样本"],
                ["核心指标", "订单/客户认证、收入占比、毛利率、产能利用率、PE/PB、远期EPS、60日价格结构"],
                ["证据层级", "公告/财报/研报PDF/行情K线 > 公开新闻 > 主题标签和逻辑推断"],
            ],
        ),
        "## 2. 行业背景与需求驱动\n\n公开新闻显示企业 AI 和云端基础设施仍在扩散；A股研报端同时出现人形机器人量产、工程机械销量、国产 CPU 提价、IC 封装基板等线索。需求端没有冷却，但股票定价开始要求更硬的兑现证据。"
        "\n\n" + md_table(
            ["驱动", "方向", "影响环节", "传导逻辑", "证据强度"],
            [
                ["企业AI扩散", "正向", "算力/机器人应用", "AI进入企业流程 -> 物理世界自动化需求提升", "中-高"],
                ["人形机器人量产爬坡", "正向", "减速器/丝杠/伺服", "本体放量 -> 运动部件价值量与客户认证重要性上升", "中-高"],
                ["工程机械销量与电动化", "正向但间接", "工程机械/新能源链", "设备电动化和资本开支改善 -> 相邻链路验证", "中"],
                ["高估值样本大跌", "负向/筛选", "核心卡口标的", "估值先于订单透支 -> 市场要求更硬证据", "高"],
            ],
        ),
        "## 3. 产业链全景图谱\n\n![产业链投研拆解图](assets/physical-ai-chain-map.png)\n\n"
        + md_table(
            ["环节", "细分领域", "角色", "关键输入", "关键输出", "价值/成本驱动", "代表A股公司"],
            [
                ["上游核心部件", "减速器、丝杠、伺服、电机、控制器", "决定运动精度、寿命和负载", "精密加工、材料、客户认证", "精密传动/运动控制部件", "认证周期、良率、寿命、订单", "绿的谐波、秦川机床、鸣志电器"],
                ["上游设备/检测", "精密加工与检测设备", "影响良率和扩产速度", "机床、检测、工艺Know-how", "加工/检测能力", "扩产周期、良率爬坡", "华中数控、日发精机待验证"],
                ["中游制造", "机器人本体、系统集成、工程机械", "承接终端需求和场景交付", "核心零部件、软件、工程能力", "机器人/智能设备", "订单、场景复制、成本控制", "埃斯顿、汇川技术"],
                ["下游应用", "工厂、物流、工程施工、服务机器人", "形成最终需求", "ROI、客户预算、场景标准化", "自动化/智能化服务", "订单、销量、客户验证", "非A股或间接映射"],
                ["相邻链路", "新能源、储能、工程机械电动化", "侧面验证制造业资本开支", "电池、电驱、储能", "电动化设备", "销量和资本开支", "宁德时代"],
            ],
        ),
        "## 4. 上游材料、部件与制程要素挖掘\n\n" + md_table(
            ["上游层级", "细分材料/部件", "对目标产业的作用", "价值/稀缺性", "卡脖子程度", "A股候选", "纳入主线判断"],
            [
                ["Product BOM", "减速器/丝杠/伺服电机", "决定运动精度、负载和寿命", "高；客户认证和可靠性要求高", "高", "绿的谐波/秦川机床/鸣志电器", "Core"],
                ["Equipment/tools", "精密加工与检测设备", "影响良率、成本和扩产速度", "中高；良率爬坡慢", "中", "华中数控/日发精机待验证", "Important"],
                ["Adjacent infrastructure", "工业软件/视觉传感/AI模型", "提升泛化和场景复制", "中；技术路线分散", "中", "科大讯飞/虹软科技待验证", "Adjacent"],
                ["Commodity/background", "新能源/储能/工程机械电动化", "验证设备电动化需求，不是机器人核心部件", "中", "低-中", "宁德时代", "Adjacent"],
            ],
        ),
        "## 5. 产业链核心环节价值分布\n\n" + md_table(
            ["产业链环节", "细分领域/关键产品", "BOM成本占比/价值占比", "核心技术壁垒", "卡脖子程度", "代表A股公司", "公司环节地位", "证据口径/备注"],
            value_rows,
        ),
        "## 6. 竞争格局与核心壁垒\n\n" + md_table(
            ["候选环节", "寡头是谁", "扩产周期", "替代方案", "下游刚需", "是否卡口"],
            [
                ["减速器/丝杠", "国内少数精密传动供应商，海外仍有强供应商", "中长；客户认证、寿命测试和良率爬坡耗时", "短期可多供应商验证，但核心客户切换慢", "是，机器人运动执行绕不开", "卡口候选"],
                ["伺服/电机/控制器", "供应商较多但高端产品分化", "中；需要客户和场景适配", "替代较减速器更容易", "是，但壁垒分化", "重要配套"],
                ["本体与系统集成", "竞争者较多", "中；工程交付为主", "替代较多", "是，但利润池可能分散", "普通受益/核心需验证"],
                ["新能源/储能", "龙头集中但不在主链", "长", "与机器人核心部件替代关系弱", "间接", "相邻链路"],
            ],
        ),
        "## 7. A股公司映射与核心地位判断\n\n" + md_table(
            ["公司", "代码", "环节", "细分领域", "产业占比/暴露度", "核心技术/产品", "卡脖子相关性", "环节地位", "证据与备注"],
            company_rows,
        ),
        "## 8. 投资线索、交易跟踪与目标价情景\n\n"
        "### 8.1 机会类型\n\n" + md_table(["机会类型", "产业链逻辑", "代表A股公司", "验证里程碑", "风险"], opportunity_rows)
        + "\n\n### 8.2 核心标的股票层面跟踪\n\n"
        "股票层面的顺序是：先确认公司确实卡在产业链关键环节，再看财务和估值是否能解释预期，最后才用价格结构寻找买点。下表里的买点不是“明天买什么”，而是用于持续跟踪的触发条件：支撑位只代表观察区，必须叠加订单/客户/收入证据；压力位代表兑现或减仓观察位。\n\n"
        + selected_price_images + "\n\n"
        + (f"![绿的谐波营收同比](assets/{finance_png.name})\n\n" if finance_png else "")
        + md_table(
            ["公司", "代码", "产业链结论", "财务质量", "当前估值", "技术面/趋势", "买点区间", "止损/失效条件", "目标价/空间", "综合判断"],
            trading_rows,
        )
        + "\n\n> 说明：目标价情景使用券商研报 EPS 预测的中位数作为粗略锚点，再用 100/140/180 倍 PE 做情景推导。由于样本估值极高，该区间不是买入建议，而是用于判断市场价格是否已经透支远期成长。",
        "## 9. 催化因素与产业传导路径\n\n" + md_table(
            ["催化因素", "方向", "影响环节", "传导路径", "受影响A股公司", "证据强度", "时间维度"],
            [
                ["人形机器人量产爬坡", "正向", "减速器/丝杠/伺服", "本体放量 -> 核心部件订单 -> 收入和毛利验证", "绿的谐波、秦川机床、鸣志电器", "中-高", "中期"],
                ["工程机械销量延续高增", "正向但间接", "工程机械/电动化设备", "销量改善 -> 制造业资本开支 -> 设备智能化需求", "宁德时代、工程机械链", "中", "短中期"],
                ["核心公司风险提示公告", "负向/筛选", "高估值卡口股", "股价波动和估值压力 -> 需要订单证据消化", "绿的谐波", "高", "短期"],
                ["国产CPU/封装基板研报升温", "相邻正向", "算力硬件/封装", "AI基础设施扩散 -> 硬件链关注度提升", "半导体/封装链", "中", "中期"],
            ],
        ),
        "## 10. 风险提示\n\n"
        "1. 机器人量产节奏低于预期，核心零部件订单无法兑现。\n"
        "2. 绿的谐波等高估值标的已经提前反映远期成长，若订单证据不足，估值回撤可能继续。\n"
        "3. 减速器、丝杠、伺服等环节存在替代路线和供应商竞争，卡口价值可能被稀释。\n"
        "4. 公司公告只能证明事件存在，不等于机器人收入占比提升；必须继续核验年报、订单和客户认证。\n"
        "5. 研报标题和主题热度不能代替原始财报、公告和产品收入证据。",
        "## 11. 数据来源、证据强度与待核验事项\n\n" + md_table(
            ["结论/数据", "来源", "日期", "置信度", "链接"],
            source_rows[:14],
        )
        + wencai_section
        + "\n\n待核验事项：\n\n"
        "1. 绿的谐波机器人相关收入占比、客户认证、订单和产能利用率。\n"
        "2. 秦川机床、鸣志电器等配套公司的机器人链直接收入和客户证据。\n"
        "3. 核心部件行业的真实 BOM 价值占比和国产替代率。\n"
        "4. 历史 PE 分位、机构持仓、成交结构和更长周期 K 线趋势。\n"
        "5. 研报 PDF 对收入预测、EPS 假设和风险提示的原文核验。",
    ])

    (OUT / "report.md").write_text(report + "\n", encoding="utf-8")
    source_data = {
        "generated_at": datetime.now().isoformat(),
        "payload_file": "data/raw/latest-full-loop.json",
        "focus_symbol": focus,
        "selected_symbols": list(SELECTED_SYMBOLS),
        "quotes": quotes,
        "selected_quotes": {symbol: item["quote"] for symbol, item in selected.items()},
        "selected_supplements": {symbol: item["supplement"] for symbol, item in selected.items()},
        "technical_structures": {symbol: item["tech"] for symbol, item in selected.items()},
        "selected_supplement": focus_supp,
        "levels": lv,
        "wen_cai_enrichment": wencai_enrichment,
        "wen_cai_summary": wen_cai.summarize_enrichment(wencai_enrichment),
        "source_rows": source_rows,
        "sources": source_entries,
        "assets": [str(p.relative_to(OUT)) for p in ASSETS.iterdir()],
    }
    (OUT / "source_data.json").write_text(json.dumps(source_data, ensure_ascii=False, indent=2), encoding="utf-8")
    quality_proc = subprocess.run(
        [
            sys.executable,
            "skills/industry-chain-analysis/scripts/report_quality.py",
            str(OUT / "report.md"),
            "--output",
            str(OUT / "quality_report.json"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    try:
        quality = json.loads(quality_proc.stdout)
    except Exception:
        quality = {
            "passed": False,
            "stdout": quality_proc.stdout,
            "stderr": quality_proc.stderr,
            "returncode": quality_proc.returncode,
        }
    print(json.dumps({"report": str(OUT / "report.md"), "quality": quality}, ensure_ascii=False, indent=2))
    if not quality.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
