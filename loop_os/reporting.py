from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _role_items(review: dict[str, Any], role: str, limit: int = 4) -> list[str]:
    roles = review.get("roles", {})
    items = roles.get(role, []) if isinstance(roles, dict) else []
    return [str(item) for item in items[:limit]] if isinstance(items, list) else []


def _top_pair(items: list[Any], idx: int = 0, fallback: str = "待观察") -> str:
    if not items:
        return fallback
    try:
        return str(items[0][idx])
    except Exception:
        return fallback


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return str(value)


def _fmt_num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def _fmt_money(value: Any) -> str:
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


def _avg(values: list[float]) -> float | None:
    values = [v for v in values if isinstance(v, (int, float))]
    return sum(values) / len(values) if values else None


def _market_line(payload: dict[str, Any]) -> str:
    quotes = payload.get("a_share_quotes", [])
    charts = payload.get("global_charts", [])
    parts: list[str] = []
    for quote in quotes[:3]:
        parts.append(f"{quote.get('name') or quote.get('symbol')} {_fmt_pct(quote.get('change_pct'))}")
    for chart in charts[:3]:
        parts.append(f"{chart.get('symbol')} {_fmt_pct(chart.get('change_pct'))}")
    return "；".join(parts) if parts else "市场快照不足，先补数据。"


def _primary_theme(industry: dict[str, Any]) -> tuple[str, int]:
    buckets = industry.get("top_theme_buckets", [])
    if buckets:
        return str(buckets[0][0]), int(buckets[0][1])
    return "待确认主线", 0


def _theme_cn(theme: str) -> str:
    mapping = {
        "ai_physical_ai": "AI/物理AI",
        "ai": "AI/物理AI",
        "semiconductor": "半导体",
        "equipment": "高端设备/机器人",
        "new_energy": "新能源",
        "auto": "汽车链",
        "medical": "医药医疗",
    }
    return mapping.get(theme, theme)


def _public_source_summary(payload: dict[str, Any]) -> list[str]:
    news = payload.get("news", {})
    reports = payload.get("industry_reports", [])
    quotes = payload.get("a_share_quotes", [])
    charts = payload.get("global_charts", [])
    news_sources: list[str] = []
    for item in news.get("headlines", []):
        source = item.get("source")
        if source and source not in news_sources:
            news_sources.append(source)
        if len(news_sources) >= 6:
            break
    report_orgs: list[str] = []
    for item in reports:
        org = item.get("org")
        if org and org not in report_orgs:
            report_orgs.append(org)
        if len(report_orgs) >= 6:
            break
    quote_sources = sorted({str(item.get("source")) for item in quotes if item.get("source")})
    chart_sources = sorted({str(item.get("source")) for item in charts if item.get("source")})
    lines = []
    if reports:
        org_text = "、".join(report_orgs) if report_orgs else "多家机构"
        lines.append(f"行业研报：东方财富研报公开接口，本轮读取 {len(reports)} 篇；机构样本包括 {org_text}。")
    if news.get("headlines"):
        lines.append(f"公开资讯：RSS/公开网页源，本轮读取 {len(news.get('headlines', []))} 条；来源样本包括 {'、'.join(news_sources)}。")
    if quotes:
        lines.append(f"A 股行情：公开行情接口，来源包括 {'、'.join(quote_sources)}。")
    if charts:
        lines.append(f"全球市场：公开行情接口，来源包括 {'、'.join(chart_sources)}。")
    return lines or ["本轮公开来源不足，需要补充新闻、研报、公告和行情数据。"]


