# SOP:跑一次完整研究循环(L3)

## 前提
- 已初始化 `.venv`;外部数据源缓存通过环境变量显式配置(不得引入隐式本地依赖)。

## 步骤
1. (可选)先验证数据源可用:
   ```bash
   uv run python scripts/run_provider_smoke.py --live
   ```
2. 运行完整循环:
   ```bash
   uv run python scripts/run_full_loop.py
   ```
   该循环:拉行情/新闻/研报 → 生成 evidence card 与 claim index → 主题打分选一条产业链 → agent review → 组装 pipeline → 提交 state transition → 写 `runs/`、`reports/daily/`(增量 inbox)、`data/raw/latest-full-loop.json` → 由 `route_cycle_reports` 把最终结论沉淀到 `reports/themes/<theme>/report.md` → 生成产业链深度报告。
3. 提交任何 state 变更前跑 harness:
   ```bash
   uv run python scripts/run_harness.py
   ```
   status 必须为 ok(所有 check 为 ok/warn)。

## 校验
- `reports/themes/<theme>/report.md` 已更新(canonical)。
- `uv run python scripts/run_harness.py` 无 error。

## 注意
- `reports/daily/` 是过程日志,不是最终报告,不要当交付物。
- 最终交付物永远是 `reports/themes/<theme>/report.md`。
