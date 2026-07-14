from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from providers.open_source import a_stock_data, pdf_text, wen_cai  # noqa: E402

REPORT_DATE = datetime.now().strftime("%Y-%m-%d")
# 方案 A:physical-ai 生成器产出 canonical theme report 的素材。
# 旧路径 reports/industry/physical-ai-chain-analysis-<date> 已废弃(legacy 手工快照)。
# 关键约束:生成器**不整篇覆盖** canonical report.md;它写 cycle draft,
# canonical 正文由 route_cycle_reports 做增量合并,report.md 仅在首轮 seed。
OUT = ROOT / "reports" / "themes" / "physical-ai"
ASSETS = OUT / "assets"
# draft 写在 theme 根目录(与 report.md 同级),使正文里的相对 assets/ 链接在质检时可解析;
# draft 命名 report.cycle-draft-<run_id>-cycle-NNN.md(明确非 canonical),同一天多轮不覆盖;归档到 drafts/。
DRAFTS = OUT / "drafts"


def draft_slug_from_payload(payload_file: Path) -> str:
    """从 cycle 的 payload_file 路径推导唯一草稿 slug。

    full loop 的 payload 落在 runs/<date>/<run_id>/cycle-<NNN>/result.json,
    其中 <run_id> 形如 full-loop-<HHMMSS>,<cycle> 形如 cycle-001。
    因此用 "<run_id>-<cycle>" 作为 slug,同一天多轮 loop 不会互相覆盖草稿。
    路径不符合该布局时(例如手动指定 payload)回退到时间戳,保证唯一。
    """
    try:
        cycle_dir = payload_file.resolve().parent
        cycle = cycle_dir.name          # cycle-001
        run_id = cycle_dir.parent.name  # full-loop-181606
        if cycle.startswith("cycle-") and run_id:
            return f"{run_id}-{cycle}"
        if cycle_dir.parent.name == "themes":
            theme_key = cycle_dir.name
            cycle_dir = cycle_dir.parent.parent
            run_dir = cycle_dir.parent
            if cycle_dir.name.startswith("cycle-") and run_dir.name:
                return f"{run_dir.name}-{cycle_dir.name}-{theme_key}"
    except Exception:  # noqa: BLE001
        pass
    return f"manual-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"


def write_report_outputs(
    report: str,
    payload_file: Path,
    *,
    out_dir: Path = OUT,
    drafts_dir: Path = DRAFTS,
) -> tuple[Path, Path, bool]:
    """方案 A 的写入策略(抽成纯函数以便单测)。

    核心不变量:**绝不整篇覆盖已存在的 canonical report.md**。
    - 每轮把正文写成 cycle draft(theme 根目录,与 report.md 同级,相对 assets/ 链接可解析);
    - 同一份归档到 drafts/<slug>.md 便于回溯;draft 文件名带 run_id + cycle,不会互相覆盖;
    - canonical report.md 仅在不存在时 seed,已存在则原样保留,交给 route_cycle_reports 增量合并。

    返回 (canonical_path, draft_path, seeded_canonical)。
    """
    slug = draft_slug_from_payload(payload_file)
    body = report + "\n"

    out_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir.mkdir(parents=True, exist_ok=True)

    draft_path = out_dir / f"report.cycle-draft-{slug}.md"
    draft_path.write_text(body, encoding="utf-8")
    (drafts_dir / f"{slug}.md").write_text(body, encoding="utf-8")

    canonical_path = out_dir / "report.md"
    seeded_canonical = False
    if not canonical_path.exists():
        canonical_path.write_text(body, encoding="utf-8")
        seeded_canonical = True
    return canonical_path, draft_path, seeded_canonical


SELECTED_SYMBOLS: dict[str, dict[str, str]] = {
    "688017": {
        "name": "绿的谐波",
        "chain_position": "减速器/精密传动",
        "chain_thesis": "谐波减速器主研究位；若人形机器人订单兑现，卡口属性最直接",
        "financial_note": "核心看机器人相关订单、客户认证、毛利率和产能利用率",
        "evidence_note": "已有财报高增长和研报覆盖，但订单/收入占比仍需公告验证",
    },
    "002472": {
        "name": "双环传动",
        "chain_position": "精密齿轮/传动系统",
        "chain_thesis": "传动齿轮与减速器产业化能力较强，是精密传动国产替代的重要对照样本",
        "financial_note": "核心看机器人减速器/传动件客户验证、传统汽车齿轮主业韧性和毛利率",
        "evidence_note": "机器人链弹性需用订单、客户和产品收入占比继续验证",
    },
    "002896": {
        "name": "中大力德",
        "chain_position": "减速器/电机/驱动一体化",
        "chain_thesis": "小型减速电机和精密减速器具备机器人执行单元映射，弹性高但波动也大",
        "financial_note": "核心看精密减速器、驱动器和机器人客户认证带来的收入弹性",
        "evidence_note": "高弹性配套候选，需防止主题估值先行而基本面兑现不足",
    },
    "000837": {
        "name": "秦川机床",
        "chain_position": "丝杠/机床/精密加工",
        "chain_thesis": "丝杠和精密机床是运动执行链的重要配套，弹性取决于机器人业务直接暴露",
        "financial_note": "核心看滚动功能部件、机床订单和机器人链客户验证",
        "evidence_note": "保留为关键技术突破者，需继续核验收入占比和客户名单",
    },
    "300580": {
        "name": "贝斯特",
        "chain_position": "滚珠丝杠/精密零部件",
        "chain_thesis": "丝杠和精密零部件是人形机器人线性执行器的重要观察方向，估值弹性来自产能和客户",
        "financial_note": "核心看丝杠产品进展、客户送样/验证、汽车零部件主业现金流",
        "evidence_note": "丝杠方向候选，需核验机器人业务收入确认节奏",
    },
    "603667": {
        "name": "五洲新春",
        "chain_position": "丝杠/轴承/线性执行器配套",
        "chain_thesis": "轴承、丝杠及线性执行器配套具备物理AI关节和执行器映射",
        "financial_note": "核心看丝杠/轴承产品在机器人客户的认证进度和放量节奏",
        "evidence_note": "属于高弹性配套链，需用客户、订单和毛利率排除概念化风险",
    },
    "603728": {
        "name": "鸣志电器",
        "chain_position": "电机/控制",
        "chain_thesis": "电机与运动控制是机器人执行单元的重要环节，壁垒低于减速器但应用广",
        "financial_note": "核心看高端电机/控制产品放量、毛利率和海外/机器人客户",
        "evidence_note": "保留为重要配套，需验证人形机器人订单和收入弹性",
    },
    "300124": {
        "name": "汇川技术",
        "chain_position": "伺服/控制器/工业自动化",
        "chain_thesis": "国内工业自动化龙头，机器人链受益来自伺服、控制和制造业自动化资本开支",
        "financial_note": "核心看通用自动化订单、伺服份额、机器人客户和利润率",
        "evidence_note": "基本面质量较强，但机器人链弹性可能被大体量主业摊薄",
    },
    "002979": {
        "name": "雷赛智能",
        "chain_position": "运动控制/伺服系统",
        "chain_thesis": "运动控制和伺服系统是执行层基础能力，受益于机器人关节和自动化设备扩散",
        "financial_note": "核心看伺服、控制器产品放量及机器人/自动化客户结构",
        "evidence_note": "运动控制受益明确，但竞争格局比减速器更分散",
    },
    "688320": {
        "name": "禾川科技",
        "chain_position": "伺服系统/控制",
        "chain_thesis": "国产伺服系统候选，机器人和自动化链需求改善时具备弹性",
        "financial_note": "核心看营收修复、毛利率和高端客户认证",
        "evidence_note": "基本面修复尚需验证，亏损或低利润阶段需更严格看订单",
    },
}


PHYSICAL_AI_BLUEPRINT: list[dict[str, Any]] = [
    {
        "node": "减速器/精密传动",
        "companies": ["绿的谐波", "双环传动", "中大力德"],
        "logic": "决定关节运动精度、寿命和负载，是人形机器人从样机走向量产最需要验证的卡口。",
        "risk": "订单和客户认证不足、谐波/行星/滚柱丝杠路线切换、扩产后价格压力。",
    },
    {
        "node": "丝杠/线性执行器",
        "companies": ["秦川机床", "贝斯特", "五洲新春"],
        "logic": "线性执行器对应腿部、手臂等运动单元，丝杠良率、寿命和一致性决定量产天花板。",
        "risk": "送样不等于量产，机器人收入占比披露不足会削弱估值支撑。",
    },
    {
        "node": "伺服/运动控制",
        "companies": ["鸣志电器", "汇川技术", "雷赛智能"],
        "logic": "控制响应、伺服精度和关节协同决定机器人运动能力，应用广但竞争也更分散。",
        "risk": "壁垒低于核心传动，价格竞争和主业周期会稀释机器人弹性。",
    },
    {
        "node": "本体/系统集成",
        "companies": ["埃斯顿", "汇川技术", "机器人"],
        "logic": "承接终端场景和工程交付，能验证下游需求，但利润池可能被集成成本吞噬。",
        "risk": "本体环节竞争者多，若缺少核心零部件自供和规模化订单，估值弹性有限。",
    },
    {
        "node": "精密加工/检测设备",
        "companies": ["华中数控", "华辰装备", "日发精机"],
        "logic": "影响丝杠、减速器等核心部件良率和扩产速度，是上游卡口的设备底座。",
        "risk": "需要确认机器人链订单而不是传统机床周期反弹。",
    },
]

