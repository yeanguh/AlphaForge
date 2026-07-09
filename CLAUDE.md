# Claude Code Notes

Use this repository as a local-first research operating system.

Run provider smoke checks before trusting external data:

```bash
python scripts/run_provider_smoke.py --live
```

Run harness before committing state changes:

```bash
python scripts/run_harness.py
```
