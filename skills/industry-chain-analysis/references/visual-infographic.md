# Visual Infographic Style

Use this reference when a Report-mode output needs a professional analysis
figure, especially when the user asks for 更专业的图、投研图、信息图、一图看懂,
or provides a visual sample. The goal is to turn the industry-chain analysis
into a dense but readable research infographic, not a decorative flow chart.

## Analytical Angle

The figure should answer six questions in one screen:

1. 为什么现在看这个产业链：AI耗材、政策、价格、国产替代、技术迭代、供需错配、资本开支, or another trigger.
2. 量价怎么变：usage/shipment/capacity multiplier, unit-price change, BOM/cost change, margin or value-pool expansion.
3. 链条处在哪个阶段：early adoption, capacity ramp, localization window, route switching, price inflection, inventory cycle.
4. 谁在关键环节：global leaders, domestic leaders, A-share direct exposure, materials/equipment bottleneck companies.
5. 关键时间表是什么：current year shipments/orders, next product generation, localization milestone, market-size target.
6. 结论是什么：the single investable thesis plus the main caveat.

Do not draw only upstream/midstream/downstream boxes. The visual must show
drivers, quantitative anchors, company positioning, and timing.

## Default Layout

Use a portrait canvas, usually `1500 x 2100` or `1600 x 2200`.

Required blocks:

| Block | Position | Purpose |
| --- | --- | --- |
| Title band | Top | `1分钟拆解产业链：<主题>` or `<主题>产业链投研拆解` |
| Trigger cards | Top row | 3-5 cards with large numbers/keywords, e.g. `用量6倍`, `单价10倍`, `市场400亿`, `国产替代` |
| Central visual | Center | Product/process schematic or chain focal object. Use simple SVG illustration, icons, or a product-like technical drawing, not an abstract decorative blob. |
| Left analysis rail | Left side | 量价拆解、BOM/成本、上游材料、产业阶段、壁垒 |
| Right analysis rail | Right side | 应用主线、需求驱动、国产替代窗口、风险/替代路线 |
| Company cards | Below center | 4-8 representative companies grouped by role: 龙头、材料、设备、挑战者、待验证 |
| Core drivers | Bottom-left | 5-7 bullet drivers, each short and quantitative where possible |
| Timeline | Bottom-right | 4-7 dated milestones or forecast anchors |
| Conclusion strip | Bottom | One decisive sentence: chain thesis + value driver + caveat |
| Source note | Footer | Compact source note, no raw adapter logs |

## Visual Rules

- Use a restrained research palette: muted blue/green/purple/orange plus off-white background. Avoid one-color purple gradients.
- Use thick section borders and card grouping so hierarchy is clear at a glance.
- Put the largest numeric facts in the top trigger cards, not buried in tables.
- Keep each card to 1 bold keyword/number plus 2-4 short lines.
- Use arrows sparingly: 2-4 callout arrows from central visual to `量价齐升`, `国产替代`, `核心卡点`, or `成本传导`.
- Prefer concise Chinese labels. English technical terms can appear in sublabels when they are industry-standard, e.g. HBM, CoWoS, ABF, DSP.
- Include company cards only when exposure evidence exists; weak names should be labeled `待验证` or omitted.
- Keep all visual text readable after PNG export. No text smaller than 12px on a 1500px-wide canvas; main cards should use 18-28px.
- Render SVG+PNG and visually inspect the PNG. Check for Chinese font fallback, text overflow, overlapping arrows, and unreadable dense cards.

## Data Rules

- Every large number in the infographic must be supported by `source_data.json`
  or marked as `定性/待核验`. Do not invent precise multipliers.
- If credible numeric ranges are unavailable, use qualitative anchors such as
  `定性高`, `认证周期长`, `国产化率待核验`, and put the missing-data caveat in the report.
- Use the figure to summarize the report, not to introduce unsupported claims.
- Keep adapter failures, endpoint names, retries, and runtime details out of the
  image and out of `report.md`.

## Figure Selection

For Report mode, prefer two complementary figures when the report is important:

1. `产业链投研拆解图`: the professional infographic described above, used as the first figure.
2. `产业链全景图谱`: a cleaner upstream/midstream/downstream hierarchy map, used when the chain has many material or equipment links.

If only one figure is allowed, use the infographic style and embed a compact
vertical chain map inside the central or side section.

## Output Naming

Save under the report's `assets/` directory:

- `<topic>-industry-infographic.svg`
- `<topic>-industry-infographic.png`

Markdown reference must be relative:

```markdown
![产业链投研拆解图](assets/<topic>-industry-infographic.png)
```