def _candidate_table(payload: dict[str, Any]) -> list[str]:
    pipeline = payload.get("research_pipeline", {})
    stocks = {item.get("symbol"): item for item in pipeline.get("stock_analyzer", [])} if isinstance(pipeline, dict) else {}
    decisions = pipeline.get("trade_decision_engine", {}).get("decisions", []) if isinstance(pipeline, dict) else []
    if decisions:
        lines = [
            "| 标的 | 决策门禁 | 今日信号 | 估值/技术 | 下一步 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for decision in decisions:
            symbol = decision.get("symbol")
            stock = stocks.get(symbol, {})
            name = decision.get("name") or stock.get("name") or symbol
            valuation = stock.get("valuation", {})
            technical = stock.get("technical", {})
            signal = f"涨跌幅 {_fmt_pct(technical.get('change_pct'))}"
            val_text = f"PE {valuation.get('pe')}，PB {valuation.get('pb')}，估值分 {valuation.get('score')}，技术分 {technical.get('score')}"
            if decision.get("action") == "paper_candidate":
                next_action = "只进入模拟观察，并补公告/研报正文验证收入暴露。"
            elif decision.get("action") == "reject_or_wait":
                next_action = "先作为反证样本，等估值、技术或基本面证据修复。"
            else:
                next_action = "继续观察，补产业链位置和订单证据。"
            lines.append(f"| {name} `{symbol}` | {decision.get('action')}({decision.get('passed_conditions')}/5) | {signal} | {val_text} | {next_action} |")
        return lines

    lines = [
        "| 标的 | 状态 | 今日信号 | 估值/风险 | 下一步 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for quote in payload.get("a_share_quotes", []):
        name = quote.get("name") or quote.get("symbol")
        signal = f"涨跌幅 {_fmt_pct(quote.get('change_pct'))}，价格 {quote.get('price')}"
        valuation = f"PE {quote.get('pe')}，PB {quote.get('pb')}，{quote.get('valuation_band')}"
        if quote.get("valuation_band") == "high":
            status = "反证优先"
            next_action = "先验证订单、毛利率、量产节奏，估值不降不主动升级。"
        elif quote.get("change_pct") is not None and quote.get("change_pct") > 0:
            status = "观察"
            next_action = "补产业暴露和基本面证据。"
        else:
            status = "候选"
            next_action = "等待基本面或资金面确认。"
        lines.append(f"| {name} `{quote.get('symbol')}` | {status} | {signal} | {valuation} | {next_action} |")
    return lines


def _public_item_lines(items: list[dict[str, Any]], limit: int = 8) -> list[str]:
    lines = []
    for item in items[:limit]:
        title = item.get("title")
        source = item.get("source") or "公开来源"
        date = item.get("published_at") or item.get("publish_date") or ""
        url = item.get("url")
        suffix = f" ({url})" if url else ""
        lines.append(f"- {source} {date}：{title}{suffix}")
    return lines


def _simple_md_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def _stock_data_coverage_table(payload: dict[str, Any]) -> list[str]:
    pipeline = payload.get("research_pipeline", {})
    stocks = pipeline.get("stock_analyzer", []) if isinstance(pipeline, dict) else []
    rows = []
    for item in stocks:
        coverage = item.get("a_stock_data_coverage", {})
        rows.append(
            [
                f"{item.get('name')} `{item.get('symbol')}`",
                coverage.get("announcements", 0),
                coverage.get("fund_flow", 0),
                coverage.get("dragon_tiger", 0),
                coverage.get("financial_indicator_periods", 0),
                coverage.get("research_reports", 0),
            ]
        )
    if not rows:
        return ["- 本轮未形成个股补充数据。"]
    return _simple_md_table(["标的", "公告", "资金", "龙虎榜", "财务期数", "研报"], rows)


def _report_pick(reports: list[dict[str, Any]], keywords: list[str], limit: int = 4) -> list[dict[str, Any]]:
    picked = []
    for item in reports:
        text = f"{item.get('title', '')} {item.get('industry_name', '')}"
        if any(keyword in text for keyword in keywords):
            picked.append(item)
        if len(picked) >= limit:
            break
    return picked


def _news_pick(news: dict[str, Any], keywords: list[str], limit: int = 4) -> list[dict[str, Any]]:
    picked = []
    for item in news.get("headlines", []):
        text = f"{item.get('title', '')} {item.get('source', '')}"
        if any(keyword.lower() in text.lower() for keyword in keywords):
            picked.append(item)
        if len(picked) >= limit:
            break
    return picked


def _source_line(item: dict[str, Any]) -> str:
    date = item.get("published_at") or item.get("publish_date") or ""
    if isinstance(date, str) and "T" in date:
        date = date.split("T", 1)[0]
    source = item.get("source") or item.get("org") or "公开来源"
    title = item.get("title") or ""
    url = _source_url(item)
    suffix = f"：{url}" if url else ""
    return f"{source}，{date}，《{title}》{suffix}"


def _source_url(item: dict[str, Any]) -> str:
    for key in ("url", "link", "pdf_url"):
        value = item.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    info_code = item.get("info_code") or item.get("infoCode")
    if not info_code and isinstance(item.get("raw"), dict):
        info_code = item["raw"].get("infoCode")
    if info_code:
        return f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"
    return ""


def _date_cn(date: Any) -> str:
    if not isinstance(date, str) or not date:
        return ""
    if "T" in date:
        date = date.split("T", 1)[0]
    parts = date.split("-")
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        return f"{int(parts[1])}月{int(parts[2])}日"
    return date


def _source_fragment(item: dict[str, Any]) -> str:
    source = item.get("source") or item.get("org") or "公开来源"
    date = _date_cn(item.get("published_at") or item.get("publish_date") or "")
    title = item.get("title") or ""
    date_text = f"{date}" if date else ""
    return f"{source}{date_text}《{title}》"


def _source_sentence(items: list[dict[str, Any]], limit: int = 4) -> str:
    fragments = [_source_fragment(item) for item in items[:limit] if item.get("title")]
    return "；".join(fragments)


def _cn_level(value: Any) -> str:
    text = str(value or "").strip().lower()
    mapping = {
        "high": "高",
        "medium": "中",
        "low": "低",
        "none": "无",
    }
    return mapping.get(text, str(value or "待验证"))


def _stock_snapshot(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    for item in payload.get("research_pipeline", {}).get("stock_analyzer", []):
        if item.get("symbol") == symbol:
            return item
    return {}


def _quote_snapshot(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    for item in payload.get("a_share_quotes", []):
        if item.get("symbol") == symbol:
            return item
    return {}


def _supplement(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    supp = payload.get("stock_supplements", {}).get(symbol, {})
    return supp if isinstance(supp, dict) else {}


def _latest_financial(supp: dict[str, Any]) -> dict[str, Any]:
    statements = supp.get("financials", {}).get("statements", {}) if isinstance(supp.get("financials"), dict) else {}
    indicators = statements.get("indicators", []) if isinstance(statements, dict) else []
    return indicators[0] if indicators else {}


def _forecast_rows(supp: dict[str, Any]) -> list[dict[str, Any]]:
    rows = supp.get("research_reports", {}).get("rows", []) if isinstance(supp.get("research_reports"), dict) else []
    return [row for row in rows if isinstance(row, dict)]


def _median(values: list[float]) -> float | None:
    vals = sorted(v for v in values if isinstance(v, (int, float)))
    if not vals:
        return None
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2


def _buy_sell_levels(quote: dict[str, Any], supp: dict[str, Any]) -> dict[str, Any]:
    history_rows = supp.get("price_history", {}).get("rows", []) if isinstance(supp.get("price_history"), dict) else []
    closes = [float(row["close"]) for row in history_rows if isinstance(row, dict) and isinstance(row.get("close"), (int, float))]
    highs = [float(row["high"]) for row in history_rows[-60:] if isinstance(row, dict) and isinstance(row.get("high"), (int, float))]
    lows = [float(row["low"]) for row in history_rows[-60:] if isinstance(row, dict) and isinstance(row.get("low"), (int, float))]
    price = quote.get("price")
    forecast_rows = _forecast_rows(supp)
    eps_next_two = [
        row.get("eps_forecast", {}).get("next_two_year")
        for row in forecast_rows
        if isinstance(row.get("eps_forecast"), dict)
    ]
    eps_next = [
        row.get("eps_forecast", {}).get("next_year")
        for row in forecast_rows
        if isinstance(row.get("eps_forecast"), dict)
    ]
    eps_anchor = _median([v for v in eps_next_two + eps_next if isinstance(v, (int, float))])
    value_low = eps_anchor * 100 if eps_anchor else None
    value_mid = eps_anchor * 140 if eps_anchor else None
    value_high = eps_anchor * 180 if eps_anchor else None
    ma20 = _avg(closes[-20:])
    ma60 = _avg(closes[-60:])
    recent_high = max(highs) if highs else None
    recent_low = min(lows) if lows else None
    return {
        "price": price,
        "ma20": ma20,
        "ma60": ma60,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "eps_anchor": eps_anchor,
        "value_low": value_low,
        "value_mid": value_mid,
        "value_high": value_high,
        "buy_watch": min(v for v in [ma60, value_high] if v is not None) if any(v is not None for v in [ma60, value_high]) else None,
        "stop_loss": recent_low,
        "take_profit": recent_high,
        "history_rows": history_rows,
    }


def _svg_line_chart(path: Path, title: str, rows: list[dict[str, Any]], *, width: int = 760, height: int = 280) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [row for row in rows if isinstance(row.get("close"), (int, float))]
    if len(data) < 2:
        path.write_text(
            f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\"><text x=\"20\" y=\"40\">历史价格数据不足</text></svg>",
            encoding="utf-8",
        )
        return str(path)
    data = data[-90:]
    closes = [float(row["close"]) for row in data]
    min_v, max_v = min(closes), max(closes)
    span = max(max_v - min_v, 1e-9)
    left, right, top, bottom = 58, 22, 36, 42
    plot_w, plot_h = width - left - right, height - top - bottom
    points = []
    for idx, value in enumerate(closes):
        x = left + idx / max(len(closes) - 1, 1) * plot_w
        y = top + (max_v - value) / span * plot_h
        points.append(f"{x:.1f},{y:.1f}")
    grid = []
    for i in range(5):
        y = top + i * plot_h / 4
        val = max_v - i * span / 4
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        grid.append(f'<text x="10" y="{y+4:.1f}" font-size="12" fill="#4b5563">{val:.1f}</text>')
    start_date = data[0].get("date", "")
    end_date = data[-1].get("date", "")
    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            f'<text x="{left}" y="22" font-size="16" font-weight="700" fill="#111827">{title}</text>',
            *grid,
            f'<polyline fill="none" stroke="#2563eb" stroke-width="2.5" points="{" ".join(points)}"/>',
            f'<text x="{left}" y="{height-14}" font-size="12" fill="#4b5563">{start_date}</text>',
            f'<text x="{width-right-86}" y="{height-14}" font-size="12" fill="#4b5563">{end_date}</text>',
            f'<text x="{width-right-150}" y="22" font-size="12" fill="#111827">最新 {closes[-1]:.2f}</text>',
            "</svg>",
        ]
    )
    path.write_text(svg, encoding="utf-8")
    return str(path)


def _svg_bar_chart(path: Path, title: str, rows: list[tuple[str, float, str]], *, width: int = 760, height: int = 280) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    vals = [abs(v) for _, v, _ in rows if isinstance(v, (int, float))]
    max_v = max(vals) if vals else 1
    left, top, bar_h, gap = 180, 42, 26, 18
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="20" y="24" font-size="16" font-weight="700" fill="#111827">{title}</text>',
    ]
    for idx, (label, value, display) in enumerate(rows[:6]):
        y = top + idx * (bar_h + gap)
        w = max(2, abs(value) / max_v * (width - left - 90))
        color = "#16a34a" if value >= 0 else "#dc2626"
        svg_lines.append(f'<text x="20" y="{y+18}" font-size="12" fill="#374151">{label}</text>')
        svg_lines.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{color}" opacity="0.82"/>')
        svg_lines.append(f'<text x="{left+w+8:.1f}" y="{y+18}" font-size="12" fill="#111827">{display}</text>')
    svg_lines.append("</svg>")
    path.write_text("\n".join(svg_lines), encoding="utf-8")
    return str(path)


def write_human_research_memo(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = payload.get("research_pipeline", {})
    chain = pipeline.get("selected_industry_chain", {}) if isinstance(pipeline, dict) else {}
    news = payload.get("news", {})
    reports = payload.get("industry_reports", [])
    theme = str(chain.get("selected_theme") or "unknown")
    theme_name = _theme_cn(theme)
    chain_map = chain.get("chain_map", {}) if chain else {}
    upstream_materials = chain.get("upstream_material_discovery", []) if chain else []
    value_distribution = chain.get("core_value_distribution", []) if chain else []
    company_mapping = chain.get("company_mapping", []) if chain else []
    ai_news = _news_pick(news, ["OpenAI", "Hugging Face", "AI", "机器人", "模型"], 5)
    compute_reports = _report_pick(reports, ["Intel", "CPU", "封装", "基板", "算力", "半导体", "元件"], 4)
    physical_reports = _report_pick(reports, ["机器人", "工程机械", "装载机", "电机", "机械"], 4)
    focus_stock = _stock_snapshot(payload, "688017")
    focus_valuation = focus_stock.get("valuation", {}) if focus_stock else {}
    focus_technical = focus_stock.get("technical", {}) if focus_stock else {}

    title = "# 物理AI产业链深度：核心矛盾不是需求，而是谁拿到卡口利润"

    lines = [
        title,
        "",
        "本轮公开信息放在一起看，真正值得深挖的不是“AI 又热了”，而是物理 AI 产业链开始进入兑现验证期。",
        "",
        "过去市场愿意为一个宏大的 AI 叙事付钱：模型更强、算力更多、应用更广，所以硬件、设备、材料、机器人都可以被放进同一个篮子里上涨。现在这个交易正在分叉。软件端和企业端继续证明 AI 渗透在发生，但硬件端必须回答一个更具体的问题：需求到底会落到哪一段供应链，谁能把它变成订单、收入和毛利。",
        "",
        "这也是本轮选题最值得看的地方：公开资讯里，OpenAI、Hugging Face、Google Research 等仍在强化企业 AI 和基础设施扩散；A 股研报端则同时出现了国产 CPU 提价、IC 封装基板、工程机械高增、新能源装载机、人形机器人量产爬坡等线索。它们表面上分散，底层其实指向同一件事：AI 交易从“买总量”进入“挑链条”。",
        "",
        "如果把盘面也放进去，分歧会更清楚：绿的谐波作为机器人核心零部件样本出现大幅回撤，而企业 AI、国产算力、先进封装、工程机械电动化的公开信息仍在增多。信息面没有冷，价格却已经开始挑剔。这说明研究重点不该停在“这个行业有没有机会”，而应该进入更深一层：哪一段产业链最稀缺，哪家公司最接近卡口，什么条件下才有买点。",
        "",
        "这篇研报只讨论一个问题：如果要从物理 AI 产业链里找核心标的，应该沿着哪条价值链往上挖？我的答案是，先找上游卡口，再看订单验证，最后才讨论买点。过去有 AI 故事就能获得估值弹性，现在必须回答订单、产能、良率、客户认证和收入占比。",
        "",
        "## 1. 选题依据：为什么深挖物理AI产业链",
        "",
        "我更愿意把这条产业链的研究前提概括成一句话：**AI 仍在扩散，但市场不再无条件奖励所有 AI 暴露，只有能解释清楚产业链位置的环节才值得继续研究。**",
        "",
        "这个判断不是来自单条新闻，而是来自两端信号的叠加。一端是企业 AI 使用和云端基础设施继续推进；另一端是 A 股研报把注意力放到国产 CPU、IC 封装基板、机器人零部件、工程机械销量和人形机器人量产。前者说明需求叙事还没结束，后者说明研究资金正在寻找更窄、更可验证的承接环节。",
        "",
        "所以不能再把 AI 当成一个大主题泛泛研究。真正的问题变成：谁是 AI 扩散过程中绕不过去的物理环节？谁只是概念标签？谁的估值已经先于订单透支？",
        "",
        "## 2. 催化事件：为什么要从主题切到产业链",
        "",
    ]

    if ai_news:
        lines.extend(
            [
                "先看需求端。公开资讯继续证明 AI 正在从模型话题进入企业工作流和基础设施层。",
                f"{_source_sentence(ai_news, 4)}，共同指向一个变化：AI 不再只是模型发布会，而是在企业流程、云端训练和推理基础设施里继续扩散。",
                "",
            ]
        )

    if compute_reports:
        lines.extend(
            [
                "再看硬件和国产替代端。本轮研报里最有解释力的不是泛 AI，而是能落到硬件成本、供应安全和国产替代的细分环节。",
                f"{_source_sentence(compute_reports, 4)}，把注意力从“模型还会不会更强”拉回到 CPU、先进封装、基板、半导体设备和材料这些更硬的约束上。",
                "",
            ]
        )

    if physical_reports:
        lines.extend(
            [
                "同时，物理世界的 AI 和装备链也在给出另一条线索：机器人、工程机械、电动化设备这些方向，不再只是“未来场景”，而开始要求销量、订单和出口数据来验证。",
                f"{_source_sentence(physical_reports, 4)}，说明资金正在把“具身智能”拆成更具体的工程机械销量、核心零部件、量产爬坡和新能源装载机需求。",
                "",
            ]
        )

    lines.extend(
        [
            "把这三组信息合在一起，结论不是所有 AI 硬件都应该上修，而是研究重心正在从“有没有 AI 故事”切到“有没有产业链兑现路径”。换句话说，市场正在重新定价的是确定性，而不是想象空间本身。",
            "",
            "## 3. 产业链全景：从应用热度倒推物理卡口",
            "",
            "这条链可以从下往上看。",
            "",
            f"下游是应用和场景：{'、'.join(chain_map.get('downstream', [])) or '企业 AI、数据中心和工厂场景'}。这一层决定需求是否真实，但通常不直接告诉我们 A 股谁最受益。",
            "",
            f"中游是制造和系统集成：{'、'.join(chain_map.get('midstream', [])) or '本体、封测、设备和系统集成'}。这一层能承接订单，但竞争往往更拥挤，利润率取决于规模和交付能力。",
            "",
            f"上游才是当前更应该深挖的位置：{'、'.join(chain_map.get('upstream', [])) or '材料、设备、核心零部件和工艺'}。如果需求继续扩散，上游会先暴露产能、认证、良率和替代路线问题；如果需求证伪，上游高估值也会最先被杀。",
            "",
            "因此，深度挖掘的重点不是把所有 AI 相关公司列出来，而是先问四个问题：不可替代吗？供给刚性吗？客户认证周期长吗？市场有没有把它当普通受益环节定价？",
            "",
            "## 4. 价值量与卡口：优先挖上游核心部件",
            "",
        ]
    )

    if value_distribution:
        for row in value_distribution[:3]:
            lines.append(
                f"**{row.get('细分领域/关键产品')}** 是当前最值得跟踪的环节之一。"
                f"它的壁垒不是一句“AI 相关”，而是 {row.get('核心技术壁垒')}。"
                f"当前卡口判断为{_cn_level(row.get('卡脖子程度'))}，代表公司包括 {row.get('代表A股公司')}。"
                f"但这里仍有一个关键限制：{row.get('证据口径/备注')}。"
            )
            lines.append("")
    elif upstream_materials:
        for row in upstream_materials[:3]:
            lines.append(
                f"**{row.get('细分材料/部件')}** 值得继续跟踪。它对产业链的作用是{row.get('对目标产业的作用')}，"
                f"稀缺性判断为{row.get('价值/稀缺性')}，卡口判断为{_cn_level(row.get('卡脖子程度'))}，A 股候选包括{row.get('A股候选')}。"
            )
            lines.append("")

    lines.extend(
        [
            "这里最容易犯的错，是把“代表公司”直接等同于“可以买”。这一步必须慢下来：公开研报标题只能说明研究注意力，不能证明收入暴露；行情和估值只能说明市场状态，不能证明产业位置。",
            "",
            "## 5. 核心标的筛选：先找卡口，再看买点",
            "",
            "第一类是**主线卡口候选**。绿的谐波对应机器人核心零部件里的精密传动方向，逻辑上更接近上游卡口。但它当前的市场状态并不友好："
            f"PE {focus_valuation.get('pe')}、PB {focus_valuation.get('pb')}，涨跌幅 { _fmt_pct(focus_technical.get('change_pct')) }。"
            "这不是“热度确认”，反而是一个很好的反证样本：如果订单和收入暴露跟不上，高估值会先变成压力。也就是说，卡口资产不是不能贵，而是贵必须有更硬的兑现线索。",
            "",
            "第二类是**相邻基础设施**。宁德时代这类新能源/储能资产可能受益于工程机械电动化、储能和制造业资本开支，但它不是机器人主链卡口。它可以解释能源和设备电动化，不能直接解释人形机器人零部件弹性。把它混进 AI 机器人核心链，会让判断变钝。",
            "",
            "第三类是**非主线样本**。贵州茅台的行情只能说明市场风险偏好的一部分，不能作为 AI 产业链证据。它可以留在市场温度计里，但不应该出现在主线推演里。",
            "",
            "因此，当前核心标的筛选顺序应该是：先把绿的谐波这类上游卡口候选放在主研究位，再把宁德时代这类相邻基础设施放在辅助验证位，最后把贵州茅台这类非主线样本只作为市场温度计。真正值得升权重的，不是名字里有 AI 的公司，而是能被公开披露验证产业位置的公司。",
            "",
            "## 6. 买点框架：不是问哪天买，而是等什么证据",
            "",
            "产业链研报最后要落到买点，但买点不应该是一个日期，也不应该是临场交易冲动。买点是证据、估值和价格行为同时收敛的区域。",
            "",
            "对绿的谐波这类核心卡口候选，第一类买点是**基本面确认型**：出现订单、客户认证、产能利用率、收入占比或毛利率改善的公开证据，同时估值没有继续透支。这类买点胜率更高，但通常不会买在最低点。",
            "",
            "第二类买点是**杀估值后的修复型**：产业逻辑没有被证伪，但高估值被市场充分消化，价格开始停止单边下跌，成交和资金行为出现修复。这个买点的关键不是跌幅够大，而是反证没有继续扩大。",
            "",
            "第三类买点是**产业催化型**：人形机器人量产、工程机械电动化、先进封装扩产或国产替代事件继续强化，并能明确传导到核心部件需求。这个买点最容易被主题情绪放大，所以必须用订单和收入暴露过滤。",
            "",
            "反过来，如果只有研报热度，没有订单和收入暴露；只有概念关联，没有产业链位置；只有短线反弹，没有估值和基本面修复，那就不是买点，只是波动。",
            "",
            "## 7. 风险与反证：什么时候要放弃这条线",
            "",
            "第一，需求不能落到公告、订单、销量或资本开支。比如工程机械高增、新能源装载机、国产 CPU 提价、IC 封装基板高端化，如果最终都停留在研报标题层面，就不能作为买点依据。",
            "",
            "第二，上游卡口没有价格、产能或客户认证信号。减速器、丝杠、伺服、电机、封装基板、先进封装材料，只有出现供给刚性或客户验证，才有资格从“概念受益”升级成“卡口资产”。",
            "",
            "第三，高估值标的继续被市场惩罚，同时没有公告或订单支撑。如果绿的谐波这类样本继续下跌，且基本面证据没有补上，那说明市场正在拒绝只靠远期叙事定价。",
            "",
            "## 8. 结论",
            "",
            f"本轮结论不是简单看多或看空 {theme_name}，而是把它作为一条产业链做深度挖掘：应用扩散仍在，硬件和设备链也有机会，但研究必须从主题热度下沉到卡口、价值量、订单验证和买点条件。",
            "",
            "这一阶段最重要的能力不是更快地收集新闻，而是把新闻变成产业链判断：哪些信息支持需求扩散，哪些信息挑战收入兑现，哪些公司只是被主题带起来，哪些公司真的站在卡口上。",
            "",
            "所以，后续研究应围绕核心标的买点展开：先验证绿的谐波等上游卡口候选的订单和收入暴露，再观察估值消化和价格修复。没有这些信号，AI 仍然只是主题；有了这些信号，才可能变成可交易的产业链机会。",
            "",
            "## 公开来源",
            "",
        ]
    )

    source_items = []
    source_items.extend(ai_news[:3])
    source_items.extend(compute_reports[:3])
    source_items.extend(physical_reports[:3])
    seen: set[str] = set()
    for item in source_items:
        key = str(item.get("title"))
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {_source_line(item)}。")
    lines.extend(["", "_免责声明：本文仅用于研究和复盘，不构成任何真实交易建议。_"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ops_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    industry = payload.get("industry_analysis", {})
    review = payload.get("agent_review", {})
    news = payload.get("news", {})
    pipeline = payload.get("research_pipeline", {})
    chain = pipeline.get("selected_industry_chain", {}) if isinstance(pipeline, dict) else {}
    lines = [
        "# Research OS Ops Report",
        "",
        f"- Cycle: `{payload.get('cycle')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Started at: `{payload.get('started_at')}`",
        f"- Finished at: `{payload.get('finished_at')}`",
        f"- Agent: `{review.get('agent_provider')}` `{review.get('review_type')}`",
        f"- Evidence cards: `{len(payload.get('evidence_ids', []))}`",
        f"- State transition: `{payload.get('state_transition')}`",
        "",
        "## Inputs",
    ]
    lines.append(f"- A-share quotes: `{len(payload.get('a_share_quotes', []))}`")
    lines.append(f"- Global charts: `{len(payload.get('global_charts', []))}`")
    lines.append(f"- News sources={news.get('source_count')}, headlines={len(news.get('headlines', []))}, errors={len(news.get('errors', []))}")
    lines.append(f"- Industry reports={industry.get('report_count')}, headlines={industry.get('headline_count')}")
    lines.extend(["", "## Capability Chain"])
    lines.append(f"- selected_theme=`{chain.get('selected_theme')}` score=`{chain.get('score')}`")
    lines.append(f"- skills_used=`{pipeline.get('skills_used', []) if isinstance(pipeline, dict) else []}`")
    lines.append(f"- stock_supplements=`{len(payload.get('stock_supplements', {}))}`")
    lines.append(f"- tradingagents_rating=`{payload.get('tradingagents_review', {}).get('portfolio_rating')}`")
    harness = payload.get("harness") if isinstance(payload.get("harness"), dict) else {}
    lines.extend(["", "## Harness"])
    lines.append(f"- status=`{harness.get('status') or 'pending'}`")
    lines.extend(["", "## Submodule Write Check"])
    lines.append(f"- before_dirty={payload.get('submodule_dirty_before')}")
    lines.append(f"- after_dirty={payload.get('submodule_dirty_after')}")
    if payload.get("errors"):
        lines.extend(["", "## Errors"])
        lines.extend(f"- {item}" for item in payload.get("errors", []))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_markdown_report(path: Path, payload: dict[str, Any]) -> None:
    write_human_research_memo(path, payload)
