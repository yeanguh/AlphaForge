# Report Template

Use this structure for industry upstream/downstream analysis. Adapt section names to the target industry, but keep the reader-facing research-report sequence: conclusion first, boundary next, chain map and evidence in the body, then company mapping, trading follow-through when requested, catalysts, risks, and a compact source/missing-data summary.

## Light Mode Template

```markdown
## 核心结论
- ...

## 上下游结构
| 环节 | 细分领域 | 关键价值/壁垒 | 代表A股公司 |
| --- | --- | --- | --- |

## 需要继续核验
- ...
```

## Standard Mode Template

```markdown
## 核心结论
- ...

## 产业链图谱
| 环节 | 细分领域 | 价值占比/成本占比 | 技术壁垒 | 卡脖子程度 | 代表A股公司 |
| --- | --- | --- | --- | --- | --- |

## 上游材料与部件发现
适用于硬件、半导体、电子、通信、能源装备、汽车、机器人、医疗器械、化工和大宗商品等有物理输入的主题；如果不适用，说明不纳入原因。

| 上游层级 | 细分材料/部件 | 对目标产业的作用 | 价值/稀缺性 | 卡脖子程度 | A股候选 | 纳入主线判断 |
| --- | --- | --- | --- | --- | --- | --- |
| Product BOM | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |
| Process materials | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |
| Board/package materials | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |
| Resource/feedstock | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |
| Adjacent infrastructure | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |

## 产业链核心环节价值分布
该模块用于回答“整个产业链中，哪些环节占成本/价值、壁垒在哪里、A股谁代表该环节”。它是环节维度，不替代后续公司维度的 9 列映射表。

| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 上游 | ... | ... | ... | High/Medium/Low/None | ... | 核心/重要/间接/待验证 | BOM拆分/分部收入/市占率/定性估计 |

## 关键环节公司映射
使用统一的 9 列口径（与 `a-share-screening.md` 的公司映射表一致）：

| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 风险与待核验
- ...

## 可选：交易与估值跟进
| 公司 | 代码 | 产业链结论 | 财务质量 | 估值水平 | 技术面/趋势 | 买点区间 | 目标价/空间 | 风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

## Report Mode Structure

Report mode should read like a finished research memo, not a generation log. Borrow the structure and pacing of formal industry reports: a compact cover/header, executive summary, research boundary, core chain map, evidence-backed sections, conclusion and risk closure. Do not expose process phrases such as "本次新增", "上一版", "根据用户要求补充", or "以下为重新整理".

### Title

`# <行业/主题/产品>上下游产业链与A股公司分析报告`

Add:

- Analysis date
- Scope: China / global / specified market
- Target: product, technology, commodity, or policy theme
- Output directory and figure references only when useful to the reader

### Recommended Report Flow

Use the following chapter order by default. Section names can be localized to the industry, and small sections can be merged when evidence is thin, but do not omit the logical function of each section.

```markdown
# <行业/主题/产品>上下游产业链与A股公司分析报告

> 分析日期：YYYY-MM-DD
> 研究范围：中国/全球/指定市场；A股映射口径：...

## 0. 核心结论
## 1. 研究对象、边界与口径
## 2. 行业背景与需求驱动
## 3. 产业链全景图谱
## 4. 上游材料、部件与制程要素挖掘
## 5. 产业链核心环节价值分布
## 6. 竞争格局与核心壁垒
## 7. A股公司映射与核心地位判断
## 8. 投资线索、交易跟踪与目标价情景
## 9. 催化因素与产业传导路径
## 10. 风险提示
## 11. 数据来源、证据强度与待核验事项
```

### 0. Executive Conclusion / 核心结论

Provide 3-6 bullets:

- Chain-level conclusion
- Highest-value or most constrained sub-segments
- Main demand driver
- Main supply bottleneck
- A-share companies with strongest direct exposure
- Key risk or uncertainty

Keep this section decisive. Each bullet should answer "so what": why this link matters, which company is truly exposed, or which risk can break the thesis.

### 1. Industry Boundary / 研究对象、边界与口径

| Item | Definition |
| --- | --- |
| Analysis object | ... |
| Included links | ... |
| Excluded or weakly related links | ... |
| Core indicators | Price, volume, capacity, utilization, margin,国产化率, policy milestones |
| A-share mapping scope | Main board / STAR / ChiNext / BSE; direct exposure only or including adjacent links |
| Evidence hierarchy | Filings > official/company releases > industry association/statistics > market-data adapters > media/third-party estimates |

