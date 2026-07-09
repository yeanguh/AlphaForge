# 参考:主题池与研报路由(方案 A)(L3)

> 稳定事实。主题池配置 `config/theme_pool.json`,研报策略 `config/report_policy.json`。

## 三层主题池

- `config/theme_pool.json` 的 `themes` 是**字典**(key 为主题键),不是列表。
- 每个主题含:`tier`(core / watch / emerging)、`aliases`、`label`(中文名)、`discovery_keywords`(发现打分关键词)。
- `tier_policy` 定义各层策略。
- 消费方:`loop_os/report_router.py`(路由)、`loop_os/domain/capability_chain.py`(发现关键词)、`loop_os/reporting.py`(中文 label)。三者均 config-driven + 内置 fallback。

当前 15 个主题键:`ai-compute-infra`、`datacenter-power`、`physical-ai`、`agentic-ai`、`sovereign-ai`、`ai-security-governance`、`edge-ai`、`ai-healthcare`、`ai-industrial-software`、`ai-commercialization`、`autonomous-low-altitude`、`quantum-computing`、`space-defense-ai`、`ai-fintech-infra`、`blockchain-ai-payments`。

## 研报三级产物(方案 A)

| 目录 | 定位 | 说明 |
| --- | --- | --- |
| `reports/themes/<theme>/report.md` | **canonical 最终研报** | 循环持续精炼的权威知识库,唯一"最重要可见产物" |
| `reports/daily/` | **增量 inbox / 研究日志** | 过程产物,非最终;由 `route_cycle_reports` 沉淀到 themes |
| `reports/industry/<topic>-<date>/` | **legacy / 手工快照** | 已迁移,留 `MOVED.md` 指针;harness 校验降级为 optional/warn |
| `reports/stocks/<symbol>/`、`reports/weekly/` | 个股 / 周报 | — |

## 门禁(harness)

- `check_theme_reports`:canonical gate `theme_report:canonical:<key>`(默认要求 `physical-ai`,由 `config/report_policy.json` 的 `theme_report.canonical_required` 配置)+ 图片坏链检查 `theme_report:image_links`。
- `check_industry_analysis_report`:全部降级为 `warn`(legacy,`industry_report:legacy_*`),不阻断。