PHYSICAL_AI_ABSOLUTE_CORE = {"688017", "002472", "300124"}
PHYSICAL_AI_HIGH_BETA = {"000837", "300580", "603667", "603728", "002896", "002979", "688320"}

HARD_FACT_KEYWORDS = {
    "订单/客户": ("订单", "中标", "定点", "客户", "认证", "供应", "交付", "送样", "量产"),
    "收入占比/财务": ("营收", "净利", "毛利率", "收入占比", "同比", "EPS", "预测PE"),
    "价格/涨价": ("涨价", "提价", "价格", "报价", "ASP"),
    "产能/扩产": ("产能", "扩产", "投产", "满产", "利用率", "锁定", "爬坡"),
    "良率/寿命": ("良率", "寿命", "精度", "测试", "验证", "可靠性", "一致性"),
}

HARD_FACT_NUM_RE = re.compile(
    r"(\d{4}[-年]\d{1,2}[-月]?\d{0,2}日?|20\d{2}Q[1-4]|\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s*(?:亿|万|元|倍|台|套))"
)

PHYSICAL_AI_PDF_INCLUDE_TERMS = ("人形机器人", "机器人", "减速器", "丝杠", "伺服", "执行器", "精密传动", "电机", "运动控制")


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


def fact_category(text: str) -> str | None:
    for category, keywords in HARD_FACT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return None


def fact_strength(kind: str) -> str:
    return {
        "announcement": "公告级/High",
        "financial": "财报级/High",
        "research_report": "研报级/Medium",
        "pdf_body": "PDF正文级/Medium-High",
        "industry_report": "标题级/Medium-Low",
        "news": "新闻级/Low",
    }.get(kind, "线索级/Low")


def fact_numbers(text: str) -> str:
    matches = HARD_FACT_NUM_RE.findall(text)
    return "、".join(dict.fromkeys(matches[:5])) or "未披露明确数值/日期"


def physical_fact_node(text: str) -> str:
    mapping = (
        ("减速器/精密传动", ("减速器", "谐波", "行星", "传动", "齿轮")),
        ("丝杠/线性执行器", ("丝杠", "线性执行器", "轴承", "滚珠", "滚柱")),
        ("伺服/运动控制", ("伺服", "控制器", "运动控制", "电机", "步进")),
        ("本体/系统集成", ("本体", "系统集成", "机器人整机")),
        ("精密加工/检测设备", ("机床", "磨床", "加工", "检测", "数控")),
    )
    for node, keywords in mapping:
        if any(keyword in text for keyword in keywords):
            return node
    return "跨节点/待定位"


def physical_fact_company(text: str, selected: dict[str, dict[str, Any]]) -> str:
    hits = [item["meta"]["name"] for item in selected.values() if item["meta"]["name"] in text]
    if hits:
        return "、".join(dict.fromkeys(hits[:4]))
    for node in PHYSICAL_AI_BLUEPRINT:
        hits.extend([name for name in node["companies"] if name in text])
    return "、".join(dict.fromkeys(hits[:4])) or "未指向单一A股公司"


def add_physical_fact(
    rows: list[dict[str, Any]],
    *,
    kind: str,
    text: Any,
    source: Any,
    date: Any,
    selected: dict[str, dict[str, Any]],
) -> None:
    fact = " ".join(str(text or "").split())
    if not fact:
        return
    if kind == "announcement" and any(term in fact for term in ("股权激励", "权益分派", "法律意见书", "回购价格", "授予价格", "行权价格")):
        return
    category = fact_category(fact)
    if not category:
        return
    rows.append(
        {
            "category": category,
            "fact": fact,
            "node": physical_fact_node(fact),
            "company": physical_fact_company(fact, selected),
            "numbers": fact_numbers(fact),
            "source": compact(source or kind, 28),
            "date": date or "",
            "strength": fact_strength(kind),
        }
    )


def physical_hard_fact_rows(
    payload: dict[str, Any],
    selected: dict[str, dict[str, Any]],
    industry_reports: list[dict[str, Any]],
    news: list[dict[str, Any]],
    *,
    pdf_text_live: bool = False,
) -> list[list[Any]]:
    items: list[dict[str, Any]] = []
    for report in industry_reports:
        if isinstance(report, dict):
            add_physical_fact(
                items,
                kind="industry_report",
                text=report.get("title"),
                source=report.get("org"),
                date=report.get("publish_date") or report.get("date"),
                selected=selected,
            )
    for fact in pdf_text.enrich_pdf_facts(
        [r for r in industry_reports if isinstance(r, dict)],
        live=pdf_text_live,
        max_docs=6,
        snippets_per_doc=3,
        include_terms=PHYSICAL_AI_PDF_INCLUDE_TERMS,
    ):
        if fact.get("snippet"):
            add_physical_fact(
                items,
                kind="pdf_body",
                text=f"{fact.get('title')}：{fact.get('snippet')}",
                source=f"{fact.get('source')} PDF正文",
                date=fact.get("date"),
                selected=selected,
            )
    for headline in news:
        if isinstance(headline, dict):
            add_physical_fact(
                items,
                kind="news",
                text=headline.get("title"),
                source=headline.get("source"),
                date=headline.get("published_at"),
                selected=selected,
            )
    for symbol, item in selected.items():
        name = item["meta"]["name"]
        supp = item["supplement"]
        announcements = supp.get("announcements", {}) if isinstance(supp, dict) else {}
        for row in (announcements.get("rows", []) if isinstance(announcements, dict) else [])[:6]:
            if isinstance(row, dict):
                add_physical_fact(items, kind="announcement", text=f"{name}：{row.get('title')}", source=row.get("source") or "公告", date=row.get("date"), selected=selected)
        reports = supp.get("research_reports", {}) if isinstance(supp, dict) else {}
        report_rows = reports.get("rows", []) if isinstance(reports, dict) else []
        for fact in pdf_text.enrich_pdf_facts([r for r in report_rows if isinstance(r, dict)], live=pdf_text_live, max_docs=3, snippets_per_doc=2):
            if fact.get("snippet"):
                add_physical_fact(
                    items,
                    kind="pdf_body",
                    text=f"{name}：{fact.get('snippet')}",
                    source=f"{fact.get('source')} PDF正文",
                    date=fact.get("date"),
                    selected=selected,
                )
        for row in report_rows[:5]:
            if isinstance(row, dict):
                add_physical_fact(
                    items,
                    kind="research_report",
                    text=f"{name}：{row.get('title')}；预测PE{row.get('pe_forecast') if isinstance(row.get('pe_forecast'), dict) else ''}；EPS{row.get('eps_forecast') if isinstance(row.get('eps_forecast'), dict) else ''}",
                    source=row.get("org") or "券商研报",
                    date=row.get("publish_date"),
                    selected=selected,
                )
        indicators = supp.get("financials", {}).get("statements", {}).get("indicators", []) if isinstance(supp.get("financials"), dict) else []
        if indicators and isinstance(indicators[0], dict):
            row = indicators[0]
            add_physical_fact(
                items,
                kind="financial",
                text=(
                    f"{name}：{row.get('REPORT_DATE_NAME') or row.get('REPORT_DATE')} "
                    f"营收同比{fmt(row.get('TOTALOPERATEREVETZ'))}%，"
                    f"归母净利同比{fmt(row.get('PARENTNETPROFITTZ'))}%，"
                    f"毛利率{fmt(row.get('XSMLL'))}%"
                ),
                source="公开财务接口",
                date=row.get("REPORT_DATE_NAME") or row.get("REPORT_DATE"),
                selected=selected,
            )
    strength_order = {
        "公告级/High": 0,
        "财报级/High": 1,
        "PDF正文级/Medium-High": 2,
        "研报级/Medium": 3,
        "标题级/Medium-Low": 4,
        "新闻级/Low": 5,
    }
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in sorted(items, key=lambda x: strength_order.get(str(x.get("strength")), 9)):
        key = str(item["fact"])[:90]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    rows: list[list[Any]] = []
    for item in deduped[:18]:
        implication = {
            "订单/客户": "可提升机器人链收入兑现置信度；必须继续核验客户名称和金额",
            "价格/涨价": "若伴随订单和良率，说明卡口具备定价权",
            "产能/扩产": "决定量产爬坡节奏，也可能带来供给释放反证",
            "良率/寿命": "最接近人形机器人核心部件瓶颈，优先级高",
            "收入占比/财务": "证明公司质量，但还需拆分机器人相关收入",
        }.get(str(item["category"]), "只作为观察线索")
        rows.append([item["category"], compact(item["fact"], 88), item["node"], item["company"], item["numbers"], f"{item['source']} / {item['date']}", item["strength"], implication])
    return rows or [["证据缺口", "本轮未取得机器人订单、客户认证、产能利用率、良率或收入占比的公告级证据", "全链路", "未指向", "无", "full-loop", "Low", "不升级为买入结论，下一轮优先补证"]]


