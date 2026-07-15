# AlphaForge

AlphaForge 是一个本地优先的 AI 深度投研系统,用于持续挖掘产业链主题、A 股标的和投资机会。

边界：

- Codex / Claude Code 是执行 Agent，不自研 Agent runtime。
- `loop_os/` 定义 schema、state、loop、harness。
- `external/` 中存放框架、Agent、资讯等第三方开源 submodule。
- `skills/` 中存放本仓库项目级 skill 入口：`a-stock-data`、`global-stock-data`、`industry-chain-analysis`、`wen-cai-*`。
- `.codex/skills/` 是 workspace-local Codex 扫描符号链接目录(ignored),可指向仓库内 skill 和 `external/ch-skills/skills/*` reference skill,但不代表 runtime 依赖。
- `loop_os/` 不直接 import `external/*`。
- 个股和行情能力通过 open-source provider adapter 接入。

第一轮验证：

```bash
uv run python scripts/run_provider_smoke.py --live
uv run python scripts/run_harness.py --live
```

输出会写入 `runs/YYYY-MM-DD/`。

## 可选 Vibe-Trading agent runtime

Vibe-Trading 的完整 agent/API/MCP 依赖较重，并且与默认 A 股增强依赖 `mootdx` 的 `httpx` 版本约束冲突，所以不并入默认 `uv.lock`。需要运行 upstream agent 能力时，使用独立的 uv requirements：

```bash
PYTHONPATH=external/Vibe-Trading/agent \
  uv run --no-project --with-requirements requirements/vibe-trading.txt \
  python - <<'PY'
from src.agent.skills import SkillsLoader
import api_server
import mcp_server
print(len(SkillsLoader().skills), api_server.app.title, mcp_server.APP_VERSION)
PY
```

若要把依赖装进当前 `.venv`：

```bash
uv pip install --python .venv/bin/python -r requirements/vibe-trading.txt
uv pip install --python .venv/bin/python --no-deps -e external/Vibe-Trading
```

在完整 loop 中默认不会启动 Vibe-Trading sidecar。需要启用时设置：

```bash
VIBE_TRADING_ENABLED=1 VIBE_TRADING_TIMEOUT_SECONDS=60 \
  uv run python scripts/run_full_loop.py --max-cycles 1 --agent-mode deterministic
```

启用后，`providers/open_source/vibe_trading.py` 会用 subprocess 运行 `scripts/run_vibe_trading_agent.py`，输出写入 `research_pipeline.provider_insights.providers.vibe_trading_agent`，并由 evidence service 生成 provider evidence card；sidecar 失败只返回 `warn`，不会中断主 loop。

`requirements/vibe-trading.txt` 由 `uv pip compile requirements/vibe-trading.in --output-file requirements/vibe-trading.txt --python-version 3.12` 生成。当前刻意排除了 `smartmoneyconcepts`，因为它的 PyPI 依赖链会拉取元数据损坏的 `zigzag==0.3.2`；这只影响 SMC 信号 skill，不影响 Vibe-Trading 的 CLI、API、MCP、skills loader、数据 loader、回测和 shadow account 主体能力。

报告类产物统一写入 `reports/`（方案 A：主题池是 loop 持续沉淀的最终知识库）：

- `reports/themes/<theme>/report.md`：**canonical final reports**——由每日 loop 持续精炼的最终研报，是最终研究资产。每篇可带 `assets/`（图片）。主题键与 `config/theme_pool.json` 一致（如 `physical-ai`）。
- `reports/stocks/<symbol>/`：单票深度报告（持续沉淀）。
- `reports/weekly/`：周度复盘。
- `reports/daily/`：**增量 inbox / 研究日志**，非最终报告——每日 loop 的证据流水与运维摘要，最终结论以 `reports/themes/` 为准。
- `reports/industry/`：**legacy / 手写快照**——历史产业链深度研报，已迁移到 `reports/themes/`（留 `MOVED.md` 指针）；harness 视为可选检查，不再作为主报告门禁。

## 持续运行

本地常驻闭环入口：

```bash
uv run python scripts/run_full_loop.py --forever --interval-seconds 300 --continue-on-error --agent-mode codex
```

测试或演示时可以限制轮数：

```bash
uv run python scripts/run_full_loop.py --forever --interval-seconds 30 --max-cycles 2 --agent-mode codex
```

每个 cycle 会完成：公开数据取数、资讯/研报抓取、Codex/Claude Code Agent 归纳评审、evidence 落库、主题/催化/候选状态迁移、harness 裁判、模拟仓复盘记录。supervisor 心跳写入 `state/system-health.json`，单轮失败时可退避后继续下一轮。

Agent 模式：

- `--agent-mode codex`：调用当前环境中的 `codex exec`，输出结构化 JSON 评审。
- `--agent-mode claude`：调用当前环境中的 `claude --print`，输出结构化 JSON 评审。
- `--agent-mode auto`：优先 Codex，失败后尝试 Claude，最后降级到 deterministic fallback 并记录 `agent_errors`。
- `--agent-mode deterministic`：不用外部 LLM，仅用于离线测试和 harness smoke。

## 数据源降级策略

AlphaForge 默认只依赖仓库内目录、submodule、显式环境配置的 CLI/缓存和公开网络源。以 `skills/a-stock-data` 的公开源策略作为 A 股数据 adapter 的主要依据：

- A 股实时/估值快照优先级：腾讯公开行情 -> 东方财富 push2 -> 仓库内或显式配置的历史数据缓存兜底。
- 仓库内历史数据默认目录是 `data/local/a-data/hist/<code>.csv`；如需复用外部缓存，必须显式设置 `RESEARCH_OS_A_DATA_DIR`。
- 全球股票快照优先级：Yahoo chart -> 腾讯美股行情 -> 其他公开源兜底。
- 资讯/研报抓取允许部分源失败，loop 记录错误但不因少数源不可用中断主流程。
- 需要 key 的能力只能作为增强项，缺失时必须降级到公开数据、本地归档或标记 evidence gap。
- 数据接入契约、token/key 环境变量和手工 reference skill 使用方式见 `docs/reference/data-access.md`。
