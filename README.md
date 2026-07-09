# AI 投研 Loop OS

这是一个从 0 到 1 新建的独立投研 Loop 项目。

边界：

- Codex / Claude Code 是执行 Agent，不自研 Agent runtime。
- `loop_os/` 定义 schema、state、loop、harness。
- `external/` 中存放框架、Agent、资讯等第三方开源 submodule。
- `skills/` 中存放 skill 型 submodule 和项目级 skill 入口：`a-stock-data`、`global-stock-data`、`industry-chain-analysis`。
- `loop_os/` 不直接 import `external/*`。
- 不再保留 `china-stock-analysis`、`china-stock-price-analysis`；个股和行情能力通过 open-source provider adapter 接入。

第一轮验证：

```bash
python scripts/run_provider_smoke.py --live
python scripts/run_harness.py --live
```

输出会写入 `runs/YYYY-MM-DD/`。

报告类产物统一写入 `reports/`：

- `reports/daily/`：每日 loop 面向人的摘要和运维摘要。
- `reports/industry/`：产业链深度研报，目录形如 `<topic>-<YYYY-MM-DD>/`，包含 `report.md`、`source_data.json`、`quality_report.json` 和 `assets/`。
- `reports/stock/`：预留给单票深度报告。
- `reports/weekly/`：预留给周度复盘。

## 持续运行

本地常驻闭环入口：

```bash
python scripts/run_full_loop.py --forever --interval-seconds 300 --continue-on-error --agent-mode codex
```

测试或演示时可以限制轮数：

```bash
python scripts/run_full_loop.py --forever --interval-seconds 30 --max-cycles 2 --agent-mode codex
```

每个 cycle 会完成：公开数据取数、资讯/研报抓取、Codex/Claude Code Agent 归纳评审、evidence 落库、主题/催化/候选状态迁移、harness 裁判、模拟仓复盘记录。supervisor 心跳写入 `state/system-health.json`，单轮失败时可退避后继续下一轮。

Agent 模式：

- `--agent-mode codex`：调用本机 `codex exec`，输出结构化 JSON 评审。
- `--agent-mode claude`：调用本机 `claude --print`，输出结构化 JSON 评审。
- `--agent-mode auto`：优先 Codex，失败后尝试 Claude，最后降级到 deterministic fallback 并记录 `agent_errors`。
- `--agent-mode deterministic`：不用外部 LLM，仅用于离线测试和 harness smoke。

## 数据源降级策略

对齐旧 `stock-analysis` 的本地优先原则，并以 `skills/a-stock-data` 的公开源策略作为 A 股数据 adapter 的主要依据：

- A 股历史数据优先读取 workspace 级 `../a-data/hist/<code>.csv`；只有后续需要补历史尾部时，才通过 adapter 做增量补齐。
- A 股实时/估值快照优先级：腾讯公开行情 -> 东方财富 push2 -> 本地 `a-data/hist` 最新收盘价兜底。
- 全球股票快照优先级：Yahoo chart -> 腾讯美股行情 -> 其他公开源兜底。
- 资讯/研报抓取允许部分源失败，loop 记录错误但不因少数源不可用中断主流程。
- 需要 key 的能力只能作为增强项，缺失时必须降级到公开数据、本地归档或标记 evidence gap。
