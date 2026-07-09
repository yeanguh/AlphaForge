# Data Sourcing

Single reference for collecting evidence for an industry upstream/downstream analysis and A-share company exposure mapping. Covers source priority, the evidence checklist, the public-data adapters, and failure handling. For module-level source priority across the stock-analysis skills, also read `../../daily-a-share-news-impact/references/data-source-matrix.md`.

The adapter patterns described here are implemented once in `scripts/public_data.py`; prefer importing those helpers over re-writing safe imports, baostock login/logout, or source-trail bookkeeping per output directory. Run `scripts/check_data_sources.py` first to see which adapters are reachable in the current network before deciding online vs. cache.

## Source Priority

1. Primary policy and regulatory sources: State Council, NDRC, MIIT, MOF, PBOC, CSRC, exchange announcements, local government releases, and official standards.
2. Official statistics and trade data: National Bureau of Statistics, Customs, industry associations, exchange inventory data, and commodity exchange data.
3. Company evidence: annual reports, interim reports, prospectuses, investor relations records, order announcements, capacity announcements, and official websites.
4. Industry and market data: association reports, reputable sell-side reports if available to the user, AkShare/CNINFO, Tongdaxin/mootdx, Tencent/Eastmoney quote data, baostock/adata/efinance style public datasets, commodity price providers, and credible specialist media.
5. News confirmation: Reuters, Caixin, Cailian Press, Xinhua, Securities Times, Shanghai Securities News, company-confirmed press releases, and other reputable outlets.

The evidence hierarchy for company exposure is: filings > official/company releases > industry association/statistics > public-data adapters > media/third-party estimates.

## Minimum Evidence Checklist

Collect enough evidence to answer these questions:

- Boundary: what exact product, service, technology, commodity, or use case is included?
- Demand: who buys it, what drives demand, and what are the measurable demand indicators?
- Supply: who produces it, what are capacity, utilization, inventory, and expansion plans?
- Price: what price, spread, or cost indicator best represents the chain?
- Policy: what policies or standards materially change demand, supply, subsidy, approval, or compliance cost?
- Key sub-segments: which upstream, midstream, and downstream links hold the highest value share, cost share, margin, or bottleneck importance?
- Upstream completeness: what are the product BOM inputs, process materials, board/package materials, resource feedstocks, consumables, equipment, and adjacent infrastructure? Which are core, important, adjacent, commodity background, or out of scope?
- Bottleneck technology: which links involve卡脖子 constraints, import substitution,国产化率, scarce equipment/materials/software/IP, or customer validation barriers?
- Competition: who controls the scarce resource, core technology, channel, license, customer relationship, or cost advantage?
- Listed exposure: which A-share companies have direct revenue, capacity, order, reserves, customers, product certification, patents, or commercialized technology in each key sub-segment?
- Risks: what could break the demand, price, policy, supply, or company-exposure thesis?

## Company Mapping Rules

Classify each company by exposure strength. The full exposure tiers and required fields live in `a-share-screening.md`; this is the data-collection summary:

| Level | Meaning | Evidence Required |
| --- | --- | --- |
| Direct core | Main business sits in a key sub-segment and company appears core in that link | Revenue/proportion, capacity, product, reserves, customer, market share, or patents disclosed by company or filing |
| Direct partial | Material segment exposure but not dominant | Segment revenue/proportion, product line, order, or certified customer |
| Indirect | Supplier, customer, equipment, service, or substitute relationship | Explainable chain relationship with source support |
| Concept-only | Market label without confirmed operating exposure | Do not include in the main company table except as "待验证概念" |

Never let public-data labels such as "概念板块成分" or "行业板块成分" become proof of industrial exposure. They are discovery signals only; verify decisive claims with filings, main-business evidence, capacity/order disclosures, patents, product pages, or official releases before classifying a company as core.

## Verification Habits

