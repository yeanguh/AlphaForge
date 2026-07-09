from __future__ import annotations

from collections import Counter
from typing import Any


KEYWORD_BUCKETS = {
    "ai": ["AI", "人工智能", "大模型", "算力", "智能体", "机器人"],
    "semiconductor": ["半导体", "芯片", "晶圆", "封装", "先进制程", "存储"],
    "new_energy": ["新能源", "光伏", "风电", "储能", "锂电", "电池"],
    "auto": ["汽车", "智能驾驶", "新能源车", "车载", "零部件"],
    "medical": ["医药", "医疗", "创新药", "器械", "生物"],
    "equipment": ["设备", "工艺", "材料", "机床", "工业"],
}


def analyze_industry_reports(reports: list[dict[str, Any]], headlines: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [r.get("title", "") for r in reports] + [h.get("title", "") for h in headlines]
    bucket_hits: Counter[str] = Counter()
    for text in texts:
        for bucket, keywords in KEYWORD_BUCKETS.items():
            if any(keyword.lower() in text.lower() for keyword in keywords):
                bucket_hits[bucket] += 1

    industries = Counter(r.get("industry_name") or "unknown" for r in reports if r.get("industry_name"))
    orgs = Counter(r.get("org") or "unknown" for r in reports if r.get("org"))
    top_reports = reports[:8]
    catalysts = []
    for report in top_reports:
        catalysts.append(
            {
                "source": "eastmoney_industry_report",
                "industry": report.get("industry_name"),
                "title": report.get("title", ""),
                "publish_date": report.get("publish_date"),
                "hypothesis": f"{report.get('industry_name') or '相关行业'}出现新的机构研究信号，需要验证需求、上游卡口和A股真实暴露。",
            }
        )

    return {
        "methodology": "industry-chain-analysis",
        "report_count": len(reports),
        "headline_count": len(headlines),
        "top_theme_buckets": bucket_hits.most_common(8),
        "top_industries": industries.most_common(8),
        "top_orgs": orgs.most_common(8),
        "catalysts": catalysts,
        "next_actions": [
            "从终端需求向上回溯，确认增长是否来自真实订单、政策或资本开支。",
            "拆上中下游，优先验证材料、设备、工艺、资源等稀缺卡口。",
            "把报告提到的行业映射到A股公司真实收入/订单暴露，剔除纯概念标签。",
            "为每个候选主题补充反证条件和退出条件。",
        ],
    }
