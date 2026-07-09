from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# 发现/打分链路的主题命中词。
# 语义(方案 A):每日挖掘围绕 config/theme_pool.json 的主题池组织,而不是围绕旧的
# industry 分类。THEME_KEYWORDS 由 theme_pool 的 discovery_keywords 驱动(键为规范主题
# 目录键,如 "physical-ai"),配置缺失/损坏时回退到下面的硬编码字典,保证离线可跑。
_FALLBACK_THEME_KEYWORDS = {
    "physical-ai": ["AI", "人工智能", "大模型", "算力", "机器人", "物理AI", "智能体"],
    "ai-compute-infra": ["半导体", "芯片", "封装", "CPU", "GPU", "晶圆", "先进制程"],
    "ai-industrial-software": ["设备", "机械", "工程机械", "机床", "工业", "通用设备"],
    "datacenter-power": ["新能源", "锂电", "电池", "光伏", "储能", "风电"],
    "autonomous-low-altitude": ["汽车", "新能源车", "智能驾驶", "零部件", "车载"],
    "ai-commercialization": ["消费", "酒店", "餐饮", "服饰", "旅游", "零售"],
    "ai-fintech-infra": ["银行", "证券", "保险", "理财", "券商"],
}


def _theme_pool_path() -> Path:
    # capability_chain.py 位于 loop_os/domain/, 仓库根为 parents[2]
    return Path(__file__).resolve().parents[2] / "config" / "theme_pool.json"


def _load_theme_keywords() -> dict[str, list[str]]:
    """从 theme_pool.json 的 discovery_keywords 构造主题命中词表, 失败时回退硬编码。"""
    path = _theme_pool_path()
    try:
        pool = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(_FALLBACK_THEME_KEYWORDS)
    themes = pool.get("themes")
    if not isinstance(themes, dict):
        return dict(_FALLBACK_THEME_KEYWORDS)
    keywords: dict[str, list[str]] = {}
    for key, meta in themes.items():
        if not isinstance(meta, dict):
            continue
        dk = meta.get("discovery_keywords")
        if isinstance(dk, list) and dk:
            keywords[str(key)] = [str(t) for t in dk if str(t).strip()]
    return keywords or dict(_FALLBACK_THEME_KEYWORDS)


THEME_KEYWORDS = _load_theme_keywords()

_SKILL_HEALTH_CACHE: dict[str, Any] | None = None


def _loads_json_object_from_output(output: str) -> dict[str, Any]:
    if not output.strip():
        return {}
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        start = output.find("{")
        end = output.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(output[start : end + 1])
    return value if isinstance(value, dict) else {"value": value}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha1(value.encode('utf-8')).hexdigest()[:10]}"


def _text_hit_score(text: str, keywords: list[str]) -> int:
    low = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in low)


