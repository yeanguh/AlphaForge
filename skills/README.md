# Retained Skills

本目录保存 Research OS 明确允许保留的项目级 skill 入口，以及 skill 型开源 submodule。

复制策略：

- `a-stock-data`：通过 git submodule 引入，作为 A 股取数 skill 和 provider adapter 的接口依据。
- `global-stock-data`：通过 git submodule 引入，作为美股/港股/全球市场取数 skill 和 provider adapter 的接口依据。
- `industry-chain-analysis`：从 `/Users/bytedance/Documents/a-analysis/stock-analysis/.agents/skills/industry-chain-analysis` 完整复制，保留 `agents/`、`references/`、`scripts/` 和原始 `SKILL.md`。
- `china-stock-analysis` 和 `china-stock-price-analysis` 已按最新方案移除，不作为 retained skill。

边界：

- `skills/*/SKILL.md` 是 Agent 可读的方法论和操作入口。
- `providers/retained_skills/*` 是运行时 adapter，把 skill 产物转成统一 schema。
- `loop_os/` 不直接依赖这些 skill 的文件结构。
- 除本目录 skill 外，不继承旧仓库其他 skill。
- skill 不能直接写 `state/*`；状态变化必须通过 adapter、domain service、state machine 和 harness。

保留清单：

| Skill | Runtime adapter | Purpose |
| --- | --- | --- |
| a-stock-data | providers/open_source/a_stock_data.py | A 股行情、估值、研报等公开数据源方法论 |
| global-stock-data | providers/open_source/global_stock_data.py | 全球股票行情和跨市场数据源方法论 |
| industry-chain-analysis | providers/retained_skills/industry_chain_analysis.py | 产业链、卡口、A 股暴露验证 |
