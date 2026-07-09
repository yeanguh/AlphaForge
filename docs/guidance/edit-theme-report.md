# SOP:编辑主题 canonical 研报(L3)

## 原则
- canonical 研报 = `reports/themes/<theme>/report.md`,是循环持续精炼的知识库。
- 编辑面向人阅读的深度研报,不要把过程日志塞进来(那属于 `reports/daily/`)。

## 步骤
1. 定位文件:`reports/themes/<theme>/report.md`。
2. 编辑内容。若引用图片,确保链接有效——harness 的 `theme_report:image_links` 会检查坏链。
3. 每个核心标的应覆盖:产业链位置、收入暴露假设、催化剂、估值、价格结构、趋势、箱体、支撑阻力、买点区间、失效条件、待验证证据。
4. 证据尽量附原始链接;每条会改变状态的判断都应有 evidence/claim 背书。

## 校验
```bash
python scripts/run_harness.py
```
- `theme_report:canonical:<key>` 为 ok。
- `theme_report:image_links` 无 error(无坏链)。
