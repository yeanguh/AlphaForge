# SOP:跑质量门禁 / 提交前检查 (L3 · 操作手册)

> 任何改变 state 的提交前都要过 harness。入口 `scripts/run_harness.py`,聚合逻辑在 `loop_os/harness/checks.py::run_all()`。

## 执行

```bash
uv run python scripts/run_harness.py            # 基础校验
uv run python scripts/run_harness.py --live     # 附带 live provider smoke
```

- 结果写入 `runs/<date>/harness.json` 并打印。
- 退出码:`status == "ok"` → 0;否则 → 1(可用于 CI / hook 拦截)。
- 状态判定:所有 check 为 `ok` 或 `warn` 即 `ok`;出现 `error` 即失败。

## 主要检查项

> 完整校验清单见 `../reference/harness-checks.md`;下面只列最常触发的。

| check | 守护什么 |
| --- | --- |
| `state:*` | 必需 state 文件可加载 |
| submodule / import 检查 | 不变式 1、2(禁止 `loop_os` import `external/*`) |
| `theme_report:canonical:<key>` | 方案 A canonical 研报存在(`check_theme_reports`) |
| `theme_report:image_links` | 研报图片链接不破损 |
| `industry_report:legacy_*` | legacy 产业研报(全 `warn`,可选) |
| secret 扫描 | AGENTS.md / config / docs / reports 等无泄漏密钥 |

## Pre-commit Hook

```bash
bash scripts/install_hooks.sh    # 安装 git pre-commit hook(调用 scripts/pre_commit_hook.sh)
```

hook 会在提交前跑 harness;失败即阻断提交(报错即指导 → 按提示修复后重试)。

## 失败处置

- `error` 出现 → 看 `runs/<date>/harness.json` 里对应 check 的 `error` 字段,定位到 `checks.py`。
- canonical gate 失败 → 缺 `reports/themes/<theme>/report.md`,补齐或调整 `config/report_policy.json` 的 `canonical_required`。
- ⛔ 不要盲目重试;先读报错再修。