- Check dates. Use the newest available annual/interim report and current policy status. Do not rely on memory for market size, prices, capacity, policy status, executives, or listed-company exposure.
- Cross-check module-appropriate public data where they provide similar data. For quotes and valuation use mootdx, Tencent, Eastmoney, AkShare, baostock, and efinance in that order; for announcements use CNINFO/Giant Tide through AkShare first. If sources disagree or one endpoint fails, keep the successful result but mark the source and confidence; do not silently blend them.
- Check units. Normalize tons, GWh, GW, wafers, vehicles, RMB, USD, and capacity utilization before comparing.
- Distinguish installed capacity, effective capacity, shipments, sales, and orders.
- Distinguish gross margin, operating margin, spread, and profit per unit.
- Distinguish revenue share, segment revenue share, capacity share, shipment share, market share, and customer/order exposure.
- For cyclical industries, check inventory, capex cycle, commodity prices, and downstream operating rates.
- For technology chains, check adoption rate, technical route, standards, patents, and customer validation.
- For physical technology chains, run a material keyword expansion pass before company ranking (see `upstream-discovery.md` for the keyword list). If a material is named by the user, classify it explicitly as core, important, adjacent, or out of scope.
- For policy themes, check implementation rules, funding source, eligible participants, and timeline.

## Public Data Adapters

| Tool | Use For | Caution |
| --- | --- | --- |
| mootdx / 通达讯 | Realtime quote, order book, K-line, transactions, basic snapshot, announcement-summary discovery | Best for行情; not proof of company exposure; server selection can fail |
| Tencent finance | PE/PB/market cap, no-key realtime quote, market-cap fallback | Good valuation complement to Tongdaxin; quote fields must be parsed defensively |
| AkShare | Industry board lists, board fund flow, A-share quotes, financial indicators, business introductions, historical prices, Eastmoney research/news, CNINFO announcements/company profiles | Some Eastmoney/THS/CNINFO endpoints can return `RemoteDisconnected` or change schema |
| iwencai / 艾问财 | Natural-language cross-theme research-report and topic discovery when API Key is configured | Optional credentialed source; without key use generated query text or user-exported results |
| CNINFO / 巨潮 | Original A-share filings, announcements, reports, and company profiles | Authoritative for announcements; prefer AkShare wrapper first, direct/manual search if wrapper fails |
| baostock | Backup for A-share daily K-line, adjustment factors, stock basics, and historical quote cross-checks | Requires login/logout; keep calls low-frequency and candidate-list based |
| adata | Probe only — inspect top-level API surface to see which functions are available in the installed version. No production adapters are built on adata yet; use AkShare and baostock as the primary public-data adapters. | API surface varies by version; do not rely on adata for critical data paths |
| efinance | Eastmoney quote snapshot and company base information backup | Endpoint can rate-limit or disconnect; use only for shortlisted companies |
| SEC EDGAR | Overseas supplier filings and company submissions, e.g. NVIDIA/Marvell/Broadcom/Coherent | Requires descriptive User-Agent; use for global supply-chain evidence, not A-share exposure |
| Local repo cache | Previously assembled daily brief, cached financial JSON, generated source trails | Use only with date labels and confidence notes |

Treat public-data packages as adapters, not primary proof for company exposure. Use them sparingly to discover board constituents, market heat, quotes, financial snapshots, main-business text, announcements, and cross-checks; verify decisive claims with filings, official releases, or source trails.

## Additional Free Public Sources

Use these before paywalled databases when the report needs stronger evidence:

