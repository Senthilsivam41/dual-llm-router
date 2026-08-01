# Benchmark CI/CD — feasibility & implementation

Adapted from the research-labs design for this repo’s real CLIs, genomes, and publish flow.

---

## Feasibility verdict

| Research-labs idea | Feasible? | Notes |
| --- | --- | --- |
| PR smoke (`--simulate` easy) | Yes | Implemented in `ci-benchmark.yml` |
| Unit + P0 tests in CI | Yes | `tests/test_*.py` already present |
| Weekly full suite matrix | Yes | Simulate is free / deterministic |
| Comparative variant A/B | Yes* | Needs `evolve.py --force` first — `hermes_v2/v3` do not exist after `reset.py` alone |
| Publish Markdown to `benchmark/published/` | Yes | Already existed; kept on push + schedule |
| Live OpenRouter in CI | Conditional | Only when `OPENROUTER_API_KEY` secret is set; default remains simulate |
| Slack notifications | Deferred | No Slack secret required; use Actions step summaries + artifacts instead |
| Literal `requirements.txt` cache | Yes | File exists |
| Dashboard `--output` path | Yes | Alias added for `--save` |
| Semicolon `--variants a;b` | No | This repo uses space-separated: `--variants h1,l1 h2,l1` |
| `evolve.py --force false` string | No | `--force` is a boolean flag; workflows use proper conditionals |
| Overlapping `suite_matrix` + `full_suite` | Skipped | Redundant CI minutes; only `full_suite` runs all tiers |

---

## Workflows shipped

| Workflow | File | Triggers | Purpose |
| --- | --- | --- | --- |
| Benchmark | [`.github/workflows/benchmark.yml`](../.github/workflows/benchmark.yml) | Push (path filter), weekly Sun 02:00 UTC, `workflow_dispatch` | Tests, publish Markdown, weekly full suite + comparative + summary |
| CI Benchmark (PR) | [`.github/workflows/ci-benchmark.yml`](../.github/workflows/ci-benchmark.yml) | PR → `main` (path filter) | Easy smoke + regression / P0 |
| Nightly Evolution | [`.github/workflows/nightly-evolution.yml`](../.github/workflows/nightly-evolution.yml) | Daily 04:00 UTC, `workflow_dispatch` | Simulated runs + `evolve` + analyze artifacts |

### Job map (`benchmark.yml`)

```text
tests ─────────────────────────────► always (push / schedule / dispatch)
publish ───────────────────────────► major-change detect → simulate/live → commit published/
comparative ──┐
full_suite ───┼──► summary (schedule / dispatch only)
```

---

## Secrets (optional)

Repo → Settings → Secrets and variables → Actions:

| Secret | Required? | Used by |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | No | Live publish on schedule / dispatch `--live` |
| `OPENAI_API_KEY` | No | Unused by current scripts (reserved) |

Without secrets, all workflows stay on `--simulate` and still produce useful regression signal.

---

## CLI contracts (this repo)

```bash
python scripts/reset.py
python scripts/benchmark_runner.py --suite easy --variant hermes_v1,laguna_v1 --simulate
python scripts/benchmark_dashboard.py --report overall --output reports/out.json
python scripts/comparative_benchmark.py --suite easy --simulate \
  --variants hermes_v1,laguna_v1 hermes_v2,laguna_v1 hermes_v3,laguna_v1
python scripts/publish_benchmark_results.py --force --suite easy --simulate
python scripts/evolve.py --runs 100 --force
python scripts/analyze.py
python scripts/ci_benchmark_summary.py --title "Smoke" --report reports/pr_smoke.json
```

Comparative prerequisite:

```bash
python scripts/reset.py
python scripts/evolve.py --runs 40 --force   # creates hermes_v2/v3, laguna_v*
```

---

## Local dry-run (mirrors CI)

```bash
pip install -r requirements.txt
python scripts/reset.py

# PR smoke
python scripts/benchmark_runner.py --suite easy --variant hermes_v1,laguna_v1 --simulate
python scripts/benchmark_dashboard.py --report overall --output reports/pr_smoke.json

# Unit gates
pytest tests/test_scoring.py tests/test_mutation.py tests/test_ab_test.py \
       tests/test_evolution.py tests/test_benchmark.py tests/test_benchmark_publisher.py \
       tests/test_p0_security.py -q

# Weekly comparative slice
python scripts/evolve.py --runs 40 --force
python scripts/comparative_benchmark.py --suite easy --simulate \
  --variants hermes_v1,laguna_v1 hermes_v2,laguna_v1 hermes_v3,laguna_v1
```

---

## Expected artifacts

| Trigger | Artifacts |
| --- | --- |
| PR | `pr-benchmark-smoke` |
| Push (major paths) | `benchmark-publish` + committed `benchmark/published/benchmark_results_*.md` |
| Weekly / dispatch | `full-benchmark-*`, `comparative-benchmark`, `benchmark-summary` |
| Nightly | `evolution-results` (genomes + evolution_log + analysis) |

View under **Actions → run → Artifacts**, and step summaries on the run page.

---

## What we intentionally did not copy

1. **Slack posts** — optional polish; step summaries cover the same need without secrets.
2. **Live API on every PR** — cost/noise; simulate is the PR contract.
3. **Triple-redundant suite jobs** — one `full_suite` matrix covers all tiers.
4. **Sketch runner/dashboard rewrites** — production code already lives under `evals/` + `scripts/`.
