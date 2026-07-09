# External Submodules

本目录存放非 skill 型的第三方开源 submodule；skill 型依赖放在 `skills/`。

规则：

- 所有 submodule 必须记录在 `LOCKS.md`。
- `loop_os/` 不得直接 import 本目录。
- active provider 只能通过 `providers/open_source/*` adapter 暴露能力。
- 纯思路参考项目不放入本目录；只在 `providers/reference/` 保留 notes 和上游链接。
- 更新任何 submodule 后，必须运行对应 harness 或完成 reference review。

| Project | Path | Type | Adapter/Note |
| --- | --- | --- | --- |
| investment-news | external/investment-news | active provider | providers/open_source/investment_news.py |
| TradingAgents-astock | external/TradingAgents-astock | review provider smoke-only | providers/open_source/tradingagents_astock.py |
| Vibe-Research | external/Vibe-Research | UI/reference smoke-only | providers/open_source/vibe_research.py |
| Vibe-Trading | external/Vibe-Trading | strategy sandbox smoke-only | providers/open_source/vibe_trading.py |

不再作为 submodule 的纯参考：

- NousResearch/hermes-agent：仅保留 `providers/reference/hermes_agent_notes.md`。
- TauricResearch/TradingAgents：仅保留 `providers/reference/tradingagents_upstream_notes.md`；运行/评审优先使用 `external/TradingAgents-astock`。
