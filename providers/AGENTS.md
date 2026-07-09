# providers/ 模块规则 (L2)

> `providers/` 是外部数据进入系统的**唯一入口**。`loop_os/` 通过这里(而非直接 `external/*`)获取数据。

## 职责边界

| 子目录 | 职责 |
| --- | --- |
| `ports/` | 端口抽象(接口定义),`loop_os` 依赖抽象而非实现 |
| `open_source/` | 开源子模块的运行时适配器(a_stock_data、global_stock_data、investment_news、tradingagents_astock 等) |
| `retained_skills/` | 保留技能的运行时转换代码(仅 `industry-chain-analysis`) |
| `reference/` | 仅参考、不进运行时循环的子模块文档 |

## 不变式(违反即错误)

1. external 子模块**只能**经 `open_source/*` 或 `reference/*` 访问。
2. ⛔ reference-only 子模块**禁止进运行时循环**。
3. 保留技能仅 `industry-chain-analysis`;⛔ 禁止复活 `china-stock-analysis` / `china-stock-price-analysis`。
4. 不得在仓库外引入隐式本地依赖;外部缓存必须经环境变量显式配置。
5. 保留技能入口在 `skills/*/SKILL.md`;运行时转换代码在 `providers/retained_skills/*`。

## 改动前

- 新增数据源 → 先在 `ports/` 定义端口,再在 `open_source/` 实现适配器,`loop_os` 只依赖端口。
- 改完跑 `python scripts/run_provider_smoke.py --live` 验证外部数据可用。