| Source | Best For | Access Pattern | Evidence Strength |
| --- | --- | --- | --- |
| 巨潮资讯 CNINFO | A-share annual/interim reports, announcements, company profiles, investor relations records | AkShare CNINFO helpers or direct website search | High for company disclosure |
| 上交所/深交所/北交所公告 | Exchange-filed announcements and regulatory letters | Official websites or CNINFO mirrors | High |
| 国家统计局 NBS | Macro demand, production, investment, price indicators | Official website / public tables | High |
| 海关总署 GACC | Import/export quantity and value for resources, equipment, components | Official customs releases / HS-code tables | High |
| 工信部 MIIT、信通院 CAICT | Telecom, electronics, AI infrastructure, industrial policy and industry operation data | Official releases and reports | High/Medium-High |
| 行业协会 | Capacity, shipments, standards, industry definitions | Association releases, e.g. CCSA, SEMI, CPCA, PV/Chemical/Auto associations by industry | Medium-High |
| 公司官网/IR/产品白皮书 | Product routes, customer cases, certifications, capacity announcements | Official company pages and IR documents | High for product existence; Medium for market claims |
| SEC EDGAR | Overseas supplier filings, risk factors, segment data | `try_sec_submissions(cik)` and EDGAR pages | High for overseas filings |
| OFC/CIOE/IEEE/JEDEC/OCP/UCIe/CXL等会议或标准组织 | Technology route, standards, product demonstrations | Public programs, press releases, standards pages | Medium-High |
| Yahoo/Stooq/yfinance style sources | Overseas quotes and price cross-checks | Optional future adapter | Medium; market data only |

### Reusable Adapters in `scripts/public_data.py`

Prefer these pre-built helpers over writing ad-hoc adapter code per report. All follow the same `(payload, error)` return pattern and include one transient retry.

| Helper | Purpose | When to Use |
| --- | --- | --- |
| `try_akshare_board_cons(board_name)` | Industry board constituent list | When the theme maps to a clean 申万/东方财富 industry vertical |
| `try_akshare_concept_cons(concept_name)` | Concept board constituent list | When the theme is thematic (创新药、AI、算力、机器人 etc.) and not a clean industry |
| `try_akshare_board_fund_flow(name, is_concept=False)` | Board-level fund-flow snapshot | Gauging market heat around a chain theme (heat signal only, not exposure proof) |
| `try_akshare_main_business(code)` | Single-stock main-business text (akshare THS endpoint) | Direct akshare call; prefer `try_main_business` as the standard entry |
| `try_main_business(code)` | Standard main-business entry point (akshare THS) | Default choice for company exposure checks; returns `((payload, error), source)` where source is `"akshare"` or `"none"` |
| `try_akshare_cninfo_disclosure(code, keyword, category, start_date, end_date)` | CNINFO announcement search | Annual reports, order/capacity/customer announcements, filings evidence |
| `try_akshare_individual_notice(code, notice_type, begin_date, end_date)` | Eastmoney single-stock announcement backup | Backup when CNINFO endpoint fails |
| `try_akshare_cninfo_profile(code)` | CNINFO company profile | Company identity, industry, profile cross-check |
| `try_baostock_daily(code, start, end)` | Daily K-line backup via baostock | Cross-checking prices or when akshare quote endpoints fail |
| `try_efinance_quote_snapshot(code)` | Eastmoney single-stock quote snapshot | Backup quote/market-cap/valuation snapshot for shortlisted A-shares |
| `try_efinance_base_info(code)` | Eastmoney single-stock base info | Company base info and valuation cross-check |
| `try_adata_probe()` | Inspect adata top-level API surface | Probe only — once per run to discover which adata functions are available; not a data source |
| `try_sec_submissions(cik)` | SEC EDGAR company submissions | Overseas supplier filings and recent forms |
| `SourceTrail` class | Accumulate adapter outcomes and write `source_data.json` | All runs; record every adapter call |
| `SourceTrail.from_health_check(report)` | Pre-fill trail from `check_data_sources.py` output | Skip re-probing adapters already known to be unreachable |
| `render_company_mapping_table(rows)` | Render the canonical 9-column company-mapping table | Standard / Report mode company output |
| `render_chain_overview_table(rows)` | Render the 4-column chain-overview table | Light mode structure summary |
| `render_upstream_material_table(rows)` | Render the 7-column upstream-material discovery table | Standard / Report mode upstream pass |
| `render_core_value_distribution_table(rows)` | Render the chain-link value/BOM distribution table | Standard / Report mode section before company mapping |
| `render_source_trail_table(entries)` | Render the 7-column source-trail table for diagnostics | Use in run logs or debugging only; do not paste into reader-facing reports |

