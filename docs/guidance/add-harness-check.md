# SOP:新增一个 harness 校验(L3)

## 步骤
1. 在 `loop_os/harness/checks.py` 新增函数:
   ```python
   def check_your_thing() -> list[dict[str, Any]]:
       results = []
       # ... 判定逻辑
       results.append({"check": "your_prefix:some_name", "status": "ok"})  # or "warn" / "error"
       return results
   ```
2. 在 `run_all()` 中按合适顺序 `checks.extend(check_your_thing())`。
3. 若属于提交前必须拦截的规则,同步在 `loop_os/harness/precommit.py` 加子集校验。
4. 在 `tests/test_harness.py` 补测试:覆盖 ok / error 两种路径。

## 约定
- status 只用 `ok` / `warn` / `error`;只有 `error` 会让 `run_all` 整体失败。
- legacy / 非阻断项一律用 `warn`(参考 `check_industry_analysis_report`)。
- 配置驱动优先:阈值/开关放 `config/*.json`,代码带内置 fallback(参考 `theme_report.canonical_required`)。

## 校验
```bash
uv run python -m pytest tests/test_harness.py -q
uv run python scripts/run_harness.py
```
