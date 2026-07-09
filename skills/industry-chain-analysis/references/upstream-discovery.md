# Upstream Discovery

Use this reference to avoid stopping at the obvious manufacturing or integration link. Before finalizing any industry-chain report, run a structured upstream discovery pass and decide which upstream layers are core, important, adjacent, or out of scope.

## Why This Exists

Industry-chain analysis often starts from visible manufacturers, module makers, or equipment vendors. That misses upstream material and component links where scarcity, price elasticity, or国产替代 value can be higher. Do not treat "上游材料" as a single row. Split it into resource, chemistry, process material, structural material, electronic material, consumable, equipment, and infrastructure layers.

## Five-Layer Upstream Scan

For the target product or technology, scan these layers in order:

| Layer | Question | Typical Outputs |
| --- | --- | --- |
| Product BOM | What physical parts are inside the product? | chips, modules, PCB, substrate, connector, casing, battery, optics, cooling, magnet, motor |
| Manufacturing Process | What materials are consumed or deposited during manufacturing? | gases, precursors, targets, photoresist, CMP slurry/pad, wet chemicals, plating chemicals, adhesives, encapsulants |
| Board/Package Materials | What enables electrical, thermal, and mechanical performance? | CCL, resin, electronic glass cloth, copper foil, ABF/BT substrate, solder mask, underfill, thermal interface material |
| Resource/Commodity Base | Which mined, refined, or chemical feedstocks determine cost and security? | tungsten, copper, aluminum, lithium, nickel, cobalt, phosphorus, fluorine, rare earth, quartz sand, petroleum derivatives |
| Enabling Infrastructure | What adjacent infrastructure becomes necessary when the product scales? | power, cooling, optical module, fiber, InP/GaAs/LiNbO3, networking, storage systems, testing/certification services |

If a layer is not relevant, explicitly mark it as "弱相关/不纳入主线" rather than silently skipping it.

## Recursive Decomposition Pattern

Use this pattern for every key midstream node:

```text
Final demand/use case
  -> system/module
    -> core component
      -> sub-component
        -> process materials and consumables
        -> structural/electronic materials
        -> upstream resources and chemical feedstocks
        -> equipment/testing/certification
```

Stop recursion only when one of these is true:

- The layer has no material value, scarcity, bottleneck, or A-share exposure.
- The link is too generic and not meaningfully affected by the target industry's growth.
- The link belongs to an adjacent industry and should be tracked separately.
- Public evidence is insufficient; mark it as "待验证" and include a next verification step.

## Material Keyword Expansion

When the target is hardware, electronics, semiconductors, energy equipment, chemicals, aerospace, autos, robotics, medical devices, or communications, expand search and screening keywords beyond the product name.

| Category | Keywords to Try |
| --- | --- |
| Metals and minerals | 钨, 钼, 钽, 铌, 铜, 铝, 镍, 钴, 锂, 锰, 锗, 镓, 铟, 稀土, 石英砂 |
| Semiconductor process materials | 靶材, 钨靶, 钽靶, 铜靶, 前驱体, 电子特气, 磷烷, 砷烷, 六氟化钨, 光刻胶, 显影液, 刻蚀液, CMP抛光液, CMP抛光垫, 湿电子化学品 |
| PCB and substrate | 覆铜板, CCL, 高速板, 高频板, HDI, ABF, BT, IC载板, 电子布, 电子纱, 玻纤布, 低介电, 低CTE, 铜箔, HVLP铜箔, RTF铜箔 |
| Polymer and resin | 环氧树脂, 酚醛树脂, PPO, PTFE, PI, LCP, 胶膜, 粘结片, 半固化片, 阻燃剂, 电子级树脂 |
| Packaging and assembly | 封装基板, 引线框架, 锡膏, 焊球, 底部填充胶, 临时键合胶, EMC塑封料, TIM导热材料 |
| Optical and networking adjacency | 磷化铟, 砷化镓, 硅光, 铌酸锂, 光芯片, 光模块, 800G, 1.6T, 连接器, 高速线缆 |
| Thermal and power adjacency | 液冷, 冷板, CDU, 泵阀, 电源模块, UPS, 变压器, 服务器电源 |

Use both Chinese and English forms when searching public sources. For example: `InP`, `indium phosphide`, `phosphine`, `tungsten hexafluoride`, `low Dk CCL`, `HVLP copper foil`.

