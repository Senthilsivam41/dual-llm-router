# Future changes

**Updated:** 2026-10-03  
Prioritized backlog after evolution + benchmark + CI/CD slice.

## P0 — Merge & CI hygiene

Done on `fix/p0-ci-green`:

1. `cursor/prompt-evolution-loop` merged to `main` (PR #8). Follow-up branch fixes the red test job.
2. The full pytest suite no longer requires `OPENROUTER_API_KEY`. CI Benchmark (PR) and Benchmark (push) both run that suite. Push path filters include `tests/**`.
3. `OPENROUTER_API_KEY` stays optional. Scheduled live runs use it when the secret exists and fall back to `--simulate` when it does not.

## P1 — Live evaluation quality

- Wire stricter acceptance checks against generated workspaces (beyond simulate heuristics)
- Track human-intervention rate when tools / HITL are involved
- Expand comparative matrix to evolved Laguna mutants (not only Hermes × laguna_v1)
- Keep published Markdown diffs meaningful (avoid noise-only republishes)

## P2 — Evolution productization

- Persist / promote genomes carefully (today nightly uploads artifacts; no auto-commit of genomes)
- Surface fitness trends in a durable dashboard (beyond `scripts/analyze.py` console)
- ADR via codebase-memory `manage_adr` once architecture stabilizes

## P3 — Docs / polish

- Keep `docs/Evolution.md` aligned with CI schedules
- Optional Slack / Discord webhook for weekly summary (secrets-gated)
- Retire or implement `tests/test_p1_functionality.py` expectations

## Process (always)

After each major implementation slice:

1. Update [STATUS.md](./STATUS.md) and this file
2. Refresh indexes:
   ```bash
   codegraph sync    # or: codegraph index
   ```
   and re-run codebase-memory `index_repository` when sharing the graph artifact
3. Prefer `codegraph_explore` (projectPath = repo root) — avoid full-repo Grep/Glob when `.codegraph/` exists
