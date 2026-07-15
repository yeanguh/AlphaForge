# AlphaForge 架构设计方案

> 版本：2026-07-09  
> 范围：`alpha-forge-research` 独立项目仓库
> 原则：以当前仓库最新实现为准，同时描述目标架构；默认运行不依赖仓库外目录。
>
> **文档分层**：稳定事实已抽取到 `docs/reference/`（data-contracts / repo-layout / theme-pool-and-reports / harness-checks）；可执行 SOP 见 `docs/guidance/`；本文件保留设计叙事与演进路线。索引见 `docs/AGENTS.md`，架构不变式见 `docs/reference/architecture-invariants.md`(根 `ARCHITECTURE.md` 为 L0 导航入口)。

## 1. 项目目标

AlphaForge 是一个本地优先的 AI 投研循环系统。它的目标不是回答“明天买什么”，而是围绕公开信息、产业链研究、标的验证、买点分析和复盘反馈，帮助人持续训练某个领域的投资判断力。

系统最终应该稳定产出面向人阅读的产业链深度研报，而不是给 agent 消费的过程日志。研报需要具备：

- 证据来自公开新闻、研报、公告、行情、财务数据，并尽量附原始链接；
- 每轮从公开热点中选择一个权重最高的产业链做深度分析；
- 证据足够时至少给出 3 个核心 A 股标的；
- 对每个核心标的说明产业链位置、收入暴露假设、催化剂、估值、价格结构、趋势、箱体、支撑阻力、买点区间、失效条件和待验证证据；
- Agent 评审用于挑战和提高研究质量，不用于自动交易。

Codex / Claude Code 是执行 Agent。AlphaForge 不自研 Agent runtime。

## 2. 分层系统哲学

系统设计哲学是：把 AI 嵌入人的投资体系。

| 层级 | 维护者 | 职责 | 当前仓库承载 |
| --- | --- | --- | --- |
| 数据层 | AI 维护 | 拉取公开新闻、研报、公告、行情、财务、问财查询结果，并沉淀证据。 | `providers/open_source/`、`skills/a-stock-data`、`skills/global-stock-data`、`external/investment-news`、`skills/wen-cai-*`、`evidence/` |
| 工具层 | AI 维护 | 清洗数据、生成证据卡、选择热点产业、映射产业链、分析标的、运行评审、写报告和状态。 | `loop_os/domain/`、`providers/ports/`、`providers/retained_skills/`、`scripts/` |
| 策略层 | 人维护 | 决定采用哪些投资框架和研究方法，如产业链催化、卡口投资、SEPA、CANSLIM、RPS、估值、价格行为。 | `playbooks/`、`skills/industry-chain-analysis`、未来策略配置 |
| 内核层 | 人维护 | 投资心法、风险偏好、论点库、已证实/证伪认知、人工挑战和最终取舍。 | `memory/`、`state/research-state.json`、未来 thesis library |

AI 负责维护数据层和工具层。人维护策略层和内核层。系统状态不是交易指令，而是记录当前研究循环处于什么阶段：发现、跟踪、验证、确认、已定价、拒绝或复盘。

## 3. 运行模式

目标每日循环如下：

1. 扫描公开新闻、精选资讯源、行业研报、公告、行情、财务数据和问财查询结果。
2. 将原始输入转成 evidence card 和 claim index。
3. 对热点主题打分，选择一个最高权重产业链进入深度分析。
4. 使用 `industry-chain-analysis` 方法论拆解需求驱动、上游稀缺、卡口环节、价值分布、A 股暴露、催化剂、风险和证据缺口。
5. 当证据足够时，筛出至少 3 个核心 A 股候选标的。
6. 对每个候选标的做业务暴露、财务估值、催化关联、技术结构和风险分析。
7. 先跑本地确定性决策门禁，再调用外部 Agent 风格评审作为第二意见。
8. 将面向人阅读的最终研报持续沉淀到 canonical 主题报告 `reports/themes/<theme>/report.md`（方案 A：themes 统一取代 industry，产业报告是主题报告的一种），将运行过程写入 `runs/` 和 `data/raw/`。
9. 只有经过验证的证据和状态迁移，才能通过 state service 写入 `state/`。
10. 后续根据市场表现、催化兑现和人工挑战，将反馈写回 `state/` 和 `memory/`。

