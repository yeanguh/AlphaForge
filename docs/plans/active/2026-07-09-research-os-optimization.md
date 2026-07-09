# ExecPlan: Research OS 优化改造(Harness Engineering 落地)

> 状态:active
> 创建:2026-07-09
> 范围:research-os 仓库
> 原则:自包含 / 结果导向 / 弱实现细节、强验收门槛。以当前仓库最新实现为准。
> 基线(改造前):40 个单测全绿;scripts/run_harness.py(offline)通过,仅 latest_loop:llm_agent_review 为预期 warn(deterministic provider)。

本计划把此前的架构评估、新旧项目对比、P0-P3 修复项与 10 个 Harness Engineering idea 收敛为一份统一方案,按「三支柱 + 度量 + 飞轮」组织,并给出统一优先级、落地文件与验收门槛。

---

## 总体思路

research-os 的核心资产(证据契约、依赖边界、状态机、Ports&Adapters)方向正确,不推翻。短板在工程约束的可持续性:测试覆盖、提交可追溯性、主题硬编码、运行时文件入 git、健康状态一致性。用 Harness Engineering 把「一次性修复」升级为「自维持系统」。

执行顺序:P0 止血固基 -> P1 架构约束升级 -> P2 资产迁移 + 垃圾回收 -> P3 度量与飞轮。

---

## 支柱一:上下文工程(Context Engineering)

| 项 | 优先级 | 落地文件 | 验收门槛 | 状态 |
|---|---|---|---|---|
| ExecPlan 化本方案 | P0 | docs/plans/active/2026-07-09-research-os-optimization.md | 自包含、结果导向、含验收门槛 | 已完成(本文件) |
| L0-L4 渐进式文档 | P1 | README(L0)-> AGENTS.md(L1)-> docs/architecture-design.md(L2)-> skills 各 SKILL.md(L3)-> 代码注释(L4) | 每层单一职责,repo 为唯一事实源 | 部分(已有 L0/L1/L2) |
| 单一事实源治理 | P1 | 运行时状态描述统一由 state/system-health.json 生成 | 文档不手写运行时状态 | 待办 |

## 支柱二:架构约束(Architecture Constraints)

| 项 | 优先级 | 落地文件 | 验收门槛 | 状态 |
|---|---|---|---|---|
| 报错即指导 + pre-commit hook | P1 | scripts/pre_commit_hook.sh、scripts/install_hooks.sh | 提交即跑 harness+pytest;失败打印「问题->原因->修复命令」并 exit 1;--no-verify 可紧急绕过 | 已落地并自测 |
| 主题去硬编码 | P1 | config/report_policy.json + loop_os/harness/checks.py getter | 换主题只改配置不改代码;配置缺失/损坏回退默认值 | 已落地 + 5 个测试 |
| 主题池分层(core/watch/emerging) | P1 | config/theme_pool.json + loop_os/report_router.py 主题解析 | 15 主题分三层,别名可解析;emerging 默认进观察池,core/watch 达阈值才入正文;换主题只改配置 | 已落地 + 主题解析/分层测试 |
| 规则配置化 | P2 | 逐步把状态白名单、门禁阈值迁入 config | 规则变更走配置 | 待办(报告策略已迁) |
| L2 语义级门禁:结论-证据一致性 | P1 | loop_os/harness/checks.py 复用 validate_state_transition | 无效 evidence_id 的状态变更结论无法过门禁 | 待办(运行时已校验) |
| 协议录制回放(Cassette) | P1 | providers 适配层增录制/回放模式 -> cassette.json | 离线可跑全链路测试,无需 live key | 待办 |
| 测试覆盖恢复 | P0->P1 | tests 对照旧项目补齐 | 覆盖关键路径不回退 | 进行中(40->50) |
| 结构化可观测 | P2 | scripts/run_full_loop.py 输出结构化 cycle 日志 | 每轮阶段耗时/拦截点/异常可追溯 | 待办 |

## 支柱三:垃圾回收(Garbage Collection)

