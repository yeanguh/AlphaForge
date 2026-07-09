# Agent Rules

- Do not reuse the old repository architecture.
- Only retain `industry-chain-analysis` as a methodology/adaptor skill.
- Do not reintroduce `china-stock-analysis` or `china-stock-price-analysis` as retained skills.
- The retained skill entry files live under `skills/*/SKILL.md`.
- Runtime conversion code lives under `providers/retained_skills/*`.
- Do not directly import from `external/*` inside `loop_os/`.
- Open-source submodules must be accessed only through `providers/open_source/*` or documented in `providers/reference/*`.
- Reference-only submodules must not enter runtime loops.
- Every claim that changes state must be backed by an evidence id.
- State changes must pass `loop_os/state_machine/*` rules and `loop_os/harness/*` checks.
