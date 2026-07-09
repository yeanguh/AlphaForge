# loop_os/ 模块规则 (L2)

> `loop_os/` 是系统内核(领域逻辑 + 契约 + 状态机 + 校验)。改这里前先读 `docs/reference/architecture-invariants.md` 的架构不变式(根 `ARCHITECTURE.md` 为一屏导航入口)。

## 职责边界

| 子目录 | 职责 | 关键文件 |
| --- | --- | --- |
| `domain/` | 领域服务:能力链、产业链、行情分析、评审、证据、状态更新 | `capability_chain.py` `industry_chain.py` `market_analysis.py` `agent_review.py` `evidence_service.py` `state_update.py` |
| `schemas/` | 数据契约(Pydantic/dataclass) | `evidence.py` `packet.py` `catalyst.py` `review.py` `state.py` `watchlist.py` `provider.py` |
| `state_machine/` | 状态流转规则 | `catalyst_state.py` |
| `harness/` | 质量门禁:`checks.run_all()` 聚合 + `precommit` | `checks.py` `precommit.py` |
| (根级) | 研报生成与路由(方案 A) | `reporting.py` `report_router.py` `report_curation.py` |

## 不变式(违反即错误)

1. ⛔ **禁止 `import external/*`**。外部子模块只能经 `providers/open_source/*` 或 `providers/reference/*` 访问。
2. 每个改变 state 的 claim 必须有 evidence id 背书。
3. state 变更必须通过 `state_machine/*` 规则 + `harness/*` 校验。
4. 研报 canonical 产物 = `reports/themes/<theme>/report.md`(方案 A);`reports/daily/` = inbox,`reports/industry/` = legacy。
5. **config-driven + hardcoded fallback**:主题/口径优先读 `config/`(theme_pool、report_policy),config 缺失时回退到模块内 `_FALLBACK_*`。新增主题改 `config/theme_pool.json`,不要硬编码。

## 改动前

- 先 `python scripts/run_harness.py` 看基线,改完再跑一次确认 `status: ok`。
- 加新校验 → 写进 `harness/checks.py` 并 wire 进 `run_all()`。