When a theme has adjacent but non-core links, list them here instead of burying them later. This prevents concept-only companies from being promoted into the core ranking.

### 2. Industry Background and Demand Drivers / 行业背景与需求驱动

Cover only drivers that affect the chain:

- End-use scenarios and why demand is changing now
- Capacity, price, inventory, or policy indicators that show the cycle position
- Technology route shifts, substitution, or export-control constraints
- Why this industry chain matters for A-share mapping

Use a compact table when multiple drivers exist:

| Driver | Direction | Affected Link | Transmission Logic | Evidence Strength |
| --- | --- | --- | --- | --- |
| ... | Positive/Negative | ... | ... | High/Medium/Low |

### 3. Upstream/Midstream/Downstream Chain Map / 产业链全景图谱

Use `fireworks-tech-graph` for report figures. Generate local SVG and PNG files under an `assets/` subdirectory, validate/export with `rsvg-convert` or the available renderer fallback, then reference the PNG in Markdown:

```markdown
![产业链图谱](assets/industry-chain-map.png)
```

Only use Mermaid for quick scratch notes or when the user explicitly asks for Mermaid source; do not leave Mermaid as the final report chart when a rendered analysis figure is expected.

#### 产业链投研信息图绘制规范

When the report is meant to be shared, when the user asks for a more
professional figure, or when the user provides an infographic sample, read
`visual-infographic.md` and make the first figure a professional research
infographic rather than a plain flow chart.

Required content:

- Title band: `1分钟拆解产业链：<主题>` or `<主题>产业链投研拆解`.
- Top trigger cards: 3-5 cards with the largest quantified claims or strongest drivers, such as `用量提升`, `单价提升`, `市场空间`, `国产替代`, `技术迭代`.
- Central visual: a simple product/process/chain focal illustration. It should help readers understand the physical product, process, or value focus.
- Side analysis rails: left side for量价拆解、产业阶段、BOM/材料/工艺; right side for应用主线、需求驱动、国产替代、风险或替代路线.
- Company cards: 4-8 representative A-share companies grouped by role, e.g. 龙头、材料、设备、挑战者、待验证.
- Bottom blocks: `核心驱动` and `关键时间表`, followed by one conclusion strip.
- Footer: compact source note only; no raw adapter logs.

The infographic must contain at least one of each: quantitative anchor, chain
stage judgment, company-position judgment, timing/catalyst, and risk/caveat.
If exact numbers are unavailable, mark the claim as定性 or待核验 instead of
inventing precision.

#### 产业链全景图谱绘制规范

Default to a **Chinese, vertical, top-to-bottom** full-chain map for Chinese reports. The figure should make the hierarchy obvious before readers look at tables.

Required layout:

- Canvas: portrait or tall canvas, usually `1200 x 1600`, `1400 x 1800`, or another tall ratio. Use horizontal layout only when the user asks for it.
- Direction: draw the main chain from top to bottom: `上游资源/原材料/设备 -> 中游制造/集成/平台 -> 下游客户/应用/渠道`.
- Layer headers: each upstream/midstream/downstream block must have a visible Chinese layer header. For hardware themes, split upstream into `资源/化工原料`, `过程材料/设备`, `核心零部件`, and `板级/封装材料` when relevant.
- Main vs adjacent: keep the main chain in the center column. Put `相邻基础设施`, `替代技术路线`, `商品背景`, and `待验证链路` in side lanes with dashed borders or dashed arrows; do not mix them into the core chain.
- Node density: keep each layer to 3-6 nodes. If a layer has more nodes, group them by category or split into a second figure.
- Labels: use concise Chinese node names, with optional one-line Chinese sublabels for function or A-share examples. Avoid English-only labels in Chinese reports.
- Arrows: downward blue arrows for 主链传导; green arrows for 上游输入; purple dashed arrows for 相邻链路; orange/red arrows for 约束/风险. Add a legend.
- Font: embed a CJK-friendly font stack in SVG: `PingFang SC`, `Microsoft YaHei`, `Noto Sans CJK SC`, `Heiti SC`, `Arial`, `sans-serif`. After PNG export, visually inspect the image; if Chinese renders as square tofu, switch renderer/font strategy before finalizing.
- Readability: no overlapping arrows or text; arrow labels need a light background; each node should have at least 8px padding and stable dimensions.
- Image paths: Markdown reports stored in `reports/industry/<topic>-<YYYY-MM-DD>/`
  must reference local figures with `assets/...` relative paths, not absolute
  filesystem paths, `file://` URLs, remote URLs, or same-directory bare filenames.
  Keep all report static resources under the local `assets/` folder.