| 项 | 优先级 | 落地文件 | 验收门槛 | 状态 |
|---|---|---|---|---|
| 内容类型路由(runs=证据流水 / reports=最终资产) | P1 | loop_os/report_router.py、config/theme_pool.json、scripts/run_full_loop.py | 每轮 loop 证据按主题/个股/周报路由到对应最终报告(方案 A:themes 统一取代 industry,产业报告即主题报告,人工正文已物理迁移至 reports/themes/<theme>/report.md,遗留 industry/ 留 MOVED 指针、loop 不触碰);失败轮次只留 runs/;低质线索进观察池不覆盖正文;修正旧判断以软删除线归档不物理删除;daily 降级为增量 inbox;幂等 | 已落地 + 8 个测试 |
| 运行时文件出 git | P0 | .gitignore、git rm --cached 决策 | git status 不再被运行时数据污染;state 文件作 fixture 保留 | 待办(需用户确认取舍) |
| 证据/状态 GC | P2 | 定期清理/归档 expired/rejected 催化剂与过期 evidence | 状态文件规模可控(现 catalysts.json 128KB) | 待办 |
| 文档新鲜度巡检 | P3 | 巡检脚本比对文档与代码漂移 | 过期文档自动告警 | 待办 |

## 度量(Metrics)

| 项 | 优先级 | 落地文件 | 验收门槛 | 状态 |
|---|---|---|---|---|
| metrics.json + ACI | P3 | 记录门禁拦截次数、Agent 自愈率、修复循环次数、首次即绿率、可预防失败率 | 聚合为 AI Collaboration Index | 待办 |

## 优化飞轮(Flywheel)

| 项 | 优先级 | 落地 | 验收门槛 | 状态 |
|---|---|---|---|---|
| Problem Taxonomy 迭代飞轮 | P3 | 错误信号分类 -> 定位高频 -> 针对性加门禁/文档 -> 回流度量 | 每次迭代有可量化改进项 | 待办 |

---

## 已完成(本轮)

1. 主题去硬编码:checks.py 的 physical-ai-chain-analysis glob、forbidden_report_terms、required_terms 外置到 config/report_policy.json,带默认回退。
2. pre-commit hook(报错即指导):scripts/pre_commit_hook.sh 跑 offline harness + pytest,失败打印结构化「问题/原因/修复」并 exit 1;scripts/install_hooks.sh 负责安装。
3. 回归测试:新增 tests/test_report_policy_config.py(5 例),锁定配置化行为与回退语义。测试 40 -> 45 全绿。
4. 内容类型路由(Request C):新增 loop_os/report_router.py 的 route_cycle_reports,按内容类型把每轮 loop 证据路由到最终报告——主题证据追加到 reports/themes/<theme>/report.md(方案 A:产业报告即主题报告),个股/估值/公告追加到 reports/stocks/<symbol>/report.md,每轮复盘累积到 reports/weekly/YYYY-Www.md;失败轮次(status=error 或阻断 issue)完全跳过只留 runs/;强度未达阈值(<12)的线索进「待验证/反证/观察池」子分节,永不覆盖人工正文;全部通过 per-scope HTML 注释 marker 保证幂等。
5. daily 降级:reports/daily/latest-full-loop.md 由「最终报告」降级为「增量 inbox / 研究日志」,report_curation.py 新增 INBOX_BANNER 顶部横幅并改写 seed 标题,明确其非最终报告、最终资产以 themes/stocks/weekly 为准。run_full_loop.py 的 publish 阶段改调 route_cycle_reports。
6. 回归测试:新增 tests/test_report_router.py(5 例:失败轮不落最终报告、阻断 issue 视为失败、强证据路由到各最终报告并保留人工正文、弱线索进观察池、重复路由幂等)。测试 45 -> 50 全绿。

## 已完成(主题池 + 方案 A)

> **一句话语义(方案 A):** `reports/themes/` 是 loop 持续沉淀的 canonical final reports;`reports/industry/` 是 legacy / 手写快照(已迁移、留指针、harness 可选)。