系统的价值重点不是把每天几十上百篇文章摘要推给人，而是维护“人的论点库”，只突出相对现有认知的增量信息：支持了哪条论点、挑战了哪条论点、是否已被市场定价、是否触发失效条件。

## 4. 当前仓库目录职责

| 路径 | 职责 |
| --- | --- |
| `loop_os/` | 核心 schema、domain service、状态机、harness、报告写入逻辑。不得直接 import `external/*`。 |
| `providers/ports/` | 稳定 provider 接口，包括行情数据、新闻资讯、评审能力。 |
| `providers/open_source/` | 开源项目和 submodule 的只读 adapter，把外部能力转成 AlphaForge 统一 packet。 |
| `providers/retained_skills/` | 保留方法论 skill 的运行时 adapter，当前核心是 `industry-chain-analysis`。 |
| `skills/` | skill 型依赖和保留方法论。当前允许：`industry-chain-analysis`、`a-stock-data`、`global-stock-data`、`wen-cai-*`。 |
| `.codex/skills/` | workspace-local Codex skill discovery 符号链接目录(ignored)。可链接仓库内 skill 和 `external/ch-skills/skills/*` reference skill,但不代表 runtime 依赖。 |
| `external/` | 开源 submodule 与 reference-only skill 集合。只能通过 `providers/open_source/*` 或 `providers/reference/*` 使用;`external/ch-skills/skills/*` 默认不进入 runtime loop。 |
| `config/` | provider 注册、策略、市场、调度和评审 schema。 |
| `evidence/` | 按日期存 evidence card、raw index、claim index。 |
| `state/` | 一个状态文件一个根对象：研究状态、催化剂、观察池、模拟组合、系统健康。 |
| `memory/` | 更长期的人机记忆，包括主题、公司、决策和复盘。 |
| `reports/` | 面向人的报告。canonical final reports = `reports/themes/<theme>/report.md`；`reports/stocks/<symbol>/`、`reports/weekly/`；`reports/daily/` 是增量 inbox / 研究日志（非最终报告）；`reports/industry/` 是 legacy / 手写快照。 |
| `runs/` | 每轮运行的操作产物和调试材料。 |
| `playbooks/` | 文章消化、产业链分析、决策门禁等流程契约。 |
| `tests/` | provider fallback、evidence、state、harness、agent review 的契约测试。 |

## 5. 外部依赖和定位

需要运行或 smoke 的外部项目用 submodule 固定版本。纯思路参考项目只放 notes，不作为 submodule。

| 依赖 | 路径 | 当前定位 | 目标定位 |
| --- | --- | --- | --- |
| `simonlin1212/a-stock-data` | `skills/a-stock-data` | A 股行情、估值、公告、资金流、财务、研报等公开数据 provider skill。 | A 股数据主工具箱，统一收敛到 MarketDataPort。 |
| `simonlin1212/global-stock-data` | `skills/global-stock-data` | 全球市场行情 provider skill。 | 跨市场对照和海外产业链/公司参考。 |
| `simonlin1212/investment-news` | `external/investment-news` | 资讯标题和新闻源抓取 provider。 | 精选投研资讯流和定时 ingestion 来源。 |
| `skills/wen-cai-*` | `skills/wen-cai-*` | 已安装问财 provider skill。 | 因子筛选、概念成分、技术池、候选验证、问财自然语言查询。 |
| `industry-chain-analysis` | `skills/industry-chain-analysis` | 本仓库保留的方法论 skill。 | 产业链研究核心方法：上游发现、卡口分析、A 股映射、报告质量门禁。 |
| `Haochenhust/ch-skills` | `external/ch-skills` | reference-only Codex skill 集合;可通过 `.codex/skills` 进入 workspace-local 扫描。 | 方法论/手工数据脚本参考;不得因 symlink 存在而进入 runtime loop。 |
| `ch-skills/tushare-data` | `external/ch-skills/skills/tushare-data` | Tushare Pro 手工参考 skill。 | Tushare 接口权限随账号变化;只能作为经验证的增强源,不作为利润表主源。 |
| `ch-skills/stock-market-data` | `external/ch-skills/skills/stock-market-data` | AKShare 手工参考 skill。 | 交易日、指数、ETF、板块、涨停池等手工补充;接 runtime 前需 provider adapter。 |
| `ch-skills/financial-data-fetcher` | `external/ch-skills/skills/financial-data-fetcher` | Tushare + AKShare 财务编排参考。 | 财务编排参考;Tushare 主路径必须按账号权限和 smoke 结果验证。 |
| `TradingAgents-astock` | `external/TradingAgents-astock` | 已通过 `review_packet` 轻量接入只读评审。 | A 股投委会式第二意见，在 AlphaForge 已有证据和候选后评审。 |
| `Vibe-Research` | `external/Vibe-Research` | 已通过只读 insight adapter 进入主 loop。 | 研究工作台、证据组织、报告 workflow 和覆盖度检查参考。 |
| `Vibe-Trading` | `external/Vibe-Trading` | 已通过只读 strategy adapter 进入主 loop；完整 runtime 为环境变量开启的 sidecar。 | 技术面小组、基本面严谨性检查、假设注册、回测/影子账户建议。 |
| `TradingAgents` 原生项目 | `providers/reference/tradingagents_upstream_notes.md` | note-only。 | 不进入运行依赖；A 股评审优先用 `TradingAgents-astock`。 |
| `hermes-agent` | `providers/reference/hermes_agent_notes.md` | note-only。 | 只参考 prompt/tool contract 思路。 |

