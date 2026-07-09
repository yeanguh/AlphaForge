# 参考:Harness 校验清单(L3)

> 稳定事实。全部校验在 `loop_os/harness/checks.py` 的 `run_all()` 聚合;pre-commit 子集在 `loop_os/harness/precommit.py`。
> 入口:`python scripts/run_harness.py`。status = ok 当且仅当所有 check 为 ok/warn(无 error)。

## run_all() 校验(按执行顺序)

| 校验函数 | check 前缀 | 职责 |
| --- | --- | --- |
| `check_state_files` | `state:<file>` | 五个 state 文件可加载 |
| `check_submodules` | `submodule:*` | `.gitmodules` 与 `external/LOCKS.md` 一致 |
| `check_retained_skill_files` | `retained_skill:*` | `skills/industry-chain-analysis/SKILL.md` 存在 |
| `check_provider_skill_files` | `provider_skill:*` | `a-stock-data` / `global-stock-data` 的 `SKILL.md` 存在 |
| `check_loop_state_invariants` | `loop_state:*` | 状态机不变式 |
| `check_latest_loop_artifact` | `latest_loop:*` | 最新循环产物完整(含 `llm_agent_review`,无 LLM 时 warn) |
| `check_theme_reports` | `theme_report:*` | canonical 研报存在 + 图片链接不坏(方案 A 门禁) |
| `check_industry_analysis_report` | `industry_report:legacy_*` | legacy 快照,全部 warn 不阻断 |
| `check_no_core_external_imports` | `core_imports:*` | `loop_os/*` 未 import `external/*` |
| `check_no_secret_leaks` | `secret_scan:*` | 扫描敏感路径无密钥 |

## pre-commit 子集(precommit.py)

- `_check_policy`:`config/policy.yaml` 含 `allow_real_trading: false` 且 `require_evidence_for_state_change: true`。
- `_check_draft_shape`:state draft 结构合法。
- `_check_no_secrets_in_draft`:draft 内不含密钥。

## 扩展校验时

新增校验需:定义 `check_xxx() -> list[dict]`,每项 `{"check": "<prefix>:<name>", "status": "ok|warn|error"}`,在 `run_all()` 中 `checks.extend(check_xxx())`,并在 `tests/test_harness.py` 补测试。SOP 见 `../guidance/add-harness-check.md`。
