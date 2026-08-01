# Future changes

**Updated:** 2026-08-01  
Prioritized backlog after evolution + benchmark + CI/CD slice.

## P0 — Merge & CI hygiene

1. Open / refresh PR `cursor/prompt-evolution-loop` → `main` when ready
2. Confirm Actions green: `ci-benchmark` on PR, `Benchmark` publish on push
3. Optionally set repo secret `OPENROUTER_API_KEY` for scheduled live runs

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