所有 submodule 都视为第三方只读依赖。不要直接改 submodule；项目内适配和修复应写在 `providers/open_source/` 或 AlphaForge 自己的 domain 层。默认运行不得依赖 `alpha-forge-research` 以外的隐式目录；底层 CLI、公共 skill、submodule 和通过环境变量显式配置的数据缓存除外。

Provider 接入必须经过 registry 和 fallback policy：

- `config/providers.yaml` 是 provider 注册源，记录类型、路径、adapter 和是否进入 runtime。
- runtime 只依赖 `providers/ports/*` 暴露的接口，不直接依赖第三方项目目录。
- 每个 active provider 必须声明 primary / fallback / smoke-only / reference-only 语义。
- provider 返回值必须带 `source_name`、`freshness`、`checked_at` 或等价字段，便于后续 evidence 追溯。
- provider 失败可降级为 `warn` 或 fallback，但不能静默填充无来源数据。
- 多 provider 数据冲突时，优先使用公告、交易所、公司披露和原始行情源；次级聚合源只能作为交叉验证。

数据源契约、token/key 环境变量、外部 reference skill 和财务三表替代路径见
`docs/reference/data-access.md`。Tushare Pro 的 `income` 等接口可能受账号权限限制,
利润表主路径应优先走 `a-stock-data` 东财 F10,再用 WenCai/AKShare/公告原文交叉验证。

## 6. 能力架构

AlphaForge 应该把能力做成可组合阶段，而不是松散脚本调用。

| 阶段 | 职责 | 主要工具 |
| --- | --- | --- |
| `news-scanner` | 收集公开新闻、研报标题、资讯源条目。 | `investment-news`、公开 feed/search、未来 wechat-feeds |
| `article-reader` | 把文章/标题转成 claim、主题、实体、证据缺口。 | AlphaForge reader、未来 Vibe-Research workflow adapter |
| `hotspot-scoring` | 给主题打分，选择一个产业链进入深度研究。 | `loop_os/domain/capability_chain.py`、问财概念/因子查询 |
| `industry-chain-mapper` | 生成上中下游、卡口、价值分布、A 股暴露。 | `industry-chain-analysis`、`a-stock-data`、公开研报 |
| `catalyst-tracker` | 跟踪前瞻催化剂及状态。 | `state/catalysts.json`、状态机 |
| `stock-analyzer` | 分析候选标的的业务暴露、基本面、估值、催化、风险。 | `a-stock-data`、`wen-cai`、公告/研报 |
| `technical-analyzer` | 分析趋势、箱体、支撑阻力、量能、均线、失效位。 | `a-stock-data`、`wen-cai`、未来 Vibe-Trading 技术面小组 |
| `valuation-calculator` | 计算 PE/PB、历史分位、同行对比、目标空间和估值风险。 | `a-stock-data`、财务数据、未来本地估值模块 |
| `trade-decision-engine` | 执行研究型门禁：证据、催化、盈亏比、技术结构、估值、失效条件。 | `loop_os/domain/capability_chain.py`、`playbooks/decision-gate.md` |
| `agent-reviewer` | 挑战研究结论和候选名单。 | Codex/Claude Code、`TradingAgents-astock`、未来 Vibe-Trading |
| `portfolio-analytics` | 维护模拟组合和复盘反馈。 | `state/paper-portfolio.json`、未来 Vibe-Trading shadow account 思路 |
| `report-renderer` | 写面向人的产业链研报和运维摘要。 | `loop_os/reporting.py`、`scripts/generate_physical_ai_chain_report.py` |
| `harness` | 校验仓库契约、产物质量和 provider 可用性。 | `loop_os/harness/checks.py`、provider smoke |

