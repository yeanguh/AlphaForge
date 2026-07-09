# hermes-agent Reference Notes

`hermes-agent` is reference-only.

Upstream: https://github.com/NousResearch/hermes-agent

It is intentionally not checked into `external/` as a submodule. Keep only
the design notes that are useful for Research OS.

Allowed use:

- Read memory and self-improvement design ideas.
- Compare against Research OS memory/state boundaries.

Forbidden use:

- Do not import it in runtime loops.
- Do not let it write `state/*`.
