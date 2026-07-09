# docs/ 索引(L1)

> 文档体系 L1 索引。上层入口:根 `AGENTS.md`(agent 路由/约束)、`README.md`(面向人)。
> 架构不变式与代码地图的权威源为 `docs/reference/architecture-invariants.md` + `docs/reference/module-map.md`;根 `ARCHITECTURE.md` 是 L0 导航入口(一屏概览,指向这两个文件)。
> 本文件负责把 agent 从"我要找 X"分流到 L3,渐进式披露、≤3 跳。

## 文档分层

| 层级 | 位置 | 职责 |
| --- | --- | --- |
| L0 | 根 `AGENTS.md` / `ARCHITECTURE.md` / `README.md` / `CLAUDE.md` | agent 路由 / 架构入口 / 面向人说明 |
| L1 | 本文件 `docs/AGENTS.md` | docs 索引与分流 |
| L3 | `docs/reference/` | 稳定事实(不变式、代码地图、schema、状态机、主题池、校验清单) |
| L3 | `docs/guidance/` | 可执行 SOP(跑循环、跑门禁、加主题、编辑研报、扩校验) |
| L3 | `docs/plans/` | ExecPlan 活文档(自包含、结果导向) |
| — | `docs/architecture-design.md` | 架构设计叙事(目标态 + 演进路线);稳定事实已抽取到 reference |

## 我要…… → 去看

| 需求 | 文档 |
| --- | --- |
| 查架构不变式(不能违反的规则) | `reference/architecture-invariants.md` |
| 查代码地图 / 模块边界 / 依赖方向 | `reference/module-map.md` |
| 查 evidence / claim / state 数据契约 | `reference/data-contracts.md` |
| 查主题池 / 研报路由(方案 A)规则 | `reference/theme-pool-and-reports.md` |
| 查 harness 全部校验及其含义 | `reference/harness-checks.md` |
| 跑一次完整研究循环 | `guidance/run-research-loop.md` |
| 跑质量门禁 / 提交前检查 | `guidance/run-harness.md` |
| 新增 / 调整一个投资主题 | `guidance/add-theme.md` |
| 编辑主题 canonical 研报 | `guidance/edit-theme-report.md` |
| 新增一个 harness 校验 | `guidance/add-harness-check.md` |
| **改代码 / 排查问题前的固定流程** | `guidance/change-and-debug-sop.md` |
| 新建一份 ExecPlan(任务计划) | 复制 `plans/TEMPLATE.md` → `plans/proposal/` |
| 看整体设计意图 / 演进方向 | `architecture-design.md` |
| 看进行中的优化计划 | `plans/active/` |

## 维护约定

- 稳定事实(不变式、代码地图、schema、状态流转、目录职责)沉淀到 `reference/`,单一事实源,不散落进 plan 或设计文档。
- 操作步骤沉淀到 `guidance/`,一篇一件事,新手可直接照做。
- 一次性优化/迁移写成 `plans/` 的 ExecPlan;完成即归档,不把状态留在 reference 里。
- 架构不变式 / 代码地图以 `docs/reference/architecture-invariants.md` + `docs/reference/module-map.md` 为权威源;根 `ARCHITECTURE.md` 仅作一屏导航入口,不一致以 reference 为准。
