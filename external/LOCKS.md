# External Locks

| Project | Path | Commit | Type | Purpose | Upgrade Policy |
| --- | --- | --- | --- | --- | --- |
| a-stock-data | skills/a-stock-data | bcda4054b979166a3d06b628f16f3dc9b1ff7eb2 | active provider skill | A 股数据 | 先跑 provider smoke + market-data harness |
| investment-news | external/investment-news | d98aa603228f4839fb48859812c63a58ca10cead | active provider | 新闻输入 | 先跑 provider smoke + news harness |
| global-stock-data | skills/global-stock-data | d52a8a0013363577bceb28ca876c88fe6c1a5aeb | active provider skill | 全球市场和跨市场信号 | 先跑 provider smoke + global-market harness |
| TradingAgents-astock | external/TradingAgents-astock | b81197653b367f84242e6fe0bca3fb6bac4619b5 | review provider smoke-only | A 股投委会式复核参考；尚未进入主 loop runtime | 先跑 review-provider harness |
| Vibe-Research | external/Vibe-Research | db97b9ee31bd939de5fde30724943356f41d452a | UI/reference smoke-only | 看板和研究工作台参考；尚未进入主 loop runtime | 先跑 dashboard-export smoke test |
| Vibe-Trading | external/Vibe-Trading | b8a7c5e29f138b9553438ff2094bc34d52a284c4 | strategy sandbox smoke-only | 策略实验和 Shadow Account 参考；尚未进入主 loop runtime | 先跑 sandbox adapter smoke test |

Pure reference projects are tracked as notes, not submodules:

- NousResearch/hermes-agent: see `providers/reference/hermes_agent_notes.md`.
- TauricResearch/TradingAgents: see `providers/reference/tradingagents_upstream_notes.md`; runtime review uses `external/TradingAgents-astock`.
