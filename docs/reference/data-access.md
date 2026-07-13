# 数据接入契约 (L3 · 稳定事实)

> 本文件记录 Research OS 的可迁移数据入口、权限边界、运行方式和降级顺序。
> 运行时代码仍以 `providers/*` 为唯一边界；外部 skill 可作为 Codex 可读参考,
> 但不能直接进入 `loop_os/` runtime loop。
> 具体机器、账号、token 的实时可用性以 `scripts/run_provider_smoke.py --live`
> 和 `scripts/run_harness.py --live` 的运行结果为准,不要写死在架构文档里。

## 总体原则

- Runtime 优先走 `providers/open_source/*` 和 `providers/ports/*`。
- `skills/*` 是本仓库内的 skill 入口；`.codex/skills/*` 是 workspace-local 扫描用符号链接,
  不提交到 git。
- `external/ch-skills/skills/*` 是 reference-only 外部 skill 集合；可手工读取或手工运行,
  但接入 runtime 前必须新增 provider adapter 或 documented reference boundary。
- 需要 token/key 的能力只能作为增强项。缺失或权限不足时,降级到公开源、仓库内缓存或显式 evidence gap。
- 不引入仓库外隐式缓存；外部缓存必须用环境变量显式配置,例如 `RESEARCH_OS_A_DATA_DIR`。
- 建议命令入口为 `uv run python ...`,以项目锁定依赖运行脚本。

## 环境变量

| 项 | 要求 | 说明 |
| --- | --- | --- |
| `TUSHARE_TOKEN` | Tushare Pro 能力需要 | token 权限随账号变化；任何接口进入报告或 state 前都必须由 smoke 或 evidence 证明。 |
| `IWENCAI_API_KEY` | WenCai/iWenCai 能力需要 | 用于 `providers/open_source/wen_cai.py` 和 `a-stock-data` 的 iwencai 子能力。 |
| `IWENCAI_BASE_URL` | 可选 | 覆盖 WenCai API endpoint；缺省值由 provider adapter 决定。 |
| `RESEARCH_OS_A_DATA_DIR` | 可选 | 显式声明 A 股本地缓存根目录；未配置时只能使用仓库内默认缓存路径。 |

## 运行时 Provider

| Provider | Skill/来源 | Runtime adapter | Token/key | 用途 |
| --- | --- | --- | --- | --- |
| `a-stock-data` | `skills/a-stock-data` | `providers/open_source/a_stock_data.py` | 大多数公开源零 key;iwencai 子能力需 `IWENCAI_API_KEY` | A 股统一入口。优先复用 Tushare Pro 结构化数据,并降级到腾讯/东财/AKShare/本地缓存。 |
| `tushare` | Tushare Pro SDK | `providers/open_source/tushare_provider.py` | `TUSHARE_TOKEN` | A 股高优先级结构化源: 基础资料/交易日历、行情/估值、财务三表、财务指标、主营构成、分红、股东/质押/回购、龙虎榜、融资融券、指数/基金。 |
| `global-stock-data` | `skills/global-stock-data` | `providers/open_source/global_stock_data.py` | 无个人 token | 美股/港股/全球行情与跨市场验证。 |
| `wen-cai` | `skills/wen-cai-1.0.0` | `providers/open_source/wen_cai.py` | `IWENCAI_API_KEY` | 自然语言财务字段、研报/公告/新闻/选股/板块查询。 |
| `investment-news` | `external/investment-news` | `providers/open_source/investment_news.py` | 无个人 token | 精选资讯源 headline ingestion。 |

## External Reference Data Skills

| External skill | 路径 | 依赖 | 接入定位 |
| --- | --- | --- | --- |
| `tushare-data` | `external/ch-skills/skills/tushare-data` | `tushare` Python 包 + `TUSHARE_TOKEN` | Reference/manual。运行时统一走 `providers/open_source/tushare_provider.py`; 外部 skill 只作为接口组织方式参考。 |
| `stock-market-data` | `external/ch-skills/skills/stock-market-data` | `akshare`, `pandas` | Reference/manual。交易日、指数、板块、涨停池、北向、个股日线。 |
| `financial-data-fetcher` | `external/ch-skills/skills/financial-data-fetcher` | Tushare 主源 + AKShare fallback | Reference/manual。ETF、轻量财务摘要、Tushare/AKShare 财务编排参考。 |

## 财务三表与 `income` 替代路径

Tushare Pro 是当前 A 股结构化数据的高优先级来源。利润表数据仍不应强依赖
某个 Tushare token 或单一网络状态,而应按以下路径降级:

| 优先级 | 路径 | 能力 | 说明 |
| --- | --- | --- | --- |
| 1 | `providers/open_source/tushare_provider.py::fetch_financial_bundle` / `providers/open_source/a_stock_data.py::fetch_financials_tushare` | Tushare Pro 标准三表、指标、主营构成、业绩预告/快报、审计意见、分红 | 高优先级路径;权限、IP、空数据必须显式返回状态,不得静默补值。 |
| 2 | `providers/open_source/a_stock_data.py::fetch_financials` | 东财 F10 `income` / `balance` / `cashflow` / `indicators` | Tushare 不可用时的公开源回退;可拿完整利润表字段。 |
| 3 | `providers/open_source/wen_cai.py::query("finance", ...)` | 自然语言指定财务字段 | 适合快速交叉验证和字段级查询。 |
| 4 | `external/ch-skills/skills/stock-market-data/scripts/fetch_financial_data.py --mode stock` | AKShare 财务摘要与比率 | 适合轻量摘要;不是完整标准利润表。 |
| 5 | 公司公告/巨潮/交易所披露 | 权威原始来源 | 重大报告结论或 state 变更的最终 evidence 锚点。 |

## 推荐降级顺序

### A 股行情/估值

1. Tushare `daily` / `daily_basic` / `moneyflow` / `top_list` / `margin_detail`。
2. `providers/open_source/a_stock_data.py` 腾讯公开行情。
3. 东方财富 push2 / F10。
4. AKShare fallback 或本地缓存。
5. 明确标记 evidence gap。

### A 股财务

1. Tushare `fetch_financial_bundle` / `fetch_financials_tushare`。
2. `a-stock-data` 东财 F10 三表。
3. WenCai 字段级查询交叉验证。
4. AKShare 财务摘要。
5. 公告/PDF 原文作为关键结论锚点。

### ETF / 板块 / 市场情绪

1. `stock-market-data` / `financial-data-fetcher` 的 AKShare 路径。
2. `a-stock-data` 公开源补充。
3. 若接口失败,记录 provider warning,不要静默补值。

### 全球股票

1. `global-stock-data` Yahoo chart。
2. 腾讯美股/港股行情。
3. 其他公开源 fallback。

## 可用性验证

```bash
uv run python scripts/run_provider_smoke.py --live
uv run python scripts/run_harness.py --live
```

- smoke/harness 结果是环境快照,应写入 `runs/<date>/`,不写入架构契约。
- 若某个 key-gated provider 不可用,loop 必须降级、记录 warning 或显式 evidence gap。
- 若要把 external reference skill 接入 runtime,先新增 `providers/open_source/*`
  adapter 和 harness 覆盖,再更新本文档。