可借鉴的编排骨架是：候选实体合并、证据交叉验证、维度评分、core/watch/reject 分桶、missing evidence 显式化、投委会复核。AlphaForge 应吸收这个模式，但入口应从“选股池”升级为“产业链研究”。该模式只作为方法论，不构成对其他仓库代码或目录的运行依赖。

## 7. Packet 和 Schema 契约

AlphaForge 内部阶段之间传递 packet，而不是传递第三方对象或任意 dict。所有 packet 都应具备：

- `schema_version`：必填，破坏性变化必须升级版本；
- `generated_at`：必填，记录生成时间；
- `source_stage`：必填，记录来自哪个阶段；
- `evidence_ids` 或 `claim_ids`：用于说明 packet 中哪些结论有证据支撑；
- `warnings` / `errors`：可选但结构固定，禁止只写自然语言异常；
- `raw_refs`：可选，只能指向本仓库内 `data/raw/`、`runs/` 或 provider 输出摘要。

核心 packet：

| Packet | 生产者 | 消费者 | 最小职责 |
| --- | --- | --- | --- |
| `ProviderPacket` | provider adapter | evidence service / pipeline stage | 封装外部数据、来源、新鲜度、fallback 轨迹。 |
| `EvidencePacket` | evidence service | state service / report renderer | 记录 evidence card、claim index 和 claim 覆盖情况。 |
| `ResearchPacket` | pipeline stage | agent reviewer / report renderer | 汇总主题、产业链、候选、风险和证据缺口。 |
| `CandidatePacket` | stock analyzer | decision engine / external reviewer | 单个候选的业务、估值、技术、催化、反证和证据。 |
| `ReviewPacket` | AlphaForge | TradingAgents / Codex / Claude | 只读评审输入，不包含 state 写权限。 |
| `StateTransitionDraft` | state service | state machine / pre-commit harness | 表示拟写入 state 的变更和证据绑定。 |
| `ReportSourcePacket` | pipeline / evidence service | report renderer | 给 `report.md` 和 `source_data.json` 使用的结构化来源。 |

Packet 兼容规则：

- adapter 可以接收第三方格式，但输出必须转成 AlphaForge packet。
- 外部 Agent 返回的 review result 只能作为 `ReviewPacket` 的结果，不能直接写 state。
- packet 字段删除、重命名、语义变化都视为 breaking change，需要同步 tests 和 harness。
- 面向人的 `report.md` 不暴露 packet 字段名；packet 细节只进入 `source_data.json`、`runs/` 或 `data/raw/`。

## 8. 主循环契约

当前主入口是 `scripts/run_full_loop.py`。

当前 cycle 的实际流程：

1. 用 `a_stock_data` 获取 A 股行情。
2. 用 `global_stock_data` 获取全球市场行情。
3. 用 `investment_news` 获取新闻标题。
4. 用 `a_stock_data` 获取行业研报。
5. 分析行业研报，生成 preliminary research pipeline。
6. 运行 Codex / Claude / deterministic agent review。
7. 带上 agent context 再构建一次 pipeline。
8. 调用 `TradingAgents-astock` 风格 review packet。
9. 组合成本地 committee review 和最终 pipeline。
10. 写 evidence card 和 claim index。
11. 构造、校验、提交 state transition。
12. 写 `runs/`、`reports/daily/`（增量 inbox / 研究日志，非最终报告）、`data/raw/latest-full-loop.json`；最终结论由 route_cycle_reports 沉淀到 `reports/themes/<theme>/report.md`。
13. 生成产业链深度报告。
14. 运行 harness 和 provider smoke。

当前限制：state transition 已经是 `draft -> validate -> commit`，但完整 harness 仍在 state 写入之后运行。当前 MVP 可以接受；目标应升级为：

`draft -> state-machine validation -> pre-commit harness subset -> commit -> full-cycle harness`

## 9. Evidence、Claim 和 State 模型

Evidence 是所有状态变化的证据来源。