Then explain each link:

| Link | Sub-segment | Role | Key Inputs | Key Outputs | Value/Cost Driver | Representative A-share Companies |
| --- | --- | --- | --- | --- | --- | --- |
| Upstream | ... | ... | ... | ... | ... | ... |
| Midstream | ... | ... | ... | ... | ... | ... |
| Downstream | ... | ... | ... | ... | ... | ... |

The chain map should distinguish the main chain from adjacent chains. Use separate labels such as "主链", "关键上游", "相邻基础设施", and "商品背景" when needed.

### 4. Upstream Material and Component Discovery / 上游材料、部件与制程要素挖掘

Include this section for Standard/Report mode when the target is a physical product, hardware system, commodity, chemical, semiconductor, electronics, energy equipment, autos, robotics, aerospace, medical device, or communications theme.

| Upstream Layer | Material/Component | Transmission to Target Industry | Value/Scarcity | Bottleneck Relevance | Representative A-share Candidates | Mainline Judgment |
| --- | --- | --- | --- | --- | --- | --- |
| Product BOM | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |
| Process materials | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |
| Board/package materials | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |
| Resource/feedstock | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |
| Adjacent infrastructure | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |

Explain why named materials or obvious upstream links are included or excluded. Do not mix adjacent infrastructure companies into the core company ranking unless the transmission path is direct.

For hardware and semiconductor topics, explicitly scan the five layers from `upstream-discovery.md`: Product BOM, Process materials, Board/package materials, Resource/feedstock, and Adjacent infrastructure. If a layer is not relevant, say why in one short sentence.

### 5. Core Chain-Link Value Distribution / 产业链核心环节价值分布

This section should be a link-level value map. It answers where BOM cost, value share, bargaining power, and bottlenecks sit before the report ranks companies. Use it for Standard and Report outputs whenever the target has material cost/value distribution across links.

| 产业链环节 | 细分领域/关键产品 | BOM成本占比/价值占比 | 核心技术壁垒 | 卡脖子程度 | 代表A股公司 | 公司环节地位 | 证据口径/备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ... | ... | High/Medium/Low | ... | High/Medium/Low | ... | ... |

State whether the BOM cost/value share is sourced from BOM decomposition, company segment revenue, market-share estimates, shipment/capacity, gross-margin comparison, or qualitative industry evidence. If there is no reliable percentage, write a range, "未披露", or "定性高/中/低", and explain the evidence basis.

For each key sub-segment, add a short paragraph that explains:

- Why value concentrates there
- Whether the bottleneck is resource, equipment, process know-how, certification/customer validation, or scale
- Which A-share companies are direct beneficiaries versus indirect suppliers
- Why a representative company is core, important, indirect, or only a watchlist candidate in that chain link

### 6. Competition and Core Barriers / 竞争格局与核心壁垒

Cover:

- Supply capacity, utilization, inventory, and expansion plans
- Technical routes and substitution risk
- Cost curve, scale effects, and pricing power
- Main competitors and entry barriers
- Localization rate, import substitution gap, and whether there is a卡脖子 issue

Recommended table:

| Link/Sub-segment | Global Leaders | China/A-share Leaders | Barrier Type | Localization Status | Core Bottleneck |
| --- | --- | --- | --- | --- | --- |
| ... | ... | ... | Resource/Process/Equipment/Customer/Scale | ... | ... |

### 7. A-Share Company Mapping / A股公司映射与核心地位判断

使用统一的 9 列口径（与 `a-share-screening.md` 的公司映射表一致）：

| 公司 | 代码 | 环节 | 细分领域 | 产业占比/暴露度 | 核心技术/产品 | 卡脖子相关性 | 环节地位 | 证据与备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ... | ... | 上游/中游/下游/设备/材料/服务/渠道/基础设施 | ... | 营收占比/产能份额/市占率/未披露 | ... | High/Medium/Low/None | 核心/重要/间接/待验证概念 | ... |

Classify companies into:

- 核心环节龙头
- 关键技术突破者
- 重要配套或高弹性公司
- 间接相关公司
- 待验证概念公司

After the table, write 2-4 paragraphs that separate investable chain exposure from market hype. If exact exposure is unavailable, use "未披露" and explain the nearest available proxy instead of inventing a percentage.