def physical_evidence_density_rows(fact_rows: list[list[Any]]) -> list[list[Any]]:
    high = sum(1 for row in fact_rows if "High" in str(row[6]))
    medium = sum(1 for row in fact_rows if "Medium" in str(row[6]))
    low = sum(1 for row in fact_rows if "Low" in str(row[6]))
    categories = {str(row[0]) for row in fact_rows if str(row[0]) != "证据缺口"}
    nodes = {str(row[2]) for row in fact_rows if str(row[2]) != "跨节点/待定位"}
    score = min(100, high * 18 + medium * 10 + low * 3 + len(categories) * 7 + len(nodes) * 5)
    conclusion = "可接近标杆文硬事实密度" if score >= 75 and high >= 3 else "结构已成型但硬事实不足" if score >= 45 else "仍以框架和线索为主"
    return [
        ["公告/财报级硬证据", high, "订单、客户、财报、风险提示", "高证据越多，越能进入交易结论"],
        ["研报/标题级中等证据", medium, "券商研报、行业研报标题", "形成假设，不能单独确认龙头"],
        ["新闻/线索级证据", low, "资讯标题和主题热度", "只进入观察池"],
        ["覆盖瓶颈节点", len(nodes), "减速器/丝杠/伺服/本体/设备", "节点越全，产业链图越像瓶颈图"],
        ["证据密度评分", score, conclusion, "低于75分时不宣称已经对标"],
    ]


def physical_fact_summary_bullets(fact_rows: list[list[Any]], *, limit: int = 6) -> str:
    priority = {"订单/客户": 0, "产能/扩产": 1, "良率/寿命": 2, "价格/涨价": 3, "收入占比/财务": 4}
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


def svg_to_png(svg: Path) -> Path:
    png = svg.with_suffix(".png")
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", str(svg), "-o", str(png)], check=True)
        return png
    try:
        import cairosvg  # type: ignore

        cairosvg.svg2png(url=str(svg), write_to=str(png))
        return png
    except Exception:
        pass
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1200, 800), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 1176, 776), outline=(37, 99, 235), width=4)
    draw.text((60, 60), "SVG asset generated; PNG rasterizer unavailable.", fill=(17, 24, 39))
    draw.text((60, 110), f"See sibling SVG: {svg.name}", fill=(55, 65, 81))
    image.save(png)
    return png