| 产物 | 职责 |
| --- | --- |
| `evidence/YYYY-MM-DD/ev-*.json` | 单个 evidence card，可来自行情、新闻、研报、产业链分析、个股补充、决策门禁、agent review。 |
| `evidence/YYYY-MM-DD/raw-index.json` | 当日 evidence id 增量索引。 |
| `evidence/YYYY-MM-DD/claim-index.json` | 从当日所有 evidence card 重建 claim-level 索引，支持追溯。 |

每个 evidence card 至少要包含：source name、source type、title、非空 claims、source locator 或 raw payload、freshness，以及可选的 related companies / related themes。

Claim 是 state 和报告的最小证据单元。当前 state 允许引用 `evidence_ids`；目标状态是所有会改变长期状态的字段都引用 `claim_ids`。claim 需要支持以下语义：

| 字段 | 含义 |
| --- | --- |
| `claim_id` | claim-level 稳定标识。 |
| `evidence_id` | 所属 evidence card。 |
| `claim` | 可被人工检查的一句话事实或判断。 |
| `stance` | `supporting`、`contradicting`、`neutral`、`stale`。 |
| `freshness` | `intraday`、`current`、`latest_available`、`stale` 等。 |
| `related_companies` | claim 关联公司。 |
| `related_themes` | claim 关联主题。 |
| `source_url` / `raw_path` | 可追溯来源。 |

State 文件保持粗粒度，一个文件一个根对象：

| State 文件 | 职责 |
| --- | --- |
| `research-state.json` | 研究 loop 状态、跟踪主题、下一步动作。 |
| `catalysts.json` | 催化剂生命周期和验证状态。 |
| `watchlist.json` | 候选、观察、模拟候选、拒绝等个股状态。 |
| `paper-portfolio.json` | 只用于模拟组合和复盘。 |
| `system-health.json` | supervisor 心跳和最新 loop 健康状态。 |

这本质上就是状态机：它记录 loop 当前走到哪个研究状态或验证步骤，而不是记录最终答案。

状态机最小契约：

| 对象 | 推荐状态流转 |
| --- | --- |
| Theme | `discovered -> tracking -> validated -> archived/rejected` |
| Catalyst | `discovered -> validating -> confirmed -> priced_in/expired/rejected` |
| Watchlist | `candidate -> watching -> paper_candidate -> rejected/archived` |
| PaperPortfolio | `reviewed -> simulated_position -> exited -> postmortem` |
| Thesis | `proposed -> supported/challenged -> validated/invalidated/priced_in` |

状态迁移规则：

- 新状态不得绕过 state machine。
- 已确认状态不能被新一轮信号自动降级，除非有明确 contradicting claim。
- 每次状态变化必须记录 `run_id`、`changed_at`、`reason`、`evidence_ids`，目标升级为 `claim_ids`。
- `state/*` 不保存大段原始数据；原始数据留在 `data/raw/`、`runs/` 或 evidence card。

## 10. Thesis Library 和 Memory 契约

AlphaForge 的长期价值来自论点库，而不只是每日报告。`memory/` 应逐步承载人的投资认知。

最小 thesis 模型：

| 字段 | 含义 |
| --- | --- |
| `thesis_id` | 稳定 id。 |
| `scope` | `theme`、`company`、`portfolio` 或 `strategy`。 |
| `subject` | 主题名、股票代码或策略名。 |
| `claim` | 论点正文。 |
| `status` | `proposed`、`supported`、`challenged`、`validated`、`invalidated`、`priced_in`。 |
| `supporting_claim_ids` | 支持该论点的 claim。 |
| `contradicting_claim_ids` | 反驳或削弱该论点的 claim。 |
| `last_reviewed_at` | 最近复盘时间。 |
| `next_verification` | 下一步要验证什么。 |

每日 loop 应回答：新信息支持了哪条 thesis、挑战了哪条 thesis、是否说明市场已经定价、是否触发失效条件。周度 loop 应回看 thesis 的验证质量，而不是只回看涨跌。

## 11. 报告产品契约

最重要的可见产物是 canonical 主题研报（方案 A：由每日 loop 持续精炼、永不覆盖人工正文）：

`reports/themes/<theme>/report.md`（例如 `reports/themes/physical-ai/report.md`）

> legacy：`reports/industry/<topic>-<YYYY-MM-DD>/` 是历史 / 手写快照，已迁移到 `reports/themes/`（留 `MOVED.md` 指针），harness 视为可选检查，不再作为主报告门禁。

文件约定（方案 A 实际形态）：

