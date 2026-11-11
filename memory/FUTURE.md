# Future changes

**Updated:** 2026-11-11  
Prioritized backlog after evolution + benchmark + CI/CD slice.

## P0 — Merge & CI hygiene

Done on `fix/p0-ci-green`:

1. `cursor/prompt-evolution-loop` merged to `main` (PR #8). Follow-up branch fixes the red test job.
2. The full pytest suite no longer requires `OPENROUTER_API_KEY`. CI Benchmark (PR) and Benchmark (push) both run that suite. Push path filters include `tests/**`.
3. `OPENROUTER_API_KEY` stays optional. Scheduled live runs use it when the secret exists and fall back to `--simulate` when it does not.

## P1 — Live evaluation quality

Done:

- Issue-to-fix showcase is in tree (`make showcase`, `examples/issue_to_fix/`). The committed sample is a representative live run: verified in 5 of 5, median 1 attempt, median cost $0.002041.
- Generated workspaces are checked with pytest assertion matching, including benchmark tasks beyond the billing fixture. A numeric expectation fails when no passing test asserts it. Simulate mode still does not call the provider.
- Human-intervention rate is recorded on every run. A run with no human step contributes zero, including simulate.
- Comparative runs name the genomes in the matrix and add evolved Laguna mutants beside Hermes × `laguna_v1`.
- Publishing skips a new Markdown file when the metrics and per-task outcomes are unchanged. `LATEST` and `INDEX` stay on the last material report.

## P2 — Evolution productization

Done:

- Active genomes stay in gitignored `.autoclaw/`. `scripts/promote_genomes.py` copies a pair into `evolution/promoted/` only after sample, fitness, regression, A/B, and secret gates. Nightly CI records the decision and commits a snapshot only on manual `promote=true`.
- `evolution/dashboard/` (`fitness.html`, `fitness.json`, `LATEST.md`) is the durable fitness trend. `scripts/analyze.py` still prints the console summary. Unchanged fingerprints do not add another archive file.
- Architecture decision: [docs/adr/0001-careful-genome-promotion.md](../docs/adr/0001-careful-genome-promotion.md). The codebase-memory `manage_adr` store was unreachable, so this file is the record.

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
