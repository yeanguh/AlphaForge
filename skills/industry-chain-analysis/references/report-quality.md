# Report Quality Gate

Use this reference whenever the output is a formal report or an archived
`reports/industry/<topic>-<date>/` artifact. The goal is to make the final
document stable, evidence-grounded, visually readable, and useful for investment
opportunity discovery.

> **路径说明**:本文档中的 `reports/industry/<topic>-<date>/` 仅为 legacy / 独立快照示例。research-os loop 内生成的 canonical 研报落点是 `reports/themes/<theme>/report.md`(方案 A),见 `SKILL.md` 的报告产物规则;⛔ 不要把 loop 产物写回 `reports/industry/`。

## Quality Principles

1. **Stable structure before style.** A reader should always know where to find
   the conclusion, boundary, chain map, upstream inputs, value distribution,
   company mapping, opportunity view, risks, and evidence caveats.
2. **Evidence strength before confidence language.** Strong statements require
   filings, official/company releases, standards, or reputable current sources.
   Public data adapters are supporting evidence, not proof of business exposure.
3. **Visuals should clarify hierarchy.** At least one rendered Chinese vertical
   industry-chain diagram is expected in Report mode for hardware, industrial,
   energy, electronics, communications, AI infrastructure, and other physical
   chains.
4. **Investment opportunities must be linked to chain position.** Do not list
   stocks because they are popular. Separate direct core beneficiaries, key
   technology challengers, important suppliers, adjacent beneficiaries, and
   concept-only/watchlist names.
5. **Uncertainty should be explicit.** Use `未披露`, `待验证`, `间接受益`, or
   `数据不足` when evidence is weak. This improves trust more than pretending
   precision.
6. **Opportunities need a table, not only prose.** The investment section should
   contain either the non-trading opportunity table or the trading follow-through
   table so the reader can compare exposure, catalyst, validation milestone, and
   risk across companies.

## Required Reader-Facing Structure

Report mode should include these sections in this order. Chapter names may be
adapted to the industry, but the logical function should remain.

| Order | Section Function | Must Answer |
| --- | --- | --- |
| 0 | 核心结论 | What is the chain-level answer and why does it matter? |
| 1 | 研究对象、边界与口径 | What is included, excluded, and how exposure is judged? |
| 2 | 行业背景与需求驱动 | Who pays, why now, and what changes demand? |
| 3 | 产业链全景图谱 | How do upstream, midstream, downstream, adjacent links connect? |
| 4 | 上游材料、部件与制程要素挖掘 | What does the chain buy, consume, depend on, or get constrained by? |
| 5 | 产业链核心环节价值分布 | Where do BOM cost, value, scarcity, and bargaining power sit? |
| 6 | 竞争格局与核心壁垒 | Who leads, what is hard, and what can be substituted? |
| 7 | A股公司映射与核心地位判断 | Which companies have real operating exposure and how strong is it? |
| 8 | 投资线索/交易跟踪 | Which chain positions become investable opportunities? |
| 9 | 催化因素与产业传导路径 | What events move which chain links and companies? |
| 10 | 风险提示 | What breaks the thesis? |
| 11 | 数据来源、证据强度与待核验事项 | Which claims are strong, weak, or still pending? |

If the user did not ask for trading indicators, section 8 should still discuss
investment opportunity types and beneficiary ranking, but avoid buy zones,
targets, or trading language.

## Evidence Confidence Rubric

Use the following labels consistently in source summaries and company remarks.

| Confidence | Evidence Pattern | Use In Conclusions |
| --- | --- | --- |
| High | Filings, official reports, company IR/product docs, standards, SEC filings, regulator/association data | Can support decisive chain/company claims |
| Medium-High | Reputable industry report, specialist conference material, credible news with named source | Can support trend and route judgments |
| Medium | Public data adapter, market-data snapshot, third-party estimate, company website without quantitative proof | Use as support; avoid precise exposure claims |
| Low | Logical inference, concept-board label, unsourced media summary, weak keyword match | Discovery only; mark `待验证` |

