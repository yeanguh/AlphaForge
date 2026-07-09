# Agent Rules

- Do not reuse the old repository architecture.
- The only retained *analysis* skill is `industry-chain-analysis` (data-provider skills like `a-stock-data` / `global-stock-data` / `wen-cai` are separate); do not reintroduce `china-stock-analysis` or `china-stock-price-analysis`.
- Do not add implicit local dependencies outside this repository; external caches must be explicitly configured through environment variables.
- The retained skill entry files live under `skills/*/SKILL.md`.
- Runtime conversion code lives under `providers/retained_skills/*`.
- Do not directly import from `external/*` inside `loop_os/`.
- Open-source submodules must be accessed only through `providers/open_source/*` or documented in `providers/reference/*`.
- Reference-only submodules must not enter runtime loops.
- Canonical research reports live at `reports/themes/<theme>/report.md` (方案 A); never wholesale-overwrite an existing canonical report — merge incrementally. `reports/industry/` is legacy/manual only.
- Every claim that changes state must be backed by an evidence id.
- State changes must pass `loop_os/state_machine/*` rules and `loop_os/harness/*` checks.