- `report.md`（**必备**，harness 门禁）：面向人阅读的正式研报，不出现内部路径、evidence id、payload 字段名；
- `assets/`（有图表时必备，harness 校验图片链接不坏）：产业链图、候选对比图、价格/估值图等可视化；
- `source_data.json`（可选伴随）：`physical-ai` 生成器会一并写出的结构化源数据，供后续 agent/程序消费；结构化源数据的权威落点仍是 `evidence/`、`runs/`、`data/raw/`，theme 目录下的副本仅为就近快照；
- `quality_report.json`（可选伴随）：报告质量检查结果。

> harness 只硬性要求 canonical `report.md` 存在且图片链接有效（见 `docs/reference/harness-checks.md` 的 `theme_report:*`）；`source_data.json` / `quality_report.json` 是可选伴随文件，缺失不阻断。

`report.md` 必须包含：

- 核心结论；
- 公开证据表，能附链接尽量附链接；
- 为什么今天选择这条产业链；
- 产业链全景图谱和价值分布；
- 上游稀缺、卡口和瓶颈分析；
- A 股公司映射，证据足够时至少 3 个核心候选；
- 每个候选的业务暴露、催化剂、估值、风险、技术结构、箱体/趋势、支撑阻力、买点区间、目标空间、失效条件；
- 正反证据；
- 下一步必须验证什么。

报告要给人看。内部路径、provider 名称、evidence id、决策门禁字段、payload 细节应留在 `runs/`、`data/raw/` 或 `source_data.json`。

质量指标建议：

- 公开链接覆盖率：核心证据表中可公开链接或 raw locator 的比例应被量化。
- 候选覆盖：除非报告明确证明该产业链当前不可投，否则核心候选不足 3 个应触发 warning。
- 候选证据：每个核心候选至少应有 supporting claim、risk claim、技术结构、估值口径和失效条件。
- 图表覆盖：正式产业链报告至少包含产业链图或候选对比图；缺图要写明原因。
- 反证覆盖：报告必须列出会推翻核心结论的条件。

## 12. 外部 Agent 项目接入方案

外部 Agent 项目不能拥有 AlphaForge 的状态写权限。它们只接收 packet，返回只读 review result。

### TradingAgents-astock

当前状态：已通过 `providers/open_source/tradingagents_astock.py` 轻量进入主 loop。

输入 packet：

- 已选产业链；
- 候选公司和证据摘要；
- 估值、技术、风险快照；
- 决策门禁结果；
- evidence gap。

输出：

- 多头、空头、风险、政策新闻、短线资金等角色意见；
- portfolio rating；
- trader action，但只作为研究意见；
- veto 和待补证据。

### Vibe-Trading

当前状态：已通过 `providers/open_source/vibe_trading.py` 的只读 strategy packet 进入主 loop；完整 runtime 仅在 `VIBE_TRADING_ENABLED=1` 时作为 sidecar 运行。

目标角色：

- 技术分析小组：支撑阻力、趋势、量能、买点区间挑战；
- 基本面和 financial rigor review；
- hypothesis registry 和 backtest/shadow 建议；
- 策略沙盒反馈：这套交易设想什么情况下失效。

它应该在 AlphaForge 已经选出候选公司后进入，而不是在原始数据扫描阶段进入。

### Vibe-Research

当前状态：已通过 `providers/open_source/vibe_research.py` 的只读 research packet 进入主 loop。

目标角色：

- 研究工作台和报告 workflow 参考；
- 证据组织和 source packet 整理；
- 报告覆盖度检查：哪些 claim 缺公开链接、哪些章节太薄、哪些图表缺失。

它应提升报告工作流和证据组织，不替代 AlphaForge 核心 loop。

## 13. Harness 和质量门禁

Harness 用来保证系统诚实、可维护、对 Agent 友好。

当前检查包括：

- 必需 state 文件可加载，且每个文件只有一个根对象；
- 必需 submodule 和 lock 记录存在；
- retained/provider skills 存在；
- `loop_os/` 没有直接 import `external/*`；
- latest loop artifact 包含 news scanner、article reader、hotspot selected、industry-chain methodology、stock analyzer、stock supplements、TradingAgents review、decision engine、portfolio analytics；
- latest report 不出现内部路径和操作性内部字段；
- industry report 包含深度报告关键章节、source data、quality report、assets；
- provider smoke 通过。

目标增强：

