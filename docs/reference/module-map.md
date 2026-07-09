# 代码地图 (L3 · 稳定事实)

> **本文件是代码地图的权威源。** 根 `ARCHITECTURE.md` 是 L0 导航入口(一屏概览);变更代码结构时两处同步更新,不一致以本文件为准。

## 顶层目录职责

| 目录 | 职责 | 维护者 |
| --- | --- | --- |
| `loop_os/` | 系统内核:领域逻辑 / 数据契约 / 状态机 / 校验 / 研报生成。⛔ 禁止 import `external/*` | AI |
| `providers/` | 外部数据唯一入口:`ports`(抽象)/`open_source`(适配器)/`retained_skills`/`reference` | AI |
| `skills/` | 业务技能入口 `SKILL.md`(industry-chain-analysis / a-stock-data / global-stock-data / wen-cai) | AI |
| `external/` | 子模块;只能经 `providers/*` 访问,禁止进运行时循环 | AI |
| `config/` | 配置驱动源:`theme_pool.json` `report_policy.json` `policy.yaml` `markets.yaml` `providers.yaml` `schedules.yaml` | 人 |
| `scripts/` | 运行入口:`run_full_loop` `run_harness` `run_provider_smoke` + hooks | AI |
| `playbooks/` | 投资框架 / 研究方法(策略层) | 人 |
| `memory/` `state/` | 论点库 / 研究状态(内核层) | 人 |
| `reports/` | 研报产物:`themes/`(canonical)`stocks/`weekly/`daily/`(inbox)`industry/`(legacy) | AI |
| `evidence/` `data/` `runs/` | 证据卡 / 原始数据 / 每轮运行产物 | AI |

## loop_os/ 子模块

| 子目录 | 关键文件 |
| --- | --- |
| `domain/` | `capability_chain.py`(主题→能力链→研究管线) `industry_chain.py` `market_analysis.py` `agent_review.py` `evidence_service.py` `state_update.py` |
| `schemas/` | `evidence` `packet` `catalyst` `review` `state` `watchlist` `provider` |
| `state_machine/` | `catalyst_state.py` |
| `harness/` | `checks.py`(`run_all()` 聚合) `precommit.py` |
| 根级 | `reporting.py` `report_router.py` `report_curation.py` |

## 依赖方向(单向)

```
scripts/  →  loop_os/  →  providers/ports (抽象)
                              ↑
                    providers/open_source (实现) → external/*
```

`loop_os/` 绝不反向依赖 `providers/open_source` 的具体实现,只依赖 `ports` 抽象;绝不直接 import `external/*`。
