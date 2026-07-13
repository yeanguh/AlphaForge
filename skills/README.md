# AlphaForge Skills

This directory contains the repository-owned Codex-readable skill entries for
AlphaForge.

A skill is a named capability with a `SKILL.md` manifest plus optional
supporting files such as references, scripts, templates, evals, or tools.
Codex can read these files as task guidance, while AlphaForge runtime code
must still go through the repository's provider and state boundaries.

```markdown
---
name: my-skill
description: One sentence telling Codex when to use this skill.
---

Body content: workflow, constraints, examples, helper commands, and references.
```

## Boundary Rules

- `skills/*/SKILL.md` are repository-owned Codex-readable entry files.
- `.codex/skills/*` may symlink repository-owned and external skill directories
  for workspace-local Codex discovery. This directory is ignored by git and is
  not a runtime dependency boundary.
- The only retained runtime analysis skill is `industry-chain-analysis`.
- Runtime conversion code for retained analysis skills lives under
  `providers/retained_skills/*`.
- Data-provider skills such as `a-stock-data`, `global-stock-data`, and
  `wen-cai` are separate from retained analysis skills and are accessed through
  `providers/open_source/*`.
- External skills under `external/ch-skills/skills/*` are reference/playbook
  material. They are not retained AlphaForge skills and must not be wired directly
  into `loop_os/` runtime loops.
- `loop_os/` must not directly import from `external/*` or depend on an
  external skill's internal file layout.
- Do not add implicit local dependencies outside this repository. External
  caches, tokens, and data roots must be configured through environment
  variables.
- Skills cannot directly mutate `state/*`; state changes require evidence ids
  and must pass `loop_os/state_machine/*` and `loop_os/harness/*` checks.
- Canonical research reports live at `reports/themes/<theme>/report.md` and
  must be updated incrementally, not wholesale-overwritten.

## Repository Skills

### Data Provider Skills

| Skill | Runtime adapter | Purpose |
| --- | --- | --- |
| [`a-stock-data`](a-stock-data/) | `providers/open_source/a_stock_data.py` | A-share quotes, K-line history, valuation context, announcements, financials, fund flow, research reports |
| [`global-stock-data`](global-stock-data/) | `providers/open_source/global_stock_data.py` | US/HK/global market quotes and cross-market validation |
| [`wen-cai-1.0.0`](wen-cai-1.0.0/) | `providers/open_source/wen_cai.py` | iWenCai query/search enrichment for A-share business exposure, reports, announcements, news, and screens |

## External Reference Skills

`external/ch-skills` is kept as a reference-only upstream skill collection. Its
README has been folded into this Codex-facing index without moving those skills
into the repository-owned `skills/` namespace.

When Codex needs one of these references, read the target `SKILL.md` directly
from `external/ch-skills/skills/<name>/SKILL.md`, then follow any referenced
files relative to that external skill directory. Do not treat these as Research
OS runtime dependencies unless a provider adapter or documented reference
boundary is added first.

| External skill | Reference path | Purpose |
| --- | --- | --- |
| `meta-prompt` | `external/ch-skills/skills/meta-prompt/SKILL.md` | Turn a vague task into a high-quality prompt for another AI session; supports Claude-style XML or GPT/OpenAI-style Markdown prompts |
| `marxist-method-for-action` | `external/ch-skills/skills/marxist-method-for-action/SKILL.md` | Rigorous investigation and contradiction-analysis method for substantive decisions |
| `company-analyzer` | `external/ch-skills/skills/company-analyzer/SKILL.md` | Company deep-dive through story, business logic, financial quality, moat, and judgment |
| `intrinsic-value-analysis` | `external/ch-skills/skills/intrinsic-value-analysis/SKILL.md` | Lao Tang-style intrinsic value method: ability circle, three premise checks, bond-like valuation, buy/sell discipline |
| `industry-chain-research` | `external/ch-skills/skills/industry-chain-research/SKILL.md` | General industry-chain research workflow from macro trend to bottleneck links and candidate stocks |
| `industry-chain-mapper` | `external/ch-skills/skills/industry-chain-mapper/SKILL.md` | Artifact-oriented industry-chain maps with upstream/midstream/downstream links, key companies, and elasticity ranking |
| `stock-analyzer` | `external/ch-skills/skills/stock-analyzer/SKILL.md` | A-share stock research note across business model, financials, valuation, catalysts, risks, and falsification conditions |
| `technical-analyzer` | `external/ch-skills/skills/technical-analyzer/SKILL.md` | Secondary timing analysis for trend, support/resistance, moving averages, and volume |
| `valuation-calculator` | `external/ch-skills/skills/valuation-calculator/SKILL.md` | Relative valuation with PE/PB/PS percentiles, peer comparison, and target-price derivation |
| `catalyst-tracker` | `external/ch-skills/skills/catalyst-tracker/SKILL.md` | Forward-looking catalyst calendar for earnings, conferences, policy events, and tracked stocks |
| `news-scanner` | `external/ch-skills/skills/news-scanner/SKILL.md` | Investment news scanning across Xueqiu, Eastmoney, 10jqka, and web sources, filtered for signal |
| `tushare-data` | `external/ch-skills/skills/tushare-data/SKILL.md` | Tushare Pro structured A-share data helper; requires `TUSHARE_TOKEN` |
| `stock-market-data` | `external/ch-skills/skills/stock-market-data/SKILL.md` | AKShare-based free market snapshots, trading-day checks, index/sector/limit-up/northbound data |
| `financial-data-fetcher` | `external/ch-skills/skills/financial-data-fetcher/SKILL.md` | Financial statements and ETF data helper using Tushare primary and AKShare fallback |
| `wechat-feeds` | `external/ch-skills/skills/wechat-feeds/SKILL.md` | WeChat Official Account article archive as Markdown plus SQLite, with an updater tool |

## Repository Layout

```text
skills/
├── README.md
├── industry-chain-analysis/       # retained AlphaForge analysis skill
├── a-stock-data/                  # data-provider skill
├── global-stock-data/             # data-provider skill
└── wen-cai-1.0.0/                 # data-provider skill

external/ch-skills/
├── README.md                      # upstream reference README
└── skills/                        # reference-only external skills
```

## Codex Usage

Codex should read the relevant repository-owned or external `SKILL.md` before applying a
skill. If a skill references `references/`, `scripts/`, `templates/`, or
`tool/`, resolve those paths relative to that skill directory.

For AlphaForge runtime work, prefer existing adapters and domain services over
directly executing external skill scripts. If an external skill should become a
runtime capability, add an explicit adapter under `providers/open_source/*` or,
only for the retained analysis skill, `providers/retained_skills/*`, then cover
it with harness checks.

## Configuration

- `IWENCAI_API_KEY` and optional `IWENCAI_BASE_URL` configure the WenCai
  provider.
- `TUSHARE_TOKEN` configures Tushare-based external reference skills if used
  manually. Account permissions vary; fallback rules and verification commands
  are tracked in `docs/reference/data-access.md`.
- A-share cache paths must use explicit environment variables such as
  `RESEARCH_OS_A_DATA_DIR`; do not assume caches outside this repository.
- WeChat feed tooling may require a logged-in Chrome/CDP session and tool
  dependencies documented in
  `external/ch-skills/skills/wechat-feeds/SKILL.md`.

## Provenance

`external/ch-skills` is the upstream reference collection from
`Haochenhust/ch-skills`. Its README content has been summarized here and
adjusted from a standalone Claude Code installation guide into AlphaForge
Codex guidance.