- 在写 `state/*` 前加入 pre-commit state harness；
- 状态变化从 evidence-id 绑定升级到 claim-id 绑定；
- 增加公开链接覆盖率评分；
- 增加图表/表格覆盖率评分；
- 每个核心标的必须通过技术分析深度门禁；
- 除非报告明确证明该产业链当前不可投，否则核心候选不足 3 个要触发质量警告。

Policy 对齐：

- `config/policy.yaml` 记录目标约束，不等于当前所有实现都已完全达到。
- 当前已实现 state transition 的 `draft -> validate -> commit`。
- 目标是补齐 pre-commit harness subset，使 `require_harness_before_state_write` 可以被严格解释为“写 state 前已完成必要 harness”。
- full-cycle harness 仍应在 commit 后运行，用于检查报告、provider、submodule 和运行产物完整性。

## 14. 安全和配置边界

AlphaForge 默认本地优先，但仍会使用 API key、CLI、缓存和第三方数据源。

安全规则：

- API key 只能来自环境变量、shell profile 或显式配置的 secret store，不能写入 `reports/`、`runs/`、`data/raw/` 或 `evidence/`。
- provider raw response 写盘前应避免包含 token、cookie、授权 header。
- harness 应增加 secret scan：检查常见 key/token 模式是否出现在报告、运行日志和 evidence 中。
- 外部 submodule 只读；需要 patch 时写 adapter，不改 submodule 内部源码。
- 外部缓存路径必须通过环境变量或 config 显式声明，不能隐式依赖旧仓库目录。
- 面向人的报告不得包含内部绝对路径、API key、provider 调试字段或 agent prompt。

## 15. 当前实现状态

已实现：

- 独立 `alpha-forge-research` 仓库；
- 主 loop 和 supervisor 模式；
- `a-stock-data`、`global-stock-data`、`investment-news`、`wen-cai`、`TradingAgents-astock` adapter；
- market data、news、review provider ports；
- 完整保留 `industry-chain-analysis` skill；
- evidence card 和 claim index 重建；
- state transition 的 draft / validate / commit；
- harness 检查；
- 日度报告和产业链报告产物；
- submodule lock 文档。

部分实现：

- `TradingAgents-astock` 当前是本地 structured review packet，不是完整 upstream runtime；
- `Vibe-Research` 和 `Vibe-Trading` 已进入只读 runtime insight provider，但不拥有 state 写权限；
- 技术面和估值分析已有雏形，但价格结构、箱体、趋势、支撑阻力、目标/失效位仍需加强；
- 报告质量门禁已有，但正式研报稳定对标高质量公开投研文章仍需继续打磨。

明确不做：

- 不隐式依赖 `alpha-forge-research` 以外的本地仓库、目录或旧工程结构；
- 不重新引入 `china-stock-analysis` 和 `china-stock-price-analysis`；
- skill 或 submodule 不直接写 `state/*`；
- 不做真实交易自动化。

## 16. 下一阶段架构优先级

P0：

- 以本文档作为仓库内最新架构源，保持 `AGENTS.md`、`config/providers.yaml`、`external/README.md`、`skills/README.md`、harness 常量同步。
- 继续收紧 Vibe-Trading / Vibe-Research 的 packet 契约和报告质量反馈，不扩大它们的 state 权限。
- 强化产业链报告生成器：公开链接、候选覆盖、图表、技术面和估值章节。
- 补齐 pre-commit harness subset，使 state 写入前至少完成 evidence、state-machine、policy 三类检查。
- 建立 secret scan，防止 key、token、绝对路径和内部 prompt 泄漏到面向人的报告。

P1：

- 拆分过大的 capability chain，形成清晰 stage 模块：
  `news_scanner`、`hotspot_scoring`、`industry_mapper`、`stock_analyzer`、`technical_analyzer`、`valuation_calculator`、`decision_engine`、`portfolio_analytics`。
- 状态变化从 evidence-id 绑定升级为 claim-id 绑定。
- 将问财作为一等 provider，用于候选池、因子、概念、技术结构验证。
- 固化 packet schema，并为 `ResearchPacket`、`CandidatePacket`、`ReviewPacket` 增加契约测试。

P2：

- 增加人的论点库：判断每条新信息是在支持、挑战、定价还是证伪哪条论点。
- 增加周度反馈 loop：回看之前判断是否被市场证实、证伪或提前定价。
- 引入 Vibe-Research 风格的报告 workflow/export 能力。
