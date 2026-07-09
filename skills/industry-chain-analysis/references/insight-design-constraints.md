# Insight Design Constraints

This reference holds the mode, scoring, output, and error-handling constraints for the A-share industry-chain-analysis skill. Keep behavior tied to data this repository can actually produce; do not assume any external vendor dataset or platform-specific behavior unless the current repository explicitly provides it.

## Mode Discipline

- Select Light, Standard, Report, or Trading add-on before collecting data.
- Do not silently upgrade mode. If the user asks "分析一下" or "对比一下", use Standard unless they explicitly ask for a report/document/material.
- Light and Standard modes output Markdown only unless the user explicitly asks for a chart/diagram. When a chart is requested, use `fireworks-tech-graph` and keep the answer focused on generated local SVG/PNG paths.
- Report mode in this skill defaults to a single Markdown research report unless the user explicitly requests HTML/web rendering. Report figures should be generated with `fireworks-tech-graph` as local SVG+PNG assets.
- Trading add-on is subordinate to the chain conclusion and cannot promote a weak-exposure company into a core industry beneficiary.

## Minimal Data Collection

- Start with the smallest evidence set that can answer the question.
- Avoid broad exploratory pulls. One useful board/industry pull plus one company/exposure pull is better than many unconnected tables.
- Do not fetch policy, news, or company-detail lists unless the conclusion depends on them.
- Reuse local cached data and already fetched DataFrames before calling another public endpoint.

## Output Order

Every response or report should follow:

1. Conclusion first.
2. Evidence table or source-backed chain map.
3. Business meaning: what the structure implies for value, bottlenecks, companies, catalysts, or risks.

Do not return only a raw list, only a table, or only narrative without evidence.

## Professional Figure Standard

When a Report-mode output includes figures, a plain upstream/midstream/downstream
box diagram is not enough for a shareable report. Prefer a professional
投研信息图 when the topic has clear drivers, quantities, prices, substitution
logic, catalysts, or company mapping.

The primary figure should combine:

- top numeric or keyword trigger cards,
- a central product/process/chain visual,
- side rails for量价拆解、应用主线、国产替代、风险,
- company role cards,
- a key driver block,
- a milestone timeline,
- and a bottom conclusion strip.

Use the pure vertical chain map as a secondary figure or as a compact sub-block
inside the infographic. Do not let the image become only a decorative flow
chart; every visual block should carry an analytical claim that is supported
or explicitly marked待核验.

## Ranking and Scoring

When the user asks for "最热 / Top N / 排名 / 筛选 / 推荐 / 优势 / 短板 / 核心公司", use a multi-factor view instead of a single metric.

For industry or company ranking, prefer these dimensions:

| Dimension | Examples |
| --- | --- |
| Exposure | Revenue/proportion, capacity, orders, products, customers |
| Position | Market share, leader/challenger/supplier, customer validation |
| Technology | Patents, process capability, 国产替代, scarce know-how |
| Business quality | Growth, margin, ROE, debt, cash flow |
| Market confirmation | Fund flow, volume/price trend, valuation, sentiment |

Use a single ranking only when the candidate set is small or the user asks for one list. Otherwise separate "核心环节龙头", "关键技术突破者", "重要配套或高弹性公司", "间接相关", and "待验证概念".

## Error Handling

- On the first public-data error, inspect whether the issue is endpoint failure, code format, missing dependency, schema change, or empty result.
- Retry once only when the call is cheap and likely transient.
- On repeated failure, stop trying that endpoint, record the error, and switch data source.
- Never hide data gaps. Mark "未披露", "待验证", "接口失败", or "本地缓存口径" in the report.

## Report Maintenance

- If a report already exists and the user adds constraints, update the main report or generation script into a new complete version.
- Do not append process notes such as "本次新增" inside the reader-facing report unless placed in a separate run log or appendix requested by the user.
- Keep source trails and runtime issues in `source_data.json`. The reader-facing report should include only a compact "数据来源、证据强度与待核验事项" section, not public-data adapter logs.
