# 架构不变式 (L3 · 稳定事实)

> **本文件是架构不变式的权威源。** 根 `ARCHITECTURE.md` 是 L0 导航入口(一屏概览),完整清单以本文件为准;两处不一致时以本文件为准。

违反以下任一条即视为架构错误:

1. `loop_os/*` **禁止** `import external/*`。
2. external 子模块只能经 `providers/open_source/*` 或 `providers/reference/*` 访问;reference-only 子模块**禁止进运行时循环**。
3. 每个改变 state 的 claim 必须有 **evidence id** 背书。
4. state 变更必须通过 `loop_os/state_machine/*` 规则 + `loop_os/harness/*` 校验。
5. 保留的**分析类**技能仅 `industry-chain-analysis`(取数类 `a-stock-data` / `global-stock-data` / `wen-cai` 另计);⛔ 禁止复活 `china-stock-analysis` / `china-stock-price-analysis`。
6. 研报 canonical 产物 = `reports/themes/<theme>/report.md`(方案 A);`reports/daily/` = 增量 inbox,`reports/industry/` = legacy/manual snapshot。
7. **config-driven + hardcoded fallback**:主题池 / 研报口径优先读 `config/theme_pool.json` / `config/report_policy.json`,config 缺失时回退模块内 `_FALLBACK_*`;新增主题只改 config,不硬编码。
8. 不在仓库外引入隐式本地依赖;外部缓存必须经环境变量显式配置。
9. `.codex/skills/*` 只允许作为本地 Codex 扫描符号链接;不得把 reference-only skill 因为 symlink 存在而接入 runtime loop。

## 校验落点

| 不变式 | 由谁守护 |
| --- | --- |
| 1、2 | `harness/checks.py`(import/submodule 检查) |
| 3、4 | `state_machine/*` + `harness` state 检查 |
| 6 | `harness/checks.py::check_theme_reports`(canonical gate) |
| 7 | 各模块 `_load_*` + `_FALLBACK_*`(capability_chain / report_router / reporting / checks) |
| 8、9 | code review + `docs/reference/data-access.md` + import/submodule 检查 |
