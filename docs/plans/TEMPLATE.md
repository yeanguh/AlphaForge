# ExecPlan:<用一句话说清要做什么>

> 状态:proposal | active | completed
> 创建:YYYY-MM-DD
> 范围:research-os 仓库(或更具体的模块)
> 基线(改造前):<可观测事实,如「N 个单测全绿;scripts/run_harness.py 通过,仅 X 为预期 warn」>

<!--
这是 ExecPlan 模板。每份计划必须同时满足 4 条原则(Harness Engineering 规范):
- 自包含:一个对仓库毫无了解的 agent 仅凭本文件就能接力完成,不依赖外部文档或先前对话。
- 活文档:边干边更新——完成一步更新进度,发现意外记录证据,做了决策写明理由。中断后新 agent 从断点续接。
- 结果导向:验收标准用可观测行为描述(如「全部 PASS,0 skipped」),而非模糊的「功能正常」。
- 新手友好:术语就地解释,路径用仓库相对路径,不说「如前所述」。
核心哲学:弱实现细节、强验收门槛。人定义「做什么」和「怎么算做完」,agent 自主决定「怎么做」。
新建流程:复制本文件到 docs/plans/proposal/YYYY-MM-DD-<slug>.md,填好后挪到 active/,完成后挪到 completed/。
-->

## 背景与目标

<为什么做、要达到什么结果。链接到相关 reference:docs/reference/*、根 ARCHITECTURE.md。>

## 待办清单

| 项 | 优先级 | 落地文件(仓库相对路径) | 验收门槛(可观测) | 状态 |
|---|---|---|---|---|
| <子任务> | P0/P1/P2 | `path/to/file` | pytest 目标用例全绿 | 待办 / 进行中 / 已完成 |

## 验收(整体)

- [ ] 在 .venv 环境下 `python -m pytest -q` 全部 PASS,0 skipped
- [ ] `python scripts/run_harness.py` 无 error(所有 check 为 ok/warn)
- [ ] pre-commit hook 退出码为 0

## 进度日志(活文档,倒序追加)

- YYYY-MM-DD:<做了什么 / 发现了什么 / 为什么这样决策>