### 8. Investment Opportunity View / 投资线索、交易跟踪与目标价情景

Always include an investment-opportunity view in Report mode. If the user did
not ask for trading indicators, keep it as产业投资线索: beneficiary categories,
scarcity, value-capture logic, catalyst path, and validation milestones. This is
where the report turns the chain map into investable hypotheses without
overstating weak evidence.

For non-trading Report mode:

| Opportunity Type | Chain Logic | Representative A-share Companies | Validation Milestones | Risk |
| --- | --- | --- | --- | --- |
| 核心环节龙头 | Direct exposure in high-value/scarce link | ... | order/revenue/customer proof | ... |
| 关键技术突破者 | Bottleneck technology with commercialization ramp | ... | certification/yield/customer | ... |
| 重要配套/高弹性 | Supplies critical material/component/equipment | ... | volume/customer mix | ... |
| 相邻基础设施 | Benefits from same demand driver outside core chain | ... | project/order proof | ... |
| 待验证概念 | Weak evidence or market-label only | ... | exact product/revenue proof | ... |

Include buy zones, technical analysis, target prices, or operation suggestions
only when the user asks for买点、技术面、目标价、估值、操作建议, or stock-level
opportunity. In that case, use `providers/open_source/a_stock_data.py` for fundamentals,
valuation quality, and technical setup, then use `providers/open_source/wen_cai.py` or approved public
market-data adapters for latest quote, PE/PB/PS, technical setup, buy point, and
target-price space.

For trading add-on:

| Company | Ticker | Chain Conclusion | Financial Quality | Current Valuation | Technical/Price Setup | Buy Zone | Stop/Invalidation | Target/Space | Overall View |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ... | ... | Core/Important/Indirect | ... | ... | ... | ... | ... | ... | ... |

Keep this section subordinate to the chain conclusion: do not upgrade a weak chain-exposure company only because its price setup is attractive.

Use scenario language for target prices when source confidence is limited:

- Bear/base/bull assumptions
- Valuation method or comparable range
- Invalidation point
- Catalyst needed for the target to become credible

### 9. Catalysts and Transmission Path / 催化因素与产业传导路径

| Catalyst | Direction | Affected Link/Sub-segment | Transmission Path | A-share Companies Affected | Evidence Strength | Time Horizon |
| --- | --- | --- | --- | --- | --- | --- |
| ... | Positive/Negative | ... | ... | ... | High/Medium/Low | Short/Medium/Long |

Prefer a "catalyst -> link -> company exposure" chain instead of listing news. This keeps the report anchored in industry structure.

### 10. Risks / 风险提示

List concrete risks:

- Demand miss
- Supply expansion or overcapacity
- Price/spread reversal
- Technology route change
- Import substitution slower than expected
- Company exposure weaker than expected
- Customer concentration or order volatility
- Policy or export-control risk
- Valuation and market-liquidity risk if discussing A-shares

### 11. Source Summary and Missing Data / 数据来源、证据强度与待核验事项

| Claim | Source | Date | Confidence |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

End with exact missing data, such as segment revenue unavailable, capacity undisclosed, patent/customer evidence missing, or market-share estimates needing confirmation.
This table is required in Report mode: prose caveats without a claim-level
source table are not enough for high-confidence output.

Do not include "公共数据适配器留痕" or raw AkShare/baostock/adata call logs in the reader-facing report. Keep endpoint failures, health-check results, queried functions, row counts, retries, and runtime diagnostics in `source_data.json`. Mention adapter issues in the report only when they materially reduce confidence in a conclusion, and then describe the effect briefly rather than showing the raw call log.

## Quality Gate

After writing `report.md`, run the machine quality gate and save the output:

```bash
/usr/local/bin/uv run python .agents/skills/industry-chain-analysis/scripts/report_quality.py \
  reports/industry/<topic>-<YYYY-MM-DD>/report.md \
  --output reports/industry/<topic>-<YYYY-MM-DD>/quality_report.json
```

The report should pass before delivery. If it fails, fix the generation script
or report source rather than appending a workaround note. The gate checks stable
section structure, rendered image assets, absence of raw runtime logs, canonical
upstream/value/company tables, source-trail confidence, and investment
opportunity framing. It also checks that the investment section contains a
comparison table, section 11 contains a claim-level source table, local image
references in the Markdown report are relative paths, and local image files can
be opened at readable dimensions.
