# SOP:新增 / 调整投资主题(L3)

## 步骤
1. 编辑 `config/theme_pool.json`,在 `themes` **字典**中新增一个主题键(不是数组):
   ```json
   "your-theme-key": {
     "tier": "core | watch | emerging",
     "label": "中文名",
     "aliases": ["别名1", "别名2"],
     "discovery_keywords": ["关键词1", "关键词2"]
   }
   ```
2. 三处消费方均 config-driven,通常无需改代码;仅当需要为新主题定制产业链表时,在 `loop_os/domain/capability_chain.py` 的 `_chain_tables` 分支按主题键补逻辑。
3. 若新主题要成为 canonical 门禁对象,在 `config/report_policy.json` 的 `theme_report.canonical_required` 追加该键。

## 校验
```bash
uv run python -m pytest tests/test_capability_chain.py -q
uv run python scripts/run_harness.py
```
- `test_theme_keywords_loaded_from_theme_pool` 应看到新增后的主题数。
- harness 无 error。

## 注意
- `discovery_keywords` 直接影响发现打分,填该主题最具区分度的术语。
- 主题键用小写连字符(如 `ai-compute-infra`),与现有 15 个保持一致。