## Relevance Classification

Classify discovered upstream links before adding companies to the main table:

| Class | Meaning | Report Treatment |
| --- | --- | --- |
| Core upstream | Direct input to the target product or a manufacturing bottleneck | Main chain map and A-share table |
| Important upstream | Clear cost/quality/reliability driver, but not the main bottleneck | Main table or separate upstream-material table |
| Adjacent infrastructure | Benefits from the same demand driver but serves another subsystem | Separate "相邻链路" table; do not mix with core ranking |
| Commodity background | Generic commodity exposure with weak differentiation | Mention only if price/capacity matters |
| Out of scope | No clear transmission path | Exclude and state why if the user named it |

Example: For an AI server flash-storage topic, CCL/electronic glass cloth/copper foil/resin are board-level upstream materials; tungsten targets/CMP/electronic gases are semiconductor process-material upstream; InP is mainly optical interconnect adjacency, not SSD-core upstream.

## A-Share Discovery Workflow

1. Generate a candidate keyword list from the five-layer scan.
2. Use AkShare concept, industry, and main-business tools as discovery adapters when practical.
3. Search by keyword in company business descriptions, annual-report text, prospectuses, and product pages.
4. Map each candidate to exact sub-segment and relevance class before ranking it.
5. For every material candidate, record whether exposure is:
   - `direct product revenue`,
   - `segment revenue`,
   - `capacity/market share`,
   - `product confirmed but proportion undisclosed`,
   - `adjacent only`,
   - `concept label only`.
6. Do not promote an upstream material company into "core" unless the material is scarce, high-value, high-barrier, or explicitly bottlenecked for the target chain.

## Required Output When Materials Matter

If the product has physical upstream inputs, include an upstream material table unless the analysis is explicitly Light mode.

| 上游层级 | 细分材料/部件 | 对目标产业的作用 | 价值/稀缺性 | 卡脖子程度 | A股候选 | 纳入主线判断 |
| --- | --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... | Core/Important/Adjacent/Out of scope |

Then include only core and important upstream companies in the main company mapping. Put adjacent infrastructure companies in a separate table.

## Red Flags

- The chain map starts at "制造/模组/设备" and has only one generic "材料" row.
- The company table contains manufacturers but no raw materials, process materials, PCB/substrate materials, packaging materials, consumables, or adjacent infrastructure.
- A user-named material such as 钨、磷化铟、树脂、电子布、铜箔、特气、靶材 is absent without an explicit "纳入/排除" judgment.
- Board/concept constituents are used as proof without exact product exposure.

## Evidence Checklist for Upstream Claims

For every upstream material or component promoted to "Core" or "Important" in the chain map, verify at least one concrete evidence item before the claim appears in the final report:

| Evidence Type | Examples | Confidence |
| --- | --- | --- |
| Company filing | Annual report segment revenue, prospectus BOM, capacity/order disclosure | High |
| Industry data | Association statistics, customs HS code import/export, price benchmarks | High |
| Technical report | Product datasheet, process flow diagram from equipment/vendor docs | Medium-High |
| Sell-side / third-party | Broker BOM analysis, industry research reports (with citation) | Medium |
| Logical inference | Process requires X → Y must be an input, no company verified yet | Low |
| Concept-label match | "XX材料" concept board constituent without specific product proof | Very Low / Discovery only |

Mark each row in the upstream-material table with an evidence tier, or add a note when only low-confidence evidence is available.

## Weak-Evidence Marking Rules

- If a material or component is plausible but has no filing or industry-statistics support, label it **"待验证 (Low)"** in the 证据与备注 column.
- If the only evidence is a concept-board label or a vague "XX概念股" mention, do **not** classify it as Core or Important. Use **Adjacent** at most and mark "概念标签，待验证具体产品".
- If the material is named by the user but no A-share company can be verified, keep the row in the table with **"A股候选：待验证"** rather than removing it.
- For chains with strong physical inputs (semiconductors, energy storage, EV, solar, chemicals, aerospace) that lack upstream-material evidence, add an explicit **"上游证据不足"** caveat in the risk section.
- For chains that are primarily software or service-based (互联网、软件、SaaS), explicitly state that "physical BOM 不适用" and skip the upstream-material table rather than forcing one.