When exact `产业占比` is unavailable, state the closest verified proxy:

- revenue share,
- segment revenue share,
- capacity or shipment share,
- product confirmed but proportion undisclosed,
- order/customer disclosure,
- qualitative exposure only.

Never invent a percentage to make a table look complete.

## Investment Opportunity Mining

For each important chain link, answer these four questions before naming stocks:

1. **Scarcity:** Is the constraint demand, capacity, materials, process, customer
   validation, patents, equipment, standards, or engineering delivery?
2. **Value capture:** Does the link capture margin, pass through cost, lock in
   customers, or benefit from scale?
3. **Listed exposure:** Which A-share companies disclose direct products,
   revenue, orders, customers, capacity, or certifications in this link?
4. **Catalyst path:** What event turns chain logic into financial results:
   orders, price, utilization, capex, policy, standard adoption, or customer
   validation?

Separate opportunities into:

| Category | Meaning | Report Treatment |
| --- | --- | --- |
| 核心环节龙头 | Direct exposure and leading position in a high-value or constrained link | Main beneficiary list |
| 关键技术突破者 | Solves bottleneck but commercialization may still be ramping | High-upside watchlist with validation milestones |
| 重要配套/高弹性 | Supplies key material, component, equipment, or service | Rank by customer proof and revenue elasticity |
| 相邻基础设施 | Benefits from same demand driver but is not part of the core product chain | Separate from core ranking |
| 间接受益/待验证概念 | Weak or unproven exposure | Keep as caveat or watchlist, not a core opportunity |

Report mode must include one of these table forms:

| Opportunity Type | Chain Logic | Representative A-share Companies | Validation Milestones | Risk |
| --- | --- | --- | --- | --- |
| 核心环节龙头 | ... | ... | ... | ... |

or, when the user asks for trading indicators:

| 公司 | 代码 | 产业链结论 | 财务质量 | 当前估值 | 技术面/趋势 | 买点区间 | 止损/失效条件 | 目标价/空间 | 综合判断 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Visual Quality Checklist

For report figures:

- Use Chinese labels in Chinese reports.
- Use a vertical top-to-bottom main chain by default.
- Keep main chain centered; side lanes are for adjacent infrastructure,
  substitutes, commodity background, or risks.
- Use layer headers for upstream, midstream, downstream.
- Keep nodes short enough to read in PNG.
- Save both SVG and PNG under an `assets/` subdirectory beside `report.md`.
- Reference local images with an `assets/...` relative Markdown path such as
  `![产业链图谱](assets/chain.png)`; do not use absolute filesystem paths,
  `file://` URLs, remote URLs, or same-directory bare image filenames in
  `report.md`.
- Inspect the PNG or at least verify it can be opened as an image and is large
  enough to read. The machine gate expects local figures to be at least
  `900 x 600` pixels.

## Machine Gate

After generating a report artifact, run:

```bash
/usr/local/bin/uv run python .agents/skills/industry-chain-analysis/scripts/report_quality.py \
  reports/industry/<topic>-<YYYY-MM-DD>/report.md \
  --output reports/industry/<topic>-<YYYY-MM-DD>/quality_report.json
```

If it fails, fix the report before delivery. Common fixes:

- Missing section: revise `generate_report.py`/template, not only the output file.
- Missing image: generate SVG+PNG under `assets/` and reference the PNG with an
  `assets/...` relative path from `report.md`.
- Invalid or tiny image: export a real PNG from the SVG and verify the rendered
  output before delivery.
- Weak source base: add filing/company/official/association evidence or mark
  conclusions as lower confidence.
- Missing opportunity framing: add beneficiary categories and catalyst paths.
- Missing opportunity table: add either the non-trading opportunity table or the
  trading follow-through table; prose alone is not enough.
- Missing source summary: add a compact claim-level source table in section 11
  with columns `结论/数据、来源、日期、置信度`.
- Adapter logs in report: move runtime details to `source_data.json`.