def news_scanner(news: dict[str, Any], reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Scan public news and research-report titles into a common event stream."""
    items: list[dict[str, Any]] = []
    for headline in news.get("headlines", []):
        title = str(headline.get("title") or "")
        if not title:
            continue
        items.append(
            {
                "id": _id("news", title + str(headline.get("url"))),
                "kind": "news",
                "title": title,
                "source": headline.get("source") or "public_feed",
                "url": headline.get("url"),
                "published_at": headline.get("published_at"),
                "public_source": True,
            }
        )
    for report in reports:
        title = str(report.get("title") or "")
        if not title:
            continue
        items.append(
            {
                "id": _id("report", str(report.get("info_code")) + title),
                "kind": "research_report",
                "title": title,
                "source": report.get("org") or "eastmoney_report",
                "industry": report.get("industry_name"),
                "published_at": report.get("publish_date"),
                "info_code": report.get("info_code"),
                "public_source": True,
            }
        )
    return {"stage": "news-scanner", "items": items, "item_count": len(items), "generated_at": _now()}


def article_reader(scanned: dict[str, Any]) -> dict[str, Any]:
    """Digest public items without exposing internal paths."""
    digests: list[dict[str, Any]] = []
    for item in scanned.get("items", []):
        title = str(item.get("title") or "")
        matched = []
        for theme, keywords in THEME_KEYWORDS.items():
            hits = _text_hit_score(title, keywords)
            if hits:
                matched.append({"theme": theme, "hits": hits})
        digests.append(
            {
                "id": item.get("id"),
                "kind": item.get("kind"),
                "title": title,
                "source": item.get("source"),
                "url": item.get("url"),
                "industry": item.get("industry"),
                "published_at": item.get("published_at"),
                "themes": sorted(matched, key=lambda x: x["hits"], reverse=True),
                "digest": f"{title}。需验证其对终端需求、产业链卡口、A股公司暴露和价格行为的增量影响。",
            }
        )
    return {"stage": "article-reader", "digests": digests, "digest_count": len(digests), "generated_at": _now()}


def score_hot_industries(reader: dict[str, Any]) -> dict[str, Any]:
    theme_scores: Counter[str] = Counter()
    industry_scores: Counter[str] = Counter()
    support: dict[str, list[dict[str, Any]]] = {}
    for digest in reader.get("digests", []):
        kind_weight = 3 if digest.get("kind") == "research_report" else 1
        title = str(digest.get("title") or "")
        for theme, keywords in THEME_KEYWORDS.items():
            hits = _text_hit_score(title, keywords)
            if hits:
                theme_scores[theme] += hits * kind_weight
                support.setdefault(theme, []).append(digest)
        if digest.get("industry"):
            industry_scores[str(digest["industry"])] += kind_weight
    ranked = [
        {
            "theme": theme,
            "score": score,
            "support_count": len(support.get(theme, [])),
            "sample_titles": [item["title"] for item in support.get(theme, [])[:5]],
        }
        for theme, score in theme_scores.most_common()
    ]
    top = ranked[0] if ranked else {"theme": "unknown", "score": 0, "support_count": 0, "sample_titles": []}
    return {
        "stage": "hotspot-scoring",
        "ranked_themes": ranked,
        "ranked_industries": industry_scores.most_common(10),
        "selected": top,
        "generated_at": _now(),
    }


def _load_skill_manifest(root: Path) -> dict[str, Any]:
    skill_dir = root / "skills" / "industry-chain-analysis"
    files = [
        "SKILL.md",
        "references/bottleneck-methodology.md",
        "references/analysis-methodology.md",
        "references/upstream-discovery.md",
        "references/a-share-screening.md",
        "references/data-sourcing.md",
        "references/report-template.md",
        "references/report-quality.md",
        "references/insight-design-constraints.md",
        "scripts/check_data_sources.py",
        "scripts/public_data.py",
        "scripts/report_quality.py",
    ]
    present = [item for item in files if (skill_dir / item).exists()]
    return {"skill": "industry-chain-analysis", "path": "skills/industry-chain-analysis", "files_used": present}


def _run_skill_health_check(root: Path, enabled: bool, probe_code: str) -> dict[str, Any]:
    global _SKILL_HEALTH_CACHE
    if not enabled:
        return {"status": "skipped", "reason": "enable_skill_health_check=false"}
    if _SKILL_HEALTH_CACHE is not None:
        return _SKILL_HEALTH_CACHE
    script = root / "skills" / "industry-chain-analysis" / "scripts" / "check_data_sources.py"
    if not script.exists():
        _SKILL_HEALTH_CACHE = {"status": "error", "error": "check_data_sources.py missing"}
        return _SKILL_HEALTH_CACHE
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--probe-code",
                probe_code,
                "--history-start",
                "2026-01-01",
                "--history-end",
                "2026-01-10",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=45,
        )
        payload = _loads_json_object_from_output(proc.stdout)
        _SKILL_HEALTH_CACHE = {
            "status": "ok" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "report": payload,
            "stderr_tail": proc.stderr[-1000:],
        }
    except subprocess.TimeoutExpired as exc:
        _SKILL_HEALTH_CACHE = {
            "status": "skipped",
            "reason": "check_data_sources.py timeout",
            "error": repr(exc),
        }
    except Exception as exc:
        _SKILL_HEALTH_CACHE = {"status": "error", "error": repr(exc)}
    return _SKILL_HEALTH_CACHE


def _source_trail_from_health(root: Path, health: dict[str, Any]) -> dict[str, Any]:
    public_data_path = root / "skills" / "industry-chain-analysis" / "scripts" / "public_data.py"
    report = health.get("report") if isinstance(health, dict) else None
    if not public_data_path.exists() or not isinstance(report, dict):
        return {"status": "unavailable", "entries": []}
    try:
        spec = importlib.util.spec_from_file_location("research_os_skill_public_data", public_data_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load public_data.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        trail = module.SourceTrail.from_health_check(report)
        return {"status": "ok", "entries": trail.to_list()}
    except Exception as exc:
        return {"status": "error", "error": repr(exc), "entries": []}


def _chain_tables(theme: str) -> dict[str, Any]:
    # theme 现在是 theme_pool 规范键(如 physical-ai / ai-compute-infra), 也兼容旧的
    # semiconductor / equipment / ai_physical_ai 命名, 保持链路稳健。
    theme = str(theme or "").lower()
    if "semiconductor" in theme or "compute-infra" in theme or "compute_infra" in theme:
        upstream = ["高端基板材料", "光刻/刻蚀/检测设备", "EDA/IP", "晶圆代工", "先进封装产线"]
        midstream = ["IC封装基板", "芯片设计", "封测", "算力服务器部件"]
        downstream = ["AI服务器", "数据中心", "国产CPU/GPU替代", "云厂商资本开支"]
        upstream_materials = [
            {"上游层级": "Product BOM", "细分材料/部件": "ABF/BT封装基板", "对目标产业的作用": "承载高端芯片封装互连", "价值/稀缺性": "高", "卡脖子程度": "High", "A股候选": "兴森科技/深南电路(待验证具体高端占比)", "纳入主线判断": "Core"},
            {"上游层级": "Process materials", "细分材料/部件": "光刻胶/CMP/电子特气", "对目标产业的作用": "制造良率和先进制程约束", "价值/稀缺性": "高", "卡脖子程度": "High", "A股候选": "华特气体/安集科技/彤程新材", "纳入主线判断": "Important"},
            {"上游层级": "Adjacent infrastructure", "细分材料/部件": "光模块/液冷/高速连接", "对目标产业的作用": "AI集群扩容配套", "价值/稀缺性": "中高", "卡脖子程度": "Medium", "A股候选": "中际旭创/新易盛/英维克", "纳入主线判断": "Adjacent"},
        ]
        value_distribution = [
            {"产业链环节": "上游", "细分领域/关键产品": "先进封装材料与设备", "BOM成本占比/价值占比": "定性高", "核心技术壁垒": "客户认证/制程良率/材料配方", "卡脖子程度": "High", "代表A股公司": "兴森科技、安集科技", "公司环节地位": "重要配套/待验证核心", "证据口径/备注": "需研报正文和公告验证收入占比"},
            {"产业链环节": "中游", "细分领域/关键产品": "封测/芯片设计", "BOM成本占比/价值占比": "高", "核心技术壁垒": "设计/IP/封装工艺", "卡脖子程度": "Medium", "代表A股公司": "通富微电、寒武纪", "公司环节地位": "核心/挑战者", "证据口径/备注": "公开报告标题级信号，待财报交叉验证"},
        ]
    elif "equipment" in theme or "ai_physical_ai" in theme or "physical-ai" in theme or "physical_ai" in theme:
        upstream = ["减速器", "伺服电机", "控制器", "传感器", "核心材料与加工设备"]
        midstream = ["人形机器人本体", "工程机械", "通用设备", "系统集成"]
        downstream = ["工厂自动化", "物流搬运", "工程施工", "服务机器人场景"]
        upstream_materials = [
            {"上游层级": "Product BOM", "细分材料/部件": "减速器/丝杠/伺服电机", "对目标产业的作用": "决定机器人运动精度和负载", "价值/稀缺性": "高", "卡脖子程度": "High", "A股候选": "绿的谐波/鸣志电器/秦川机床", "纳入主线判断": "Core"},
            {"上游层级": "Equipment/tools", "细分材料/部件": "精密加工与检测设备", "对目标产业的作用": "影响良率、成本和扩产速度", "价值/稀缺性": "中高", "卡脖子程度": "Medium", "A股候选": "日发精机/华中数控(待验证)", "纳入主线判断": "Important"},
            {"上游层级": "Adjacent infrastructure", "细分材料/部件": "工业软件/视觉传感/AI模型", "对目标产业的作用": "提升通用性和场景泛化", "价值/稀缺性": "中", "卡脖子程度": "Medium", "A股候选": "科大讯飞/虹软科技(待验证)", "纳入主线判断": "Adjacent"},
        ]
        value_distribution = [
            {"产业链环节": "上游", "细分领域/关键产品": "减速器/丝杠/伺服系统", "BOM成本占比/价值占比": "定性高", "核心技术壁垒": "精密加工、寿命、客户认证", "卡脖子程度": "High", "代表A股公司": "绿的谐波、秦川机床、鸣志电器", "公司环节地位": "卡口候选/重要配套", "证据口径/备注": "需公告和订单验证商业化节奏"},
            {"产业链环节": "中游", "细分领域/关键产品": "本体与系统集成", "BOM成本占比/价值占比": "中高", "核心技术壁垒": "工程交付、成本控制、场景数据", "卡脖子程度": "Medium", "代表A股公司": "埃斯顿、汇川技术", "公司环节地位": "核心/重要", "证据口径/备注": "需区分机器人业务收入占比"},
        ]
    else:
        upstream = ["关键原材料", "核心设备", "渠道/牌照/数据", "上游供给约束"]
        midstream = ["生产制造", "平台运营", "核心产品/服务"]
        downstream = ["终端客户", "应用场景", "渠道和资本开支"]
        upstream_materials = [
            {"上游层级": "Core input", "细分材料/部件": "关键原材料/设备/许可", "对目标产业的作用": "决定供给弹性", "价值/稀缺性": "待验证", "卡脖子程度": "Medium", "A股候选": "待验证", "纳入主线判断": "Important"},
        ]
        value_distribution = [
            {"产业链环节": "上游", "细分领域/关键产品": "关键输入", "BOM成本占比/价值占比": "待验证", "核心技术壁垒": "供给约束/资质/客户认证", "卡脖子程度": "Medium", "代表A股公司": "待验证", "公司环节地位": "待验证", "证据口径/备注": "需进一步取证"},
        ]
    return {"upstream": upstream, "midstream": midstream, "downstream": downstream, "upstream_materials": upstream_materials, "value_distribution": value_distribution}


def _company_mapping(quotes: list[dict[str, Any]], theme: str) -> list[dict[str, str]]:
    mapping = []
    for quote in quotes:
        symbol = str(quote.get("symbol") or "")
        name = str(quote.get("name") or symbol)
        if not symbol:
            continue
        if "688017" == symbol:
            link, segment, product, relevance, position = "上游", "减速器/核心零部件", "精密传动部件", "High/待公告验证", "卡口候选"
        elif "300750" == symbol:
            link, segment, product, relevance, position = "相邻链路", "新能源/储能", "动力电池与储能系统", "Low", "相邻基础设施"
        elif "600519" == symbol:
            link, segment, product, relevance, position = "非主线", "消费品", "白酒", "None", "反例/非产业链样本"
        else:
            link, segment, product, relevance, position = "待验证", "待验证", "待验证", "Low", "待验证"
        mapping.append(
            {
                "公司": name,
                "代码": symbol,
                "环节": link,
                "细分领域": segment,
                "产业占比/暴露度": "未披露；需年报/公告确认",
                "核心技术/产品": product,
                "卡脖子相关性": relevance,
                "环节地位": position,
                "证据与备注": "由公开行情样本进入观察；不能仅凭市场标签确认为核心暴露。",
            }
        )
    return mapping


def run_industry_chain_mapper(root: Path, scoring: dict[str, Any], reader: dict[str, Any], payload_base: dict[str, Any]) -> dict[str, Any]:
    selected = scoring.get("selected", {})
    theme = selected.get("theme") or "unknown"
    theme_digests = [
        item
        for item in reader.get("digests", [])
        if any(hit.get("theme") == theme for hit in item.get("themes", []))
    ][:12]
    tables = _chain_tables(theme)
    probe_code = str((payload_base.get("a_share_quotes") or [{}])[0].get("symbol") or "600276")
    health = _run_skill_health_check(root, bool(payload_base.get("enable_skill_health_check")), probe_code)
    source_trail = _source_trail_from_health(root, health)
    return {
        "stage": "industry-chain-mapper",
        "mode": "Standard",
        "selected_theme": theme,
        "score": selected.get("score", 0),
        "skill_manifest": _load_skill_manifest(root),
        "methodology_applied": [
            "大趋势 -> 供应链 -> 物理约束 -> 瓶颈卡口 -> 稀缺供应商 -> 低配误定价 -> 催化跟踪 -> 反证退出",
            "先完成产业链和公司暴露判断，再做估值与技术面跟进。",
            "公告/年报/研报正文优先于概念标签；公开 adapter 只作发现和交叉验证。",
        ],
        "skill_health_check": health,
        "source_trail": {
            "status": source_trail.get("status"),
            "error": source_trail.get("error"),
            "entry_count": len(source_trail.get("entries", [])),
            "entries": source_trail.get("entries", [])[:12],
        },
        "chain_map": {"upstream": tables["upstream"], "midstream": tables["midstream"], "downstream": tables["downstream"]},
        "upstream_material_discovery": tables["upstream_materials"],
        "core_value_distribution": tables["value_distribution"],
        "company_mapping": _company_mapping(payload_base.get("a_share_quotes", []), theme),
        "bottleneck_candidates": [
            {"rank": 1, "link": row["细分领域/关键产品"], "companies": row["代表A股公司"], "standards": "不可替代/供给刚性/客户认证/待验证低配", "catalyst": "订单、公告、研报正文或客户验证", "invalidation": "替代路线成熟、扩产过快、收入暴露不足"}
            for row in tables["value_distribution"][:3]
        ],
        "bottleneck_screen": [
            {"criterion": "不可替代", "question": "是否存在短期难以替代的材料、设备、工艺或客户认证？"},
            {"criterion": "供给刚性", "question": "扩产是否受产能、认证、资本开支或人才约束？"},
            {"criterion": "寡头集中", "question": "核心环节是否由少数供应商控制？"},
            {"criterion": "机构低配", "question": "市场是否仍把它当普通受益而非卡口资产定价？"},
        ],
        "supporting_public_items": theme_digests,
        "next_verifications": [
            "读取研报正文或公告，验证需求来自订单/销量/资本开支，而不是标题热度。",
            "用公告、年报、互动易或调研纪要确认 A 股公司真实收入/订单暴露。",
            "补资金流、龙虎榜和估值分位，判断热度是否过度拥挤。",
        ],
        "invalidation_triggers": [
            "公开公告/年报无法验证候选公司的产业链收入或订单暴露。",
            "核心环节出现替代路线、客户切换或新增供给导致卡口缓解。",
            "估值和资金拥挤先于基本面兑现，导致赔率不足。",
        ],
    }


def stock_analyzer(quotes: list[dict[str, Any]], supplements: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for quote in quotes:
        symbol = str(quote.get("symbol") or "")
        pe = quote.get("pe")
        pb = quote.get("pb")
        change = quote.get("change_pct")
        valuation_score = 2
        if quote.get("valuation_band") == "normal":
            valuation_score += 1
        if isinstance(pe, (int, float)) and pe < 30:
            valuation_score += 1
        if isinstance(pb, (int, float)) and pb > 10:
            valuation_score -= 1
        technical_score = 2
        if isinstance(change, (int, float)) and change > 0:
            technical_score += 1
        if isinstance(change, (int, float)) and change < -5:
            technical_score -= 1
        supp = supplements.get(symbol, {})
        financials = supp.get("financials", {}).get("statements", {}) if isinstance(supp.get("financials"), dict) else {}
        indicators = financials.get("indicators", []) if isinstance(financials, dict) else []
        latest_indicator = indicators[0] if indicators else {}
        announcements = supp.get("announcements", {}).get("rows", []) if isinstance(supp.get("announcements"), dict) else []
        research_reports = supp.get("research_reports", {}).get("rows", []) if isinstance(supp.get("research_reports"), dict) else []
        fund_flow_rows = supp.get("fund_flow", {}).get("rows", []) if isinstance(supp.get("fund_flow"), dict) else []
        dragon_rows = supp.get("dragon_tiger", {}).get("rows", []) if isinstance(supp.get("dragon_tiger"), dict) else []
        out.append(
            {
                "symbol": symbol,
                "name": quote.get("name"),
                "business_model": "待用公告/年报确认主营暴露" if not announcements else f"公告样本：{announcements[0].get('title')}",
                "financial": {
                    "quality": "available" if latest_indicator else "unknown",
                    "supplement": supp.get("fundamental", {}),
                    "latest_indicator": {
                        "report_date": latest_indicator.get("REPORT_DATE"),
                        "revenue": latest_indicator.get("TOTALOPERATEREVE"),
                        "parent_net_profit": latest_indicator.get("PARENTNETPROFIT"),
                        "roe": latest_indicator.get("ROEJQ") or latest_indicator.get("ROE"),
                        "gross_margin": latest_indicator.get("XSMLL") or latest_indicator.get("GROSSPROFITRATE"),
                    },
                },
                "valuation": {
                    "pe": pe,
                    "pb": pb,
                    "band": quote.get("valuation_band"),
                    "score": max(0, min(5, valuation_score)),
                    "method": "PE/PB current snapshot; historical percentile pending",
                },
                "technical": {
                    "change_pct": change,
                    "score": max(0, min(5, technical_score)),
                    "role": "secondary_tool",
                    "comment": "技术面只作次要过滤，不替代产业链和基本面验证。",
                },
                "catalyst": supp.get("catalysts", []) + [item.get("title") for item in research_reports[:2] if item.get("title")],
                "risk": supp.get("risks", []) + (["龙虎榜/资金流为空，短线资金确认不足"] if not fund_flow_rows and not dragon_rows else []),
                "a_stock_data_coverage": {
                    "announcements": len(announcements),
                    "fund_flow": len(fund_flow_rows),
                    "dragon_tiger": len(dragon_rows),
                    "financial_indicator_periods": len(indicators),
                    "research_reports": len(research_reports),
                },
                "public_data": supp,
            }
        )
    return out


def trade_decision_engine(stock_reports: list[dict[str, Any]], chain: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    decisions = []
    for item in stock_reports:
        conditions = {
            "clear_thesis": chain.get("selected_theme") != "unknown",
            "public_evidence": bool(chain.get("supporting_public_items")),
            "valuation_not_extreme": item.get("valuation", {}).get("band") != "high",
            "technical_not_broken": item.get("technical", {}).get("score", 0) >= 2,
            "risk_reward_ok": item.get("valuation", {}).get("score", 0) >= 3,
        }
        passed = sum(1 for ok in conditions.values() if ok)
        action = "watch"
        if passed >= 5 and review.get("decision") == "watchlist_candidate":
            action = "paper_candidate"
        elif not conditions["valuation_not_extreme"] or not conditions["technical_not_broken"]:
            action = "reject_or_wait"
        decisions.append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "action": action,
                "passed_conditions": passed,
                "conditions": conditions,
                "six_questions": [
                    "买的是什么产业链环节？",
                    "需求证据来自哪里？",
                    "卡口是否真实存在？",
                    "A股收入/订单暴露是否可验证？",
                    "估值和赔率是否足够？",
                    "什么证据出现就退出？",
                ],
                "min_risk_reward": 2.0,
            }
        )
    return {"stage": "trade-decision-engine", "decisions": decisions}


def portfolio_analytics(portfolio_state: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    positions = portfolio_state.get("positions", [])
    reviews = portfolio_state.get("reviews", [])
    candidates = [item for item in decisions.get("decisions", []) if item.get("action") == "paper_candidate"]
    rejected = [item for item in decisions.get("decisions", []) if item.get("action") == "reject_or_wait"]
    return {
        "stage": "portfolio-analytics",
        "cash": portfolio_state.get("cash"),
        "position_count": len(positions),
        "review_count": len(reviews),
        "new_paper_candidates": candidates,
        "rejected_or_wait": rejected,
        "reviewer_note": "盈利的交易也可能是坏交易；本轮先复盘判断质量，不做真实交易。",
    }


def build_research_pipeline(root: Path, payload_base: dict[str, Any], supplements: dict[str, dict[str, Any]], portfolio_state: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    scanned = news_scanner(payload_base.get("news", {}), payload_base.get("industry_reports", []))
    read = article_reader(scanned)
    scoring = score_hot_industries(read)
    chain = run_industry_chain_mapper(root, scoring, read, payload_base)
    stocks = stock_analyzer(payload_base.get("a_share_quotes", []), supplements)
    decisions = trade_decision_engine(stocks, chain, review)
    portfolio = portfolio_analytics(portfolio_state, decisions)
    return {
        "news_scanner": scanned,
        "article_reader": read,
        "hotspot_scoring": scoring,
        "selected_industry_chain": chain,
        "stock_analyzer": stocks,
        "trade_decision_engine": decisions,
        "portfolio_analytics": portfolio,
        "skills_used": [
            "news-scanner",
            "article-reader",
            "industry-chain-analysis",
            "stock-analyzer",
            "valuation-calculator",
            "technical-analyzer",
            "trade-decision-engine",
            "portfolio-analytics",
            "trade-reviewer",
        ],
    }
