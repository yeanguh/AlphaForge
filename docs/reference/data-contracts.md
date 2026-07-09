# 参考:Evidence / Claim / State 数据契约(L3)

> 稳定事实,抽取自 `docs/architecture-design.md` §7/§9。改动数据形态前先看这里。

## Evidence

| 产物 | 职责 |
| --- | --- |
| `evidence/YYYY-MM-DD/ev-*.json` | 单个 evidence card,来自行情 / 新闻 / 研报 / 产业链 / 个股补充 / 决策门禁 / agent review |
| `evidence/YYYY-MM-DD/raw-index.json` | 当日 evidence id 增量索引 |
| `evidence/YYYY-MM-DD/claim-index.json` | 从当日所有 evidence card 重建的 claim-level 索引,支持追溯 |

每个 evidence card 至少包含:source name、source type、title、非空 claims、source locator 或 raw payload、freshness;可选 related companies / related themes。

## Claim(state 与报告的最小证据单元)

| 字段 | 含义 |
| --- | --- |
| `claim_id` | claim-level 稳定标识 |
| `evidence_id` | 所属 evidence card |
| `claim` | 可被人工检查的一句话事实或判断 |
| `stance` | `supporting` / `contradicting` / `neutral` / `stale` |
| `freshness` | `intraday` / `current` / `latest_available` / `stale` |
| `related_companies` / `related_themes` | claim 关联对象 |
| `source_url` / `raw_path` | 可追溯来源 |

## State 文件(粗粒度,一文件一根对象)

| State 文件 | 职责 |
| --- | --- |
| `research-state.json` | 研究 loop 状态、跟踪主题、下一步动作 |
| `catalysts.json` | 催化剂生命周期和验证状态 |
| `watchlist.json` | 候选 / 观察 / 模拟候选 / 拒绝等个股状态 |
| `paper-portfolio.json` | 模拟组合和复盘 |
| `system-health.json` | supervisor 心跳和最新 loop 健康状态 |

## 状态流转(状态机最小契约)

| 对象 | 推荐状态流转 |
| --- | --- |
| Theme | `discovered -> tracking -> validated -> archived/rejected` |
| Catalyst | `discovered -> validating -> confirmed -> priced_in/expired/rejected` |
| Watchlist | `candidate -> watching -> paper_candidate -> rejected/archived` |
| PaperPortfolio | `reviewed -> simulated_position -> exited -> postmortem` |
| Thesis | `proposed -> supported/challenged -> validated/invalidated/priced_in` |

## 迁移规则(不变式)

- 新状态不得绕过 `loop_os/state_machine/*`。
- 已确认状态不能被新一轮信号自动降级,除非有明确 contradicting claim。
- 每次状态变化必须记录 `run_id` / `changed_at` / `reason` / `evidence_ids`(目标升级为 `claim_ids`)。
- `state/*` 不保存大段原始数据;原始数据留在 `data/raw/` / `runs/` 或 evidence card。
- schema 定义在 `loop_os/schemas/*`(evidence / packet / catalyst / review / state / watchlist / provider)。
