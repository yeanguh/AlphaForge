# A-Share Company Mapping and Trading Follow-Through

Use this reference when the user asks for A-share companies involved in key industry-chain links. Start with exposure, technology, and industry-position analysis. If the user asks for买点、技术面、目标价、估值、操作建议, add a stock-level follow-through section by using `providers/open_source/a_stock_data.py` and `providers/open_source/wen_cai.py`.

## Required Company Fields

For every A-share company included in the main table, collect or explicitly mark missing:

| Field | Meaning |
| --- | --- |
| Chain link | Upstream, midstream, downstream, equipment, material, software, service, channel, or infrastructure |
| Sub-segment | The precise细分领域, not only a broad theme |
| Exposure/proportion | Segment revenue share, product revenue share, capacity share, shipment share, market share, customer/order share, or "未披露" |
| Core technology/product | Patents, process, product line, equipment, material, software, certification, or customer-validated capability |
| 卡脖子 relevance | Whether the company addresses a domestic bottleneck, import substitution, scarce process, key material, high-end equipment, EDA/IP/core component, or other constrained link |
| Core position | Core leader, key challenger, important supplier, indirect participant, or concept-only |
| Evidence | Filing, annual report, prospectus, investor relations, order/customer disclosure, official website, or reputable third-party source |

## Exposure Strength

Classify exposure conservatively:

| Level | Meaning | Evidence Required |
| --- | --- | --- |
| Core leader | Company has direct, material exposure and leading share/technology/customer position in the sub-segment | Segment revenue/capacity/market-share evidence plus product or customer proof |
| Key challenger | Direct exposure with meaningful technology or growth, but leadership is not fully proven | Product/order/capacity evidence and credible growth signal |
| Important supplier | Supplies material, equipment, modules, software, or services to a key link | Explainable supplier relationship and disclosed product capability |
| Indirect participant | Benefits through adjacent or downstream relationship | Clear transmission path but limited direct exposure |
| Concept-only | Market label without confirmed operating exposure | Keep out of the main beneficiary list or mark as "待验证概念" |

## Proportion Rules

- Prefer disclosed segment revenue as a percentage of total revenue.
- If segment revenue is unavailable, use capacity share, shipment share, product mix, major-customer exposure, order amount, or market-share estimates.
- If only qualitative exposure exists, write "未披露；仅确认产品/业务涉及" and avoid ranking the company above firms with quantitative evidence.
- Never mix revenue share, capacity share, and market share in one ranking without labeling the metric.

## Core Technology and Bottleneck Rules

For each key sub-segment, ask:

- Is this link a high-value or high-cost part of the chain?
- Is the link constrained by foreign suppliers, equipment, materials, process know-how, patents, standards, or customer validation?
- Does the company own or commercialize a product that directly solves the bottleneck?
- Is the technology already in revenue, pilot validation, sample delivery, or still only R&D?
- Does the company have patents, certifications, major customers, yield/capacity data, or shipment proof?

Rate卡脖子 relevance as:

| Rating | Meaning |
| --- | --- |
| High | Directly addresses a scarce domestic bottleneck or high-end import-substitution link |
| Medium | Participates in an important technical link but bottleneck or leadership is partly unproven |
| Low | Related to ordinary supply, assembly, distribution, or non-core components |
| None | No meaningful bottleneck relevance |

## Output Tables

This skill uses two different tables for different modes. Do not mix them up:

### Chain Overview Table (Light mode)
Light mode uses a compact 4-column chain overview to summarize upstream/downstream structure at a glance. This is a structural, not per-company detail.

| 环节 | 细分领域 | 关键价值/壁垒 | 代表A股公司 |
| --- | --- | --- | --- |

- Use this table in Light mode when the user asks for a quick scan or a chain structure overview.
- Column 代表A股公司 lists 1-3 representative names per link; it is not a full company-mapping exercise.
- Do not add卡脖子 or core-position columns here — those belong to the full mapping table.

### Company Mapping Table (Standard / Report mode)
This is the single canonical per-company mapping table. Standard mode, Report mode section 7, and any detailed company output must use these exact 9 columns and Chinese headers; do not add, drop, or rename columns per mode.

| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Stock-Level Follow-Through

Use this section only after the chain map and company exposure table are complete.

### Skill Sequence

1. Use `providers/open_source/a_stock_data.py` to evaluate public fundamentals: profitability, growth, cash flow, debt, valuation, announcements, shareholder risks, and industry comparison where data is available.
2. Use `providers/open_source/a_stock_data.py` to fetch latest price and compute current PE/PB/PS, expected EPS valuation when available, comparable valuation, support/resistance, box structure, trend, and price/technical setup; use `providers/open_source/wen_cai.py` to cross-check research ratings, events, and business exposure.
3. Merge the outputs with this skill's chain-position judgment. A company with weak or indirect chain exposure should not receive an aggressive stock conclusion purely because its chart looks strong.

### Trading/Valuation Table

| 公司 | 代码 | 产业链结论 | 财务质量 | 当前估值 | 技术面/趋势 | 买点区间 | 止损/失效条件 | 目标价/空间 | 综合判断 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### Required Checks Before Buy Point or Target Price

- Latest quote, turnover, market cap, and recent price trend
- Current PE/PB/PS and industry comparable range
- Expected EPS or consensus estimate if using target valuation
- Support/resistance or moving-average structure
- Volume confirmation and fund-flow signal when available
- Fundamental risks from public provider evidence
- Institutional-trend gate: only promote a mapped company into an actionable opportunity row when `institutional_trend_score >= 3.5` on the repository's shared 0-5 rubric (14-day K-line structure, MA5/MA10/MA20/MA50 alignment, small-candle grind-up, healthy pullback volume, and broad-market trend context). This is the same beneficiary gate used by `daily-a-share-news-impact`; below 3.5, keep the name watchlist-level and state why.

If price, volume, or financial data is unavailable, replace buy/target fields with "数据不足" and give only a watchlist-level conclusion.
