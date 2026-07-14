# Agent Report · autonomous-low-altitude

## Run Context

| key | value |
| --- | --- |
| theme_key | autonomous-low-altitude |
| selected_theme | autonomous-low-altitude |
| payload_file | runs/2026-07-14/theme-pool-214323/cycle-001/themes/autonomous-low-altitude/result.json |
| finished_at | 2026-07-14T09:25:27.125747+00:00 |
| report_quality | {"passed": true, "missing_sections": [], "image_count": 7, "todo_count": 0, "char_count": 18531} |
| human_report_chars | 0 |
| human_report_images | 0 |

## Evidence IDs

- ev-market-cn-ecb303304235
- ev-market-cn-d4c86ae5c02b
- ev-market-cn-ccd39752789f
- ev-market-cn-4d409fe59d88
- ev-market-cn-afdb102bd839
- ev-market-cn-c4e56d6d6648
- ev-market-cn-1fa949b63c6b
- ev-market-global-128640804af8
- ev-market-global-049c731e195e
- ev-market-global-93f7d79441df
- ev-news-7f9615eac28a
- ev-news-e0ad687da034
- ev-news-6f89f1d5a93c
- ev-news-56ea934023aa
- ev-news-4e396b73bccf
- ev-news-d1ab609c1779
- ev-news-e33635acc647
- ev-news-d27c8e271749
- ev-news-2f377a3f3d4f
- ev-news-834887c59d8c
- ev-news-c841f9db1351
- ev-news-d3bc57d6ecb4
- ev-report-8346fa7ee2b3
- ev-report-1e1f36b6d1b8
- ev-report-689f1ef93928
- ev-report-cbc3c442c306
- ev-report-8287c40181e9
- ev-report-96a5d34de039
- ev-report-59ffe24e262d
- ev-report-a2a3aa81ae57
- ev-report-789a0ba698c9
- ev-report-d99fa4e3628d
- ev-report-1272fa7b171d
- ev-report-44f334357981
- ev-chain-0c8e4c6d6364
- ev-stock-supplement-ecb303304235
- ev-stock-supplement-d4c86ae5c02b
- ev-stock-supplement-ccd39752789f
- ev-stock-supplement-4d409fe59d88
- ev-stock-supplement-afdb102bd839
- ev-stock-supplement-c4e56d6d6648
- ev-stock-supplement-1fa949b63c6b
- ev-tradingagents-abeacda1dadf
- ev-provider-2aad6f37552f
- ev-provider-a01c47616610
- ev-provider-261dda401abc
- ev-decision-abeacda1dadf
- ev-review-abeacda1dadf

## Draft Routing

| key | value |
| --- | --- |
| report | reports/themes/autonomous-low-altitude/report.md |
| agent_report | reports/themes/autonomous-low-altitude/agent_report.md |
| draft | reports/themes/autonomous-low-altitude/report.cycle-draft-theme-pool-214323-cycle-001-autonomous-low-altitude.md |
| draft_archive | reports/themes/autonomous-low-altitude/drafts/theme-pool-214323-cycle-001-autonomous-low-altitude.md |
| theme_key | autonomous-low-altitude |
| seeded_canonical | False |
| quality | {"passed": true, "missing_sections": [], "image_count": 7, "todo_count": 0, "char_count": 18531} |
| returncode | 0 |

## Provider Notes

| 来源 | 状态 | 复用能力 | 本轮信息 | 降级策略 | 证据id |
| --- | --- | --- | --- | --- | --- |
| 公开数据工作台 | ok | a-stock-data、A股行情/财务数据清洗、报告证据组织 | 公开数据工作台 reused normalized A-share data for 7 symbols.；Symbols with usable K-line+financial coverage: 7. | 不阻塞；可用 | ev-provider-2aad6f37552f |
| 策略路由复核 | ok | 数据源优先级、公告/财务数据契约、交易风险门槛 | 策略路由复核 evaluated 7 decision rows.；Paper candidates=0, reject_or_wait=5. | 不阻塞；可用 | ev-provider-2aad6f37552f |
| 投委会复核 | ok | 公开数据/策略复核 | 组合复核 portfolio_rating=Underweight；组合复核 trader_action=Hold | 不阻塞；可用 | ev-provider-2aad6f37552f |

## Agent Reading Notes

- Human-facing report intentionally omits payload paths, provider internals, and evidence ids.
- Use this file plus source_data.json for traceability and rerun/debug context.