**Industry board vs. concept board rule**: Start from the user's theme. If it maps to a clean industry vertical (e.g. "半导体" → 半导体行业), try `try_akshare_board_cons` first. If it is thematic or cross-industry (e.g. "创新药", "AI", "算力", "机器人"), use `try_akshare_concept_cons`. If neither produces results, switch to top-down company discovery from filings and known leaders.

### Low-Frequency Access Policy

All public data adapters in this skill are best-effort and must be used politely:

- Query only the smallest candidate set that can answer the task.
- Prefer one batched/small pull over many repeated single-stock pulls when the adapter supports it.
- Avoid repeated full-market downloads in the same run; cache results to `source_data.json` or a local run artifact.
- Retry a cheap transient error at most once (`public_data.py` does this), then switch adapter or local cache.
- Add a small sleep/backoff when looping over multiple stocks or material keywords.
- Record adapter name, function, queried timestamp, row count, status, and failure reason in the source trail.

### Dependency Notes

The main adapters are already declared in the repository `pyproject.toml` (`akshare`, `baostock`, `adata`, `efinance`). If a fresh environment is missing them:

```bash
/usr/local/bin/uv add backtrader pyfolio baostock adata efinance
```

If any public-data import or endpoint call fails, do not block the analysis. Fall back to another adapter, local cached data, or primary filings and record the failure.

### Recommended Collection Order

1. Run `scripts/check_data_sources.py` to see which adapters are reachable. Identify the industry/theme and collect current heat using local reports, AkShare board funds, or authoritative news.
2. Build the chain map from industry logic and high-authority sources; public board constituents are only discovery candidates.
3. For candidate A-share companies, collect at least one of:
   - annual/interim report segment revenue,
   - main-business/product evidence from AkShare/adata plus company filing/website,
   - disclosed capacity/order/customer/patent/certification evidence,
   - reputable third-party market-share evidence.
4. Cross-check quote, PE/PB/PS, volume, and trend with AkShare/baostock/adata/local snapshots before stock-level follow-through.
5. Save a compact source trail with tool, function, date, row count, and failure message via `public_data.SourceTrail` into `source_data.json`. Do not paste raw adapter call logs into the reader-facing report.

### Failure Handling

| Failure | Response |
| --- | --- |
| `RemoteDisconnected` / connection reset | Retry once only if the call is cheap; then use fallback and mark confidence |
| Empty DataFrame | Check code format, market suffix, board name, and date; then fallback |
| Schema mismatch / missing columns | Inspect returned columns; avoid hard-coded assumptions; mark missing fields |
| baostock login/query failure | Logout if possible; switch to AkShare/adata/local cache |
| adata function/API mismatch | Inspect available functions once; switch adapter rather than trial-looping many calls |
| Conflicting public data | Prefer official filings for exposure; prefer newest reliable quote source for market data; show caveat |

Never hide data gaps. Mark "未披露", "待验证", or "本地缓存口径" in the report when they affect the conclusion, and keep runtime issues such as "接口失败" in `source_data.json` unless they materially reduce conclusion confidence.

## Source Trail Format

Use `public_data.SourceTrail` to accumulate adapter outcomes and write `source_data.json`. When writing a trail by hand, use these fields:

| Field | Meaning |
| --- | --- |
| `tool` | `akshare`, `baostock`, `adata`, `local-cache`, `filing`, `news` |
| `function_or_path` | Function name or local path |
| `queried_at` | Run timestamp |
| `subject` | Industry, board, or stock code |
| `rows` | Row count if tabular |
| `status` | `ok`, `fallback`, `failed`, or `partial` |
| `error` | Error text when failed |
| `confidence` | High / Medium / Low |

For the reader-facing report, do not render raw adapter logs. Use only a compact claim-level source summary:

```markdown
| Claim | Source | Date | Link/Path | Confidence |
| --- | --- | --- | --- | --- |
| ... | ... | YYYY-MM-DD | ... | High/Medium/Low |
```

Use the source trail to decide which statements deserve caveats in the final report.