def is_placeholder_png(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        from PIL import Image

        image = Image.open(path).convert("RGB").resize((240, 160))
        pixels = list(image.getdata())
        nonwhite = sum(1 for r, g, b in pixels if not (r > 248 and g > 248 and b > 248))
        unique = len(set(pixels))
        return nonwhite / max(len(pixels), 1) < 0.06 or unique < 32
    except Exception:
        return True


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


def _draw_wrapped(draw: Any, xy: tuple[int, int], text: str, font: Any, fill: str, max_width: int, line_gap: int = 6, max_lines: int = 3) -> int:
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
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    for idx, line in enumerate(lines):
        if idx == max_lines - 1 and len("".join(lines)) < len(text):
            line = line[:-1] + "…" if line else "…"
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def write_chain_png(path: Path) -> None:
    from PIL import Image, ImageDraw

    width, height = 1600, 1350
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(34, bold=True)
    h_font = _font(24, bold=True)
    body_font = _font(19)
    small_font = _font(16)
    draw.text((54, 42), "物理AI/人形机器人产业链：卡口节点与核心三公司", font=title_font, fill="#111827")
    draw.text((54, 92), "从量产爬坡 -> 核心部件卡口 -> 公司证据 -> K线执行，避免只买主题标签。", font=body_font, fill="#475569")

    top_cards = [
        ("需求触发", "具身智能从演示走向量产"),
        ("瓶颈筛选", "减速器 / 丝杠 / 伺服"),
        ("证据约束", "订单 / 客户 / 良率 / 收入占比"),
        ("交易纪律", "支撑压力 + 反证退出"),
    ]
    colors = ["#dbeafe", "#dcfce7", "#ffedd5", "#f3e8ff"]
    for idx, (title, desc) in enumerate(top_cards):
        x = 60 + idx * 380
        draw.rounded_rectangle((x, 145, x + 330, 255), radius=18, fill=colors[idx], outline="#94a3b8", width=2)
        draw.text((x + 24, 174), title, font=h_font, fill="#0f172a")
        _draw_wrapped(draw, (x + 24, 212), desc, small_font, "#334155", 280, max_lines=2)

    y = 330
    node_colors = ["#eff6ff", "#ecfdf5", "#fff7ed", "#f5f3ff", "#fdf2f8"]
    outlines = ["#2563eb", "#16a34a", "#ea580c", "#7c3aed", "#db2777"]
    for idx, node in enumerate(PHYSICAL_AI_BLUEPRINT):
        draw.rounded_rectangle((90, y, 1510, y + 150), radius=18, fill=node_colors[idx % len(node_colors)], outline=outlines[idx % len(outlines)], width=3)
        draw.text((125, y + 22), f"{idx + 1}. {node['node']}", font=h_font, fill="#111827")
        draw.text((125, y + 62), "核心三公司：" + " / ".join(node["companies"]), font=body_font, fill="#0f172a")
        _draw_wrapped(draw, (125, y + 95), "逻辑：" + node["logic"], small_font, "#334155", 980, max_lines=2)
        _draw_wrapped(draw, (1060, y + 95), "反证：" + node["risk"], small_font, "#991b1b", 410, max_lines=2)
        y += 185
    draw.rounded_rectangle((130, 1260, 1470, 1325), radius=16, fill="#fff1f2", outline="#e11d48", width=2)
    draw.text((160, 1280), "退出条件：无订单/客户认证/收入占比证据，或扩产过快压低毛利，或关键支撑位破位。", font=body_font, fill="#7f1d1d")
    image.save(path)


def write_bar_png(path: Path, rows: list[tuple[str, float, str]], title: str) -> None:
    from PIL import Image, ImageDraw

    width, height = 1200, 720
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(28, bold=True)
    body_font = _font(18)
    draw.text((45, 35), title, font=title_font, fill="#111827")
    if not rows:
        draw.text((60, 120), "无可用财务序列", font=body_font, fill="#64748b")
        image.save(path)
        return
    max_v = max(abs(v) for _, v, _ in rows) or 1
    zero_x = 320
    chart_w = 760
    for idx, (label, value, display) in enumerate(rows[:8]):
        y = 95 + idx * 68
        draw.text((45, y + 8), label, font=body_font, fill="#334155")
        bar_w = max(4, int(abs(value) / max_v * chart_w))
        color = "#dc2626" if value >= 0 else "#16a34a"
        x0 = zero_x if value >= 0 else zero_x - bar_w
        draw.rounded_rectangle((x0, y, x0 + bar_w, y + 34), radius=6, fill=color)
        draw.text((x0 + bar_w + 12 if value >= 0 else x0 - 170, y + 6), display, font=body_font, fill="#111827")
    draw.line((zero_x, 80, zero_x, 660), fill="#94a3b8", width=2)
    image.save(path)


def write_evidence_density_png(path: Path, rows: list[list[Any]]) -> None:
    from PIL import Image, ImageDraw

    width, height = 1300, 720
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(30, bold=True)
    body_font = _font(18)
    small_font = _font(15)
    draw.text((46, 34), "物理AI证据密度：硬事实是否足够支撑交易升级", font=title_font, fill="#111827")
    draw.text((46, 82), "证据密度用于约束结论强度；缺少订单、客户认证或收入占比时，只能观察等待。", font=body_font, fill="#475569")
    palette = ["#dbeafe", "#dcfce7", "#ffedd5", "#fef3c7", "#f3e8ff", "#e0f2fe"]
    outline = ["#2563eb", "#16a34a", "#ea580c", "#ca8a04", "#7c3aed", "#0284c7"]
    for idx, row in enumerate(rows[:6]):
        x = 60 + (idx % 3) * 405
        y = 145 + (idx // 3) * 230
        draw.rounded_rectangle((x, y, x + 360, y + 175), radius=16, fill=palette[idx % len(palette)], outline=outline[idx % len(outline)], width=2)
        draw.text((x + 22, y + 22), compact(row[0], 16), font=body_font, fill="#0f172a")
        draw.text((x + 22, y + 62), str(row[1]), font=title_font, fill="#111827")
        _draw_wrapped(draw, (x + 22, y + 112), str(row[3]), small_font, "#334155", 310, max_lines=2)
    draw.rounded_rectangle((70, 620, 1230, 675), radius=12, fill="#fff1f2", outline="#e11d48", width=2)
    draw.text((96, 637), "交易含义：证据密度不足时，不用K线制造买点；证据和价格结构同时达标才升级为买入候选。", font=body_font, fill="#7f1d1d")
    image.save(path)


def write_stock_valuation_png(path: Path, selected: dict[str, dict[str, Any]]) -> None:
    from PIL import Image, ImageDraw

    rows: list[tuple[str, str, float | None, float | None, float | None]] = []
    for symbol, item in selected.items():
        quote = item.get("quote", {}) if isinstance(item.get("quote"), dict) else {}
        tech = item.get("tech", {}) if isinstance(item.get("tech"), dict) else {}
        pe = quote.get("pe")
        pb = quote.get("pb")
        rr = tech.get("risk_reward")
        rows.append((
            str(item.get("meta", {}).get("name") or symbol),
            symbol,
            float(pe) if isinstance(pe, (int, float)) else None,
            float(pb) if isinstance(pb, (int, float)) else None,
            float(rr) if isinstance(rr, (int, float)) else None,
        ))
    rows.sort(key=lambda row: (row[2] is None, row[2] if row[2] is not None else 9999))

    width, height = 1500, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(30, bold=True)
    body_font = _font(17)
    small_font = _font(14)
    draw.text((50, 36), "物理AI核心标的估值与赔率对比", font=title_font, fill="#111827")
    draw.text((50, 82), "PE/PB来自行情或补充数据；风险收益比不足时，即使是龙头也只保留观察，不展开K线买点。", font=body_font, fill="#475569")
    usable_pe = [pe for _, _, pe, _, _ in rows if pe is not None and pe > 0]
    max_pe = max(usable_pe or [1])
    max_pe = max(max_pe, 1.0)
    for idx, (name, symbol, pe, pb, rr) in enumerate(rows[:10]):
        y = 135 + idx * 70
        pe_for_bar = min(pe or 0, max_pe)
        bar_w = 80 + pe_for_bar / max_pe * 760 if pe and pe > 0 else 130
        if pe is None or pe <= 0:
            color = "#64748b"
        elif pe >= 180:
            color = "#dc2626"
        elif pe >= 80:
            color = "#ea580c"
        else:
            color = "#059669"
        draw.text((54, y + 16), compact(name, 12), font=body_font, fill="#111827")
        draw.text((54, y + 42), symbol, font=small_font, fill="#64748b")
        draw.rounded_rectangle((220, y, 220 + bar_w, y + 34), radius=7, fill=color)
        pe_text = f"PE {pe:.1f}" if pe is not None else "PE 待验证"
        pb_text = f"PB {pb:.1f}" if pb is not None else "PB 待验证"
        rr_text = f"RR {rr:.2f}" if rr is not None else "RR 待验证"
        draw.text((235 + bar_w, y + 7), f"{pe_text} / {pb_text} / {rr_text}", font=body_font, fill="#111827")
        discipline = "可进入买入候选复核" if rr is not None and rr >= 1.6 and pe is not None and pe < 120 else "等待买入触发"
        draw.text((220, y + 42), discipline, font=small_font, fill="#15803d" if "复核" in discipline else "#b45309")
    image.save(path)


def write_candlestick_png(path: Path, rows: list[dict[str, Any]], title: str, tech: dict[str, Any] | None = None) -> None:
    from PIL import Image, ImageDraw

    clean = [
        r for r in rows[-90:]
        if isinstance(r.get("open"), (int, float))
        and isinstance(r.get("close"), (int, float))
        and isinstance(r.get("high"), (int, float))
        and isinstance(r.get("low"), (int, float))
    ]
    width, height = 1400, 820
    left, right, top, bottom = 90, 70, 85, 90
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(28, bold=True)
    body_font = _font(16)
    small_font = _font(14)
    draw.text((left, 34), title + " · 90日K线", font=title_font, fill="#111827")
    if len(clean) < 2:
        draw.text((left, 130), "历史K线数据不足", font=body_font, fill="#64748b")
        image.save(path)
        return

    highs = [float(r["high"]) for r in clean]
    lows = [float(r["low"]) for r in clean]
    closes = [float(r["close"]) for r in clean]
    marker_values: list[float] = []
    if tech:
        for key in ("support1", "support2", "resistance1", "resistance2"):
            if isinstance(tech.get(key), (int, float)):
                marker_values.append(float(tech[key]))
    min_v = min(lows + marker_values)
    max_v = max(highs + marker_values)
    span = max(max_v - min_v, 1e-9)
    chart_h = height - top - bottom
    chart_w = width - left - right

    def y_of(v: float) -> float:
        return top + (max_v - v) / span * chart_h

    for i in range(6):
        y = top + i * chart_h / 5
        val = max_v - i * span / 5
        draw.line((left, y, width - right, y), fill="#e5e7eb", width=1)
        draw.text((18, y - 9), f"{val:.2f}", font=small_font, fill="#64748b")
    candle_gap = chart_w / max(len(clean), 1)
    candle_w = max(4, min(12, candle_gap * 0.58))
    for idx, row in enumerate(clean):
        o, c, h, l = float(row["open"]), float(row["close"]), float(row["high"]), float(row["low"])
        x = left + idx * candle_gap + candle_gap / 2
        color = "#dc2626" if c >= o else "#16a34a"
        draw.line((x, y_of(h), x, y_of(l)), fill=color, width=2)
        y0, y1 = y_of(max(o, c)), y_of(min(o, c))
        if abs(y1 - y0) < 2:
            draw.line((x - candle_w / 2, y0, x + candle_w / 2, y0), fill=color, width=3)
        else:
            draw.rectangle((x - candle_w / 2, y0, x + candle_w / 2, y1), outline=color, fill="#fee2e2" if c >= o else "#dcfce7")

    def ma(window: int) -> list[float | None]:
        out: list[float | None] = []
        for idx in range(len(closes)):
            if idx + 1 < window:
                out.append(None)
            else:
                part = closes[idx + 1 - window : idx + 1]
                out.append(sum(part) / window)
        return out

    for label, series, color in (("MA20", ma(20), "#f59e0b"), ("MA60", ma(60), "#7c3aed")):
        pts = []
        for idx, value in enumerate(series):
            if value is None:
                continue
            x = left + idx * candle_gap + candle_gap / 2
            pts.append((x, y_of(value)))
        if len(pts) >= 2:
            draw.line(pts, fill=color, width=3)
        draw.text((left + (0 if label == "MA20" else 86), height - 42), label, font=body_font, fill=color)

    if tech:
        for label, key, color in (
            ("S1", "support1", "#15803d"),
            ("S2", "support2", "#166534"),
            ("R1", "resistance1", "#b91c1c"),
            ("R2", "resistance2", "#7f1d1d"),
        ):
            value = tech.get(key)
            if isinstance(value, (int, float)):
                y = y_of(float(value))
                draw.line((left, y, width - right, y), fill=color, width=2)
                for x in range(left, width - right, 18):
                    draw.line((x, y, x + 8, y), fill=color, width=2)
                draw.text((width - right - 110, y - 20), f"{label} {float(value):.2f}", font=small_font, fill=color)

    draw.text((left, height - 70), str(clean[0].get("date", "")), font=small_font, fill="#475569")
    draw.text((width - right - 90, height - 70), str(clean[-1].get("date", "")), font=small_font, fill="#475569")
    draw.text((width - right - 250, 40), f"最新 {closes[-1]:.2f}", font=body_font, fill="#111827")
    draw.text((left + 210, height - 42), "红=上涨 绿=下跌", font=body_font, fill="#334155")
    image.save(path)


def write_chain_svg(path: Path) -> None:
    colors = ["#eff6ff", "#ecfdf5", "#fff7ed", "#f5f3ff", "#fdf2f8"]
    strokes = ["#2563eb", "#16a34a", "#ea580c", "#7c3aed", "#db2777"]
    node_cards: list[str] = []
    for idx, node in enumerate(PHYSICAL_AI_BLUEPRINT):
        y = 360 + idx * 175
        companies = " / ".join(node["companies"])
        node_cards.append(
            f'<rect x="95" y="{y}" width="1010" height="138" rx="18" fill="{colors[idx % len(colors)]}" stroke="{strokes[idx % len(strokes)]}" stroke-width="2"/>'
            f'<text x="125" y="{y + 38}" class="n">{idx + 1}. {node["node"]}</text>'
            f'<text x="125" y="{y + 70}" class="s">核心三公司：{companies}</text>'
            f'<text x="125" y="{y + 98}" class="s">投资逻辑：{node["logic"]}</text>'
            f'<text x="125" y="{y + 124}" class="s">反证风险：{node["risk"]}</text>'
        )
        if idx < len(PHYSICAL_AI_BLUEPRINT) - 1:
            node_cards.append(f'<line x1="600" y1="{y + 145}" x2="600" y2="{y + 168}" class="arrow"/>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1450" viewBox="0 0 1200 1450">
<style>
text{{font-family:'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',Arial,sans-serif}}
.title{{font-size:34px;font-weight:800;fill:#111827}}.h{{font-size:24px;font-weight:800;fill:#0f172a}}
.n{{font-size:19px;font-weight:700;fill:#111827}}.s{{font-size:15px;fill:#374151}}
.box{{rx:18;stroke-width:2}}.main{{fill:#eff6ff;stroke:#2563eb}}.risk{{fill:#fff1f2;stroke:#e11d48;stroke-dasharray:10 8}}
.arrow{{stroke:#2563eb;stroke-width:4;marker-end:url(#arrow)}}
</style>
<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M2,2 L10,6 L2,10 Z" fill="#2563eb"/></marker></defs>
<rect width="1200" height="1450" fill="#ffffff"/>
<text x="60" y="70" class="title">物理AI/人形机器人产业链：卡口节点与核心三公司</text>
<text x="60" y="112" class="s">研究主线：人形机器人量产爬坡 -> 执行器/传动/控制价值重估 -> 用订单、收入占比、K线结构筛出可执行机会</text>

<rect x="60" y="150" width="250" height="110" class="box main"/><text x="82" y="188" class="n">需求触发</text><text x="82" y="220" class="s">企业AI进入工作流</text><text x="82" y="246" class="s">具身智能从演示到量产</text>
<rect x="335" y="150" width="250" height="110" class="box main"/><text x="357" y="188" class="n">价格信号</text><text x="357" y="220" class="s">高估值样本波动放大</text><text x="357" y="246" class="s">市场惩罚远期叙事</text>
<rect x="610" y="150" width="250" height="110" class="box main"/><text x="632" y="188" class="n">研究焦点</text><text x="632" y="220" class="s">不买主题，找卡口</text><text x="632" y="246" class="s">订单/客户/良率验证</text>
<rect x="885" y="150" width="250" height="110" class="box main"/><text x="907" y="188" class="n">执行顺序</text><text x="907" y="220" class="s">卡口价值 -> 财务兑现</text><text x="907" y="246" class="s">-> 技术买卖点</text>

<text x="470" y="325" class="h">核心节点三公司校验</text>
{''.join(node_cards)}

<rect x="120" y="1250" width="960" height="135" class="box risk"/><text x="150" y="1292" class="n">反证退出</text><text x="150" y="1326" class="s">1. 无订单/客户认证/收入占比证据；2. 高估值继续杀跌且无基本面修复；3. 替代路线成熟或扩产过快压低毛利。</text>
<text x="150" y="1360" class="s">结论：每个节点至少三家公司对照，避免把单一强势股误判成整条产业链机会。</text>
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


def ensure_history(supp: dict[str, Any], symbol: str, *, live_fetch: bool = False) -> None:
    expected_date = a_stock_data.latest_expected_trade_date()
    rows = supp.get("price_history", {}).get("rows", []) if isinstance(supp.get("price_history"), dict) else []
    if rows:
        if not a_stock_data.price_history_is_stale({"rows": rows}, expected_date=expected_date):
            return
    if not live_fetch:
        try:
            fetched = a_stock_data.fetch_price_history_cached_or_live(symbol)
            fetched_rows = fetched.get("rows", []) if isinstance(fetched, dict) else []
            if fetched_rows:
                supp["price_history"] = fetched
        except Exception as exc:  # noqa: BLE001
            supp.setdefault("errors", []).append(f"price_history_local: {exc!r}")
        return
    for label, fetcher in (
        ("price_history_live", a_stock_data.fetch_price_history),
        ("price_history_tencent", a_stock_data.fetch_price_history_tencent),
        ("price_history_efinance", a_stock_data.fetch_price_history_efinance),
        ("price_history_baostock", a_stock_data.fetch_price_history_baostock),
        ("price_history_local", a_stock_data.fetch_price_history_fallback),
    ):
        try:
            fetched = fetcher(symbol)
            fetched_rows = fetched.get("rows", []) if isinstance(fetched, dict) else []
            if fetched_rows:
                if not a_stock_data.price_history_is_stale(fetched, expected_date=expected_date):
                    supp["price_history"] = fetched
                    return
                supp.setdefault("errors", []).append(f"{label}:stale_before_{expected_date}")
        except Exception as exc:  # noqa: BLE001
            supp.setdefault("errors", []).append(f"{label}: {exc!r}")


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

    upside = resistance1 - price if isinstance(resistance1, (int, float)) and price is not None else None
    downside = price - support1 if isinstance(support1, (int, float)) and price is not None else None
    risk_reward = upside / downside if upside is not None and downside and downside > 0 else None

    if price is not None and support1 and resistance1:
        buy_zone = f"建议买点：左侧只看{support1:.2f}附近缩量企稳；右侧需放量站回/突破{resistance1:.2f}后回踩确认"
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
        "risk_reward": _round_price(risk_reward),
        "buy_zone": buy_zone,
        "stop_loss": stop_loss,
        "pressure": pressure,
        "eps_anchor": eps_anchor,
        "target_low": eps_anchor * 100 if eps_anchor else None,
        "target_mid": eps_anchor * 140 if eps_anchor else None,
        "target_high": eps_anchor * 180 if eps_anchor else None,
        "sellside_pe_median": sorted(pe_forecasts)[len(pe_forecasts) // 2] if pe_forecasts else None,
    }


BUYABLE_DECISION_ACTIONS = {"paper_candidate", "buy", "buy_candidate"}


def trade_decisions(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pipeline = payload.get("research_pipeline", {})
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    engine = pipeline.get("trade_decision_engine", {})
    rows = engine.get("decisions", []) if isinstance(engine, dict) else []
    out: dict[str, dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and row.get("symbol"):
            out[str(row["symbol"])] = row
    return out


def buyable_decision_action(action: Any) -> bool:
    return str(action or "").strip().lower() in BUYABLE_DECISION_ACTIONS


def physical_buy_candidate(symbol: str, item: dict[str, Any]) -> bool:
    tech = item.get("tech", {}) if isinstance(item.get("tech"), dict) else {}
    decision = item.get("decision", {}) if isinstance(item.get("decision"), dict) else {}
    min_rr = decision.get("min_risk_reward")
    min_rr = float(min_rr) if isinstance(min_rr, (int, float)) else 1.6
    rr = tech.get("risk_reward")
    score = tech.get("institutional_trend_score")
    position = tech.get("position60")
    price = tech.get("price")
    support = tech.get("support1")
    resistance = tech.get("resistance1")
    technical_ok = (
        isinstance(rr, (int, float))
        and rr >= min_rr
        and isinstance(score, (int, float))
        and score >= 3.5
        and isinstance(position, (int, float))
        and 20 <= position <= 80
        and isinstance(price, (int, float))
        and isinstance(support, (int, float))
        and isinstance(resistance, (int, float))
        and resistance > price >= support
    )
    if item.get("decision_scope_present") and not item.get("has_trade_decision"):
        return False
    if item.get("has_trade_decision"):
        return buyable_decision_action(decision.get("action")) and technical_ok
    return technical_ok


def physical_buy_text(symbol: str, item: dict[str, Any]) -> str:
    tech = item.get("tech", {}) if isinstance(item.get("tech"), dict) else {}
    if physical_buy_candidate(symbol, item):
        return tech.get("buy_zone") or f"建议买点：{fmt(tech.get('support1'))}附近企稳或突破{fmt(tech.get('resistance1'))}回踩"
    return "等待买入触发：当前未进入买入候选；需风险收益比、趋势分、价格位置和订单/客户/收入证据同步满足"


def physical_sell_text(symbol: str, item: dict[str, Any]) -> str:
    tech = item.get("tech", {}) if isinstance(item.get("tech"), dict) else {}
    if physical_buy_candidate(symbol, item):
        return f"建议卖点：接近{tech.get('pressure')}先减仓；跌破{fmt(tech.get('support2'))}降级"
    return "未设技术目标：尚未进入买入候选，先观察证据和价格结构修复"


def company_tier(symbol: str, item: dict[str, Any]) -> tuple[str, str]:
    meta = item["meta"]
    tech = item["tech"]
    quote = item["quote"]
    score = 0
    if symbol in PHYSICAL_AI_ABSOLUTE_CORE:
        score += 3
    elif symbol in PHYSICAL_AI_HIGH_BETA:
        score += 2
    if isinstance(tech.get("institutional_trend_score"), (int, float)) and tech["institutional_trend_score"] >= 3.5:
        score += 1
    pe = quote.get("pe")
    if isinstance(pe, (int, float)) and pe > 180:
        score -= 1
    if "收入占比需" in meta.get("evidence_note", "") or "需验证" in meta.get("evidence_note", ""):
        score -= 1
    if symbol in PHYSICAL_AI_ABSOLUTE_CORE:
        tier = "绝对核心龙头"
    elif symbol in PHYSICAL_AI_HIGH_BETA or score >= 2:
        tier = "高弹性二线"
    else:
        tier = "主题观察"
    reason = (
        f"{meta['chain_position']}；趋势分{fmt(tech.get('institutional_trend_score'), 1)}/5；"
        f"PE {fmt(pe)}；证据状态：{meta['evidence_note']}"
    )
    return tier, reason


def physical_battle_rows(selected: dict[str, dict[str, Any]]) -> list[list[Any]]:
    by_node = {
        "减速器/精密传动": ["688017", "002472", "002896"],
        "丝杠/线性执行器": ["000837", "300580", "603667"],
        "伺服/运动控制": ["603728", "300124", "002979", "688320"],
    }
    logic = {node["node"]: node for node in PHYSICAL_AI_BLUEPRINT}
    rows: list[list[Any]] = []
    for node, symbols in by_node.items():
        items = [selected[s] for s in symbols if s in selected]
        companies = "、".join(item["meta"]["name"] for item in items[:3])
        best = sorted(
            items,
            key=lambda item: (
                item["tech"].get("institutional_trend_score") if isinstance(item["tech"].get("institutional_trend_score"), (int, float)) else 0,
                item["tech"].get("risk_reward") if isinstance(item["tech"].get("risk_reward"), (int, float)) else 0,
            ),
            reverse=True,
        )
        leader = best[0]["meta"]["name"] if best else "待验证"
        rows.append(
            [
                node,
                companies,
                logic.get(node, {}).get("logic", "决定机器人执行系统的性能和成本"),
                f"当前主研究位：{leader}",
                "客户认证/订单/收入占比/毛利率任一项出现公告级证据",
                logic.get(node, {}).get("risk", "订单不足或替代路线成熟"),
            ]
        )
    return rows


def physical_tier_rows(selected: dict[str, dict[str, Any]]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for symbol, item in selected.items():
        tier, reason = company_tier(symbol, item)
        rows.append(
            [
                tier,
                item["meta"]["name"],
                symbol,
                item["meta"]["chain_position"],
                reason,
                physical_buy_text(symbol, item),
                physical_sell_text(symbol, item),
                item["meta"]["evidence_note"],
            ]
        )
    order = {"绝对核心龙头": 0, "高弹性二线": 1, "主题观察": 2}
    return sorted(rows, key=lambda row: (order.get(str(row[0]), 9), str(row[1])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-file", default="data/raw/latest-full-loop.json")
    parser.add_argument("--live-fetch", action="store_true", help="Fetch missing public market/wencai data; off by default to keep loop bounded.")
    parser.add_argument("--pdf-text", action="store_true", help="Download/extract selected report PDF text for hard-fact mining; cached text is reused in later bounded runs.")
    args = parser.parse_args()
    payload_file = Path(args.payload_file)
    if not payload_file.is_absolute():
        payload_file = ROOT / payload_file

    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    DRAFTS.mkdir(parents=True, exist_ok=True)
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    quotes = {q["symbol"]: q for q in payload.get("a_share_quotes", [])}
    supplements = payload.get("stock_supplements", {})
    decision_map = trade_decisions(payload)
    previous_source = {}
    source_path = OUT / "source_data.json"
    if source_path.exists():
        try:
            previous_source = json.loads(source_path.read_text(encoding="utf-8"))
        except Exception:
            previous_source = {}
    previous_quotes = previous_source.get("selected_quotes", {}) if isinstance(previous_source, dict) else {}
    previous_supplements = previous_source.get("selected_supplements", {}) if isinstance(previous_source, dict) else {}

    selected: dict[str, dict[str, Any]] = {}
    for symbol, meta in SELECTED_SYMBOLS.items():
        quote = quotes.get(symbol) or (previous_quotes.get(symbol) if isinstance(previous_quotes, dict) else None)
        if not quote and args.live_fetch:
            try:
                quote = a_stock_data.fetch_quote(symbol)
            except Exception as exc:  # noqa: BLE001
                quote = {"symbol": symbol, "name": meta["name"], "errors": [repr(exc)]}
        if not quote:
            try:
                quote = a_stock_data.fetch_quote_fallback(symbol)
                quote.setdefault("name", meta["name"])
            except Exception:
                pass
        if not quote:
            quote = {"symbol": symbol, "name": meta["name"], "errors": ["quote not available; using bounded fallback"]}
        quotes[symbol] = quote
        supp = supplements.get(symbol) if isinstance(supplements, dict) else {}
        if not a_stock_data.stock_supplement_usable(supp) and isinstance(previous_supplements, dict):
            supp = previous_supplements.get(symbol, {})
        if not isinstance(supp, dict):
            supp = {}
        if not a_stock_data.stock_supplement_usable(supp):
            try:
                supp = a_stock_data.fetch_stock_supplement_fallback(symbol)
            except Exception:
                supp = {}
        supplements[symbol] = supp
        if args.live_fetch and not a_stock_data.stock_supplement_usable(supp):
            try:
                fetched = a_stock_data.fetch_stock_supplement_resilient(symbol)
                supp = a_stock_data.merge_stock_supplement(fetched, supp)
                supplements[symbol] = supp
            except Exception as exc:  # noqa: BLE001
                supp.setdefault("errors", []).append(f"stock_supplement: {exc!r}")
        ensure_history(supp, symbol, live_fetch=args.live_fetch)
        tech = technical_structure(quote, supp)
        decision = decision_map.get(symbol, {})
        selected[symbol] = {
            "meta": meta,
            "quote": quote,
            "supplement": supp,
            "tech": tech,
            "decision": decision,
            "has_trade_decision": bool(decision),
            "decision_scope_present": bool(decision_map),
        }

    focus = "688017"
    focus_supp = selected[focus]["supplement"]
    focus_quote = selected[focus]["quote"]
    lv = selected[focus]["tech"]
    if args.live_fetch:
        wencai_enrichment = wen_cai.fetch_research_enrichment({symbol: item["meta"]["name"] for symbol, item in selected.items()})
    else:
        wencai_enrichment = previous_source.get("wen_cai_enrichment", {}) if isinstance(previous_source, dict) else {}
        if not wencai_enrichment:
            wencai_enrichment = {"skipped": True, "reason": "live_fetch_disabled"}
    wencai_rows = wencai_summary_rows(wencai_enrichment)

    chain_svg = ASSETS / "physical-ai-chain-map.svg"
    chain_png = ASSETS / "physical-ai-chain-map.png"
    write_chain_svg(chain_svg)
    write_chain_png(chain_png)
    price_pngs: dict[str, Path] = {}
    for symbol, item in selected.items():
        if not physical_buy_candidate(symbol, item):
            continue
        meta = item["meta"]
        price_svg = ASSETS / f"{symbol}-technical-structure.svg"
        write_line_svg(
            price_svg,
            item["supplement"].get("price_history", {}).get("rows", []),
            f"{meta['name']} {symbol} 90日趋势/支撑压力",
            item["tech"],
        )
        price_png = ASSETS / f"{symbol}-technical-structure.png"
        write_candlestick_png(
            price_png,
            item["supplement"].get("price_history", {}).get("rows", []),
            f"{meta['name']} {symbol} 支撑/压力结构",
            item["tech"],
        )
        price_pngs[symbol] = price_png

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
        finance_png = ASSETS / "green-harmonic-revenue-growth.png"
        write_bar_svg(finance_svg, fin_rows, "绿的谐波营收同比变化")
        write_bar_png(finance_png, fin_rows, "绿的谐波营收同比变化")

    reports = focus_supp.get("research_reports", {}).get("rows", [])
    announcements = focus_supp.get("announcements", {}).get("rows", [])
    latest_fin = indicators[0] if indicators else {}
    industry_reports = payload.get("industry_reports", [])
    news = payload.get("news", {}).get("headlines", [])

    value_rows = [
        [node["node"], "核心三公司", "高" if idx < 3 else "中高", node["logic"], "高" if idx < 2 else "中-高", "、".join(node["companies"]), "卡口候选/重要配套", node["risk"]]
        for idx, node in enumerate(PHYSICAL_AI_BLUEPRINT)
    ]
    company_rows = []
    for symbol, item in selected.items():
        meta = item["meta"]
        quote = item["quote"]
        tech = item["tech"]
        exposure = "高" if symbol in {"688017", "002472", "002896", "000837", "300580", "603667"} else "中"
        status = "核心环节龙头/卡口候选" if symbol in {"688017", "002472", "000837", "300124"} else "高弹性配套/待验证"
        company_rows.append(
            [
                meta["name"],
                symbol,
                "上游核心部件" if "本体" not in meta["chain_position"] else "中游",
                meta["chain_position"],
                f"{exposure}；机器人收入占比需公告/财报继续核验",
                meta["chain_thesis"],
                f"{'高' if exposure == '高' else '中'}；趋势分{fmt(tech.get('institutional_trend_score'), 1)}/5",
                status,
                f"现价{fmt(tech.get('price') or quote.get('price'))}，PE {fmt(quote.get('pe'))}，支撑{fmt(tech.get('support1'))}，压力{tech.get('pressure')}；{meta['evidence_note']}",
            ]
        )
    company_rows.extend(
        [
            ["埃斯顿", "002747", "中游", "工业机器人/系统集成", "中；需区分机器人收入和自动化收入", "本体和系统集成验证下游需求，但利润弹性取决于规模与核心零部件能力", "中", "本体侧候选", "纳入产业链对照，不替代上游卡口主线"],
            ["机器人", "300024", "中游", "机器人本体/系统集成", "中；订单和盈利质量需验证", "老牌机器人平台型公司，适合观察行业景气但交易弹性需另证", "中", "需求验证位", "需要补充实时行情和财报后再进入核心交易表"],
            ["华中数控", "300161", "设备", "数控系统/精密加工", "中；受益于加工设备和国产替代", "加工精度和数控系统是核心部件良率底座", "中", "设备侧候选", "需要确认机器人核心零部件加工订单"],
            ["华辰装备", "300809", "设备", "精密磨床/加工设备", "中；与丝杠加工能力相关", "精密磨床影响丝杠和传动件良率", "中", "设备侧候选", "订单和客户结构需进一步核验"],
            ["日发精机", "002520", "设备", "数控机床/加工装备", "中低；需排除传统周期扰动", "设备链对良率和扩产有支撑", "中", "设备侧待验证", "暂不进入核心交易表"],
        ]
    )
    opportunity_rows = [
        ["核心环节龙头/卡口候选", "机器人量产带动精密传动需求，上游认证和寿命壁垒决定价值捕获", "绿的谐波", "订单/客户认证/收入占比披露；毛利率稳定；价格止跌", "估值过高、公告无法验证订单、替代路线成熟"],
        ["关键技术突破者", "丝杠、机床和精密加工能力决定运动执行部件良率和扩产", "秦川机床", "机器人客户、滚动功能部件订单、收入占比", "仅有概念标签，无法确认产业占比"],
        ["重要配套/高弹性", "伺服、电机、控制环节受益于关节数量和执行单元增多，但竞争更分散", "鸣志电器", "高端电机产品规格、客户认证、毛利率", "技术壁垒和客户粘性弱于减速器"],
        ["相邻基础设施", "工程机械电动化、储能和制造业资本开支提供侧面验证", "宁德时代", "工程机械电动化订单、储能需求", "不是机器人核心部件，不能上升为主线标的"],
    ]
    node_three_rows = [
        [node["node"], "、".join(node["companies"]), node["logic"], node["risk"]]
        for node in PHYSICAL_AI_BLUEPRINT
    ]

    def latest_financial_summary(symbol: str, item: dict[str, Any]) -> str:
        indicators = item["supplement"].get("financials", {}).get("statements", {}).get("indicators", [])
        row = indicators[0] if indicators else {}
        if row:
            return (
                f"{str(row.get('REPORT_DATE_NAME') or row.get('REPORT_DATE') or '')[:10]}营收{money(row.get('TOTALOPERATEREVE'))}"
                f"，营收同比{fmt(row.get('TOTALOPERATEREVETZ'))}%；归母净利{money(row.get('PARENTNETPROFIT'))}"
                f"，归母净利同比{fmt(row.get('PARENTNETPROFITTZ'))}%"
            )
        return SELECTED_SYMBOLS[symbol]["financial_note"]

    def target_space_text(symbol: str, tech: dict[str, Any]) -> str:
        if tech.get("eps_anchor"):
            position = SELECTED_SYMBOLS[symbol]["chain_position"]
            if "减速器" in position or "传动" in position:
                multiples = (50, 70, 90)
            elif "丝杠" in position or "轴承" in position:
                multiples = (40, 55, 75)
            elif "伺服" in position or "控制" in position or "电机" in position:
                multiples = (25, 35, 50)
            else:
                multiples = (25, 40, 55)
            eps = float(tech["eps_anchor"])
            prices = [eps * m for m in multiples]
            return (
                f"建议卖点/目标：接近压力位{tech.get('pressure')}先减仓；"
                f"估值锚改用分环节PE {multiples[0]}/{multiples[1]}/{multiples[2]}x，"
                f"EPS锚{fmt(eps)}，情景价 {fmt(prices[0])}/{fmt(prices[1])}/{fmt(prices[2])}；"
                "若目标价显著低于现价，只说明当前估值透支，不上修买点"
            )
        return f"建议卖点/目标：接近压力位 {tech.get('pressure')} 或60日箱体上沿 {fmt(tech.get('high60'))} 先减仓；缺少一致EPS预测时不做远期目标上修"

    trading_rows = []
    for symbol, item in selected.items():
        meta = item["meta"]
        quote = item["quote"]
        tech = item["tech"]
        score = tech.get("institutional_trend_score")
        is_buy_candidate = physical_buy_candidate(symbol, item)
        action = "现阶段买入候选，允许展开K线压力/支撑跟踪" if is_buy_candidate else "观察名单，等待结构修复和证据补强"
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
                    f"箱体位置{fmt(tech.get('position60'))}%；{tech.get('volume_state')}；趋势分{fmt(score, 1)}/5；风险收益比{fmt(tech.get('risk_reward'))}"
                ),
                physical_buy_text(symbol, item),
                f"{tech.get('stop_loss')}；产业证据失效：{meta['evidence_note']}",
                target_space_text(symbol, tech) if is_buy_candidate else physical_sell_text(symbol, item),
                action,
            ]
        )

    provider_rows = provider_insight_rows(payload)
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
        f"![{item['meta']['name']}买入候选K线结构](assets/{price_pngs[symbol].name})" for symbol, item in selected.items() if symbol in price_pngs
    )
    if not selected_price_images:
        selected_price_images = "> 本轮没有通过交易决策与技术面风险收益比门槛的现阶段买入候选，K线压力/支撑图不展开；龙头和核心公司仍保留在产业链、估值和证据观察表。"
    selected_names = "、".join(item["meta"]["name"] for item in selected.values())
    battle_rows = physical_battle_rows(selected)
    tier_rows = physical_tier_rows(selected)
    hard_fact_table_rows = physical_hard_fact_rows(payload, selected, industry_reports, news, pdf_text_live=args.pdf_text)
    density_rows = physical_evidence_density_rows(hard_fact_table_rows)
    density_png = ASSETS / "physical-ai-evidence-density.png"
    valuation_png = ASSETS / "physical-ai-stock-valuation.png"
    write_evidence_density_png(density_png, density_rows)
    write_stock_valuation_png(valuation_png, selected)
    absolute_names = "、".join(str(row[1]) for row in tier_rows if row[0] == "绝对核心龙头") or "绿的谐波、双环传动、汇川技术"
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
        f"1. 强命题：物理 AI 当前不是“谁名字像机器人谁涨”，而是执行器链进入第一次龙头筛选期；真正能对标深度研究的主线应收敛到减速器/精密传动、丝杠/线性执行器、伺服/运动控制三类瓶颈。置信度中等偏上，当前绝对核心候选：{absolute_names}。\n"
        f"2. 绿的谐波仍是精密传动主研究位，但 PE {fmt(focus_quote.get('pe'))} 已经把远期成长打得很满；如果后续没有机器人订单、客户认证或收入占比证据，它只能是高波动卡口股，不是无条件龙头。\n"
        f"3. 核心跟踪标的不应只剩一只。本报告把 {selected_names} 作为上游核心部件主线跟踪，并把公司分为绝对核心龙头、高弹性二线和主题观察三层；只有“产业证据 + 股价位置”同时转强，才进入可执行机会。\n"
        "4. 买点不能靠一句“机器人量产”判断，必须同时满足三件事：订单/客户/收入证据补强、估值消化到可解释区间、价格结构从单边下跌转为企稳修复。否则只是主题波动，不是产业链买点，风险收益比不成立。\n"
        "5. 只有主题热度、缺少机器人订单/客户认证/收入占比的样本不能进入主线；相邻链路只作为需求侧辅助验证，不进入核心公司映射。",
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
        "## 2.5 硬事实台账与证据密度\n\n"
        "对标深度文章时，物理 AI 最大短板不是产业链节点不全，而是订单、客户认证、产能利用率、良率、机器人收入占比这些硬事实不足。下面的台账把公告级、财报级、研报级和标题级线索拆开，避免用弱证据覆盖强报告。\n\n"
        "### 正文级事实摘要\n\n"
        + physical_fact_summary_bullets(hard_fact_table_rows)
        + "\n\n"
        + md_table(["事实类型", "硬事实/线索", "涉及节点", "涉及公司", "数值/时间", "来源", "证据强度", "交易含义"], hard_fact_table_rows)
        + f"\n\n### 证据密度评分\n\n![证据密度评分](assets/{density_png.name})\n\n"
        + md_table(["维度", "数量/评分", "口径", "含义"], density_rows),
        "## 3. 产业链全景图谱\n\n![产业链投研拆解图](assets/physical-ai-chain-map.png)\n\n"
        "### 核心节点三公司校验\n\n"
        + md_table(["产业链节点", "至少三家核心受益/候选公司", "为什么重要", "反证风险"], node_three_rows)
        + "\n\n### 瓶颈战斗地图\n\n"
        + md_table(["瓶颈节点", "当前三家核心公司", "为什么卡", "当前主研究位", "升级信号", "反证信号"], battle_rows)
        + "\n\n"
        + md_table(
            ["环节", "细分领域", "角色", "关键输入", "关键输出", "价值/成本驱动", "代表A股公司"],
            [
                ["上游核心部件", "减速器、丝杠、伺服、电机、控制器", "决定运动精度、寿命和负载", "精密加工、材料、客户认证", "精密传动/运动控制部件", "认证周期、良率、寿命、订单", "绿的谐波、双环传动、中大力德、秦川机床、贝斯特、五洲新春、鸣志电器、汇川技术、雷赛智能"],
                ["上游设备/检测", "精密加工与检测设备", "影响良率和扩产速度", "机床、检测、工艺Know-how", "加工/检测能力", "扩产周期、良率爬坡", "华中数控、华辰装备、日发精机待验证"],
                ["中游制造", "机器人本体、系统集成、工程机械", "承接终端需求和场景交付", "核心零部件、软件、工程能力", "机器人/智能设备", "订单、场景复制、成本控制", "埃斯顿、汇川技术、机器人"],
                ["下游应用", "工厂、物流、工程施工、服务机器人", "形成最终需求", "ROI、客户预算、场景标准化", "自动化/智能化服务", "订单、销量、客户验证", "非A股或间接映射"],
                ["相邻链路", "新能源、储能、工程机械电动化", "侧面验证制造业资本开支", "电池、电驱、储能", "电动化设备", "销量和资本开支", "宁德时代"],
            ],
        ),
        "## 4. 上游材料、部件与制程要素挖掘\n\n" + md_table(
            ["上游层级", "细分材料/部件", "对目标产业的作用", "价值/稀缺性", "卡脖子程度", "A股候选", "纳入主线判断"],
            [
                ["Product BOM", "减速器/丝杠/伺服电机", "决定运动精度、负载和寿命", "高；客户认证和可靠性要求高", "高", "绿的谐波/双环传动/中大力德/秦川机床/贝斯特/五洲新春/鸣志电器/汇川技术/雷赛智能", "Core"],
                ["Equipment/tools", "精密加工与检测设备", "影响良率、成本和扩产速度", "中高；良率爬坡慢", "中", "华中数控/华辰装备/日发精机待验证", "Important"],
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
        )
        + "\n\n### 瓶颈四标准校验\n\n"
        + md_table(
            ["候选环节", "不可替代", "供给刚性", "寡头垄断", "机构低配", "反证条件"],
            [
                ["减速器/丝杠", "高", "中高", "中", "待核验", "客户切换加快、替代供应商通过认证、订单和收入占比不兑现"],
                ["伺服/电机/控制器", "中", "中", "中低", "待核验", "价格竞争加剧、毛利率下行、客户认证不能转为订单"],
                ["本体与系统集成", "中低", "中", "中低", "待核验", "整机竞争分散、交付利润率不足、核心部件外采导致利润外流"],
            ],
        ),
        "## 7. A股公司映射与核心地位判断\n\n" + md_table(
            ["公司", "代码", "环节", "细分领域", "产业占比/暴露度", "核心技术/产品", "卡脖子相关性", "环节地位", "证据与备注"],
            company_rows,
        ),
        "## 8. 投资线索、交易跟踪与目标价情景\n\n"
        "### 8.1 机会类型\n\n" + md_table(["机会类型", "产业链逻辑", "代表A股公司", "验证里程碑", "风险"], opportunity_rows)
        + "\n\n### 8.2 龙头分层与事件-交易触发器\n\n"
        + md_table(["层级", "公司", "代码", "节点", "入选/降级原因", "买入触发", "卖出/降级触发", "反证退出"], tier_rows)
        + "\n\n### 8.3 核心标的股票层面跟踪\n\n"
        "股票层面的顺序是：先确认公司确实卡在产业链关键环节，再看财务和估值是否能解释预期，最后才用价格结构寻找买点。下表里的买点不是“明天买什么”，而是用于持续跟踪的触发条件：支撑位只代表观察区，必须叠加订单/客户/收入证据；压力位代表兑现或减仓观察位。\n\n"
        + f"![核心标的估值与赔率](assets/{valuation_png.name})\n\n"
        + selected_price_images + "\n\n"
        + (f"![绿的谐波营收同比](assets/{finance_png.name})\n\n" if finance_png else "")
        + md_table(
            ["公司", "代码", "产业链结论", "财务质量", "当前估值", "技术面/趋势", "买入条件", "止损/失效条件", "卖出/目标", "综合判断"],
            trading_rows,
        )
        + "\n\n> 说明：目标价情景使用券商研报 EPS 预测的中位数作为粗略锚点，并按减速器/丝杠/伺服等环节使用不同 PE 区间；该区间不是买入建议，而是用于判断市场价格是否已经透支远期成长。",
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

    # 方案 A 写入策略(不整篇覆盖 canonical report.md)。draft 文件名带 run_id+cycle,
    # 同一天多轮 loop 不会互相覆盖。实现见 write_report_outputs(已抽成纯函数便于单测)。
    canonical_path, draft_path, seeded_canonical = write_report_outputs(report, payload_file)
    source_data = {
        "generated_at": datetime.now().isoformat(),
        "payload_file": str(payload_file.resolve().relative_to(ROOT.resolve())),
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
        "hard_fact_rows": hard_fact_table_rows,
        "evidence_density": density_rows,
        "provider_insight_rows": provider_rows,
        "pdf_text_live": args.pdf_text,
        "source_rows": source_rows,
        "sources": source_entries,
        "assets": [str(p.relative_to(OUT)) for p in ASSETS.iterdir()],
    }
    (OUT / "source_data.json").write_text(json.dumps(source_data, ensure_ascii=False, indent=2), encoding="utf-8")
    quality_proc = subprocess.run(
        [
            sys.executable,
            "skills/industry-chain-analysis/scripts/report_quality.py",
            str(draft_path),
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
    print(json.dumps({
        "report": str(canonical_path.relative_to(ROOT)),
        "draft": str(draft_path.relative_to(ROOT)),
        "seeded_canonical": seeded_canonical,
        "quality": quality,
    }, ensure_ascii=False, indent=2))
    if not quality.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
