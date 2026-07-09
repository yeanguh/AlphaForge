# ARCHITECTURE (L0 · 架构入口)

> **权威源**:架构不变式与代码地图的**完整权威内容**在
> [`docs/reference/architecture-invariants.md`](docs/reference/architecture-invariants.md) 与
> [`docs/reference/module-map.md`](docs/reference/module-map.md)。
> 本文件是 L0 导航入口:给出一屏概览并指向权威源。两处不一致时,**以 `docs/reference/` 两个文件为准**。

## 这是什么

research-os 是一个本地优先的 AI 投研 loop OS:围绕主题池持续取数 → 生成/合并研报 → 校验状态。
方案 A 下,`reports/themes/<theme>/report.md` 是被 loop 持续精修的 canonical 知识库。

## 顶层结构(速览)

```
scripts/    运行入口(run_full_loop / run_harness / run_provider_smoke)
   │
loop_os/    系统内核:domain / schemas / state_machine / harness / reporting
   │        ⛔ 禁止 import external/*
providers/  外部数据唯一入口:ports(抽象)/ open_source(实现)/ retained_skills / reference
   │
external/*  子模块;只能经 providers/* 访问,禁止进运行时循环
config/     配置驱动源:theme_pool.json / report_policy.json / ...
reports/    产物:themes/(canonical)· daily/(inbox)· industry/(legacy)· stocks/ · weekly/
```

依赖方向单向:`scripts/ → loop_os/ → providers/ports`,`loop_os/` 绝不反向依赖具体实现或直接 import `external/*`。

## 架构不变式(摘要,权威见 reference)

1. `loop_os/*` 禁止 `import external/*`;external 仅经 `providers/open_source` 或 `providers/reference` 访问,reference-only 子模块禁止进运行时循环。
2. 每个改变 state 的 claim 必须有 evidence id;state 变更须过 `state_machine/*` + `harness/*`。
3. 保留的分析类技能仅 `industry-chain-analysis`(取数类 skill 另计);⛔ 禁止复活 `china-stock-analysis` / `china-stock-price-analysis`。
4. 研报 canonical 产物 = `reports/themes/<theme>/report.md`(方案 A),已存在则增量合并、绝不整篇覆盖;`reports/industry/` = legacy/manual snapshot。
5. config-driven + hardcoded fallback:主题池 / 研报口径优先读 `config/*.json`,缺失时回退模块内 `_FALLBACK_*`;新增主题只改 config。

> 完整清单、校验落点、子模块与关键文件见
> [`docs/reference/architecture-invariants.md`](docs/reference/architecture-invariants.md) 和
> [`docs/reference/module-map.md`](docs/reference/module-map.md)。
> 文档分层与路由见 [`docs/AGENTS.md`](docs/AGENTS.md);设计叙事见 [`docs/architecture-design.md`](docs/architecture-design.md)。