7. 主题池分层落地:新增 config/theme_pool.json,15 个主题分三层——core(每天必扫:AI算力基础设施、数据中心电力、Physical AI、Agentic AI、国产算力、AI安全治理)、watch(每周更新:Edge AI、AI医疗、工业软件、AI应用商业化、自动驾驶/低空智能)、emerging(有事件再升权重:量子计算、空间/国防AI、AI金融基础设施、区块链/AI代理支付)。每主题含 tier/aliases/label,tier_policy 控制 watch_pool_default(emerging 默认进观察池,core/watch 需强度达阈值才入正文)。
8. report_router.py 新增主题解析层:_load_theme_pool / _theme_index / resolve_theme_key(别名如 "ai_physical_ai" -> "physical-ai")/ theme_tier / _tier_watch_pool_default / _theme_label,配置缺失回退内置默认。
9. 方案 A 路由语义:themes 统一取代 industry(产业报告即主题报告的一种)。人工产业正文一次性物理迁移到 reports/themes/physical-ai/report.md,遗留 reports/industry/physical-ai-chain-analysis-2026-07-09/ 留 MOVED.md 指针。日常 loop 只在 reports/themes/<theme>/report.md 的人工正文之上追加增量(证据日志/观察池/判断修正),永不覆盖正文,也不再读取/写入遗留 industry/。
10. 修正旧判断(软删除):_revision_lines 从 agent_review.invalidations / selected_chain.invalidated_claims 提取被反证的结论,以 ~~claim~~ 软删除线归档到「判断修正 / 已被反证」分节,保留审计痕迹,永不物理删除。
11. 回归测试:tests/test_report_router.py 扩展到主题解析与分层(test_theme_resolution_and_tier)、emerging 默认进观察池(test_emerging_theme_defaults_to_watch_pool)、修正软删除(test_revision_soft_marks_old_claim),并让失败轮次测试断言已迁移的 reports/themes/<theme>/report.md 人工正文不被 loop 追加(失败轮次只留 runs/),遗留 reports/industry/ 不被 loop 触碰。测试 50 -> 53 全绿(旧 5 例路由测试重构为 8 例)。
12. 语义固化到发现/打分(F3):config/theme_pool.json 每主题新增 discovery_keywords;loop_os/domain/capability_chain.py 的 THEME_KEYWORDS 改为从主题池加载(键为规范主题键如 physical-ai),配置缺失回退硬编码;article_reader / score_hot_industries 现在围绕主题池挖掘。_chain_tables / reporting._theme_cn 同步兼容新键。
13. harness 门禁迁移(F2/F1):新增 check_theme_reports——reports/themes/<key>/report.md canonical 门禁 + 全主题报告图片断链检查;check_industry_analysis_report 降级为 legacy 可选(缺失只 warn,不再 error 阻塞 run_all)。config/report_policy.json 新增 theme_report.canonical_required。
14. 资产迁移(F1):reports/themes/physical-ai/assets/ 补齐 5 张被引用图片,断链检查为 0。
15. daily 老文件补横幅(F4):update_rolling_report 对已存在但缺横幅的文件回填 INBOX_BANNER(banner_backfill_only 模式);现有 reports/daily/latest-full-loop.md 已回填,INBOX_BANNER 指向 reports/themes/<theme>/。
16. 文档统一(F5):README.md 报告目录段改为 themes(canonical)/stocks/weekly/daily(inbox)/industry(legacy);本 ExecPlan 统一为上面一句话语义。
17. 小清理(F6):scripts/run_full_loop.py 移除未使用的 update_rolling_report import(发布经 route_cycle_reports)。

## 验收记录

- python scripts/run_harness.py(offline):STATUS ok(providers 全绿)。
- python -m pytest -q:59 passed(含主题池 + 方案 A 回归;F1-F6 后新增 capability_chain 配置化与 theme_reports 门禁用例,53 -> 59)。
- pre-commit hook 自测:绿树 -> exit 0;人为破坏 report_policy.json -> 正确 BLOCKED + guidance + exit 1;恢复后复绿。

## 下一步(建议顺序)

1. P0 运行时文件出 git:需用户决定 state 文件与 evidence 的取舍(建议保留最小 seed 作 fixture,忽略按日期滚动的 evidence 目录)。
2. P1 Cassette 录制回放:让全链路测试脱离 live key。
3. P1 L2 结论-证据一致性门禁:把 validate_state_transition 上移进 harness。
4. P3 metrics.json + 飞轮:开始度量门禁拦截率/自愈率。
