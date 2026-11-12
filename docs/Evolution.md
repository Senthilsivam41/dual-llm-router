# Dual-LLM Router Prompt Evolution

This document describes the co-evolution process for Hermes (planner) and Laguna (executor) prompts.

## Goals

- **Automatic improvement** — mutate and promote prompts from run history
- **Cost reduction** — clearer task specs → fewer executor iterations
- **Quality increase** — higher acceptance-criteria pass rates
- **Transparency** — genome + lineage files show ancestry and mutations
- **Scientific rigor** — A/B testing before promoting challengers

## Layout

```
.autoclaw/
  agents/genomes/{hermes,laguna}/vN.json
  agents/genomes/lineage.json
  evals/evolution_log.json
  evals/run_results.json
  evals/ab_tests.json
  evals/best_configs.json
  evals/alerts.jsonl
evals/
  evolution_engine.py
  scoring.py
  mutation.py
  ab_test.py
  alerts.py
  templates/{hermes,laguna}_v1.json
prompts/{hermes,laguna}/base.py
prompts/{hermes,laguna}/evolved/   # generated, gitignored
config/evolution.yaml
scripts/{evolve,analyze,reset,cron_evolve}.py|.sh
```

## Lifecycle

1. **Run** — `EvolvingRouter.route_task()` executes the pipeline and appends a structured entry to `.autoclaw/evals/run_results.json`.
2. **Score** — `evals/scoring.calculate_fitness()` computes success/cost/quality/time composite scores per (hermes, laguna) pair.
3. **Trigger** — every `evolution.check_interval_runs` (default 50), `EvolutionEngine.should_evolve()` returns true.
4. **Mutate** — operators in `evals/mutation.py` create 2–3 challenger genomes and write evolved prompt modules under `prompts/*/evolved/`.
5. **A/B test** — `ABTestManager` compares control vs challengers; results land in `ab_tests.json`.
6. **Select** — elitist selection keeps top variants; winners update `best_configs.json`.
7. **Lineage** — parent→child edges are appended to `lineage.json`.
8. **Alert** — if composite fitness rises by ≥ `alerting.min_delta`, write `alerts.jsonl` and optionally POST `EVOLUTION_ALERT_WEBHOOK`.
9. **Dashboard** — `scripts/fitness_dashboard.py` writes `evolution/dashboard/` (`fitness.html`, `fitness.json`, `LATEST.md`). An unchanged fingerprint does not add another archive file.
10. **Promote** — `scripts/promote_genomes.py` copies the active pair into `evolution/promoted/` only when the gates in [ADR 0001](adr/0001-careful-genome-promotion.md) pass. `--apply` is required. The nightly schedule does not commit that directory.

## CLI

```bash
# Bootstrap baselines from evals/templates/
python scripts/reset.py

# Simulate runs + evolve when due
python scripts/evolve.py --runs 50
python scripts/evolve.py --force

# Dashboard-style summary (console)
python scripts/analyze.py

# Durable fitness page
python scripts/fitness_dashboard.py
python scripts/analyze.py --output evolution/dashboard

# Gated genome snapshot (decision only, then write)
python scripts/promote_genomes.py
python scripts/promote_genomes.py --apply
```

## CI schedules

The cron strings below are copied from the workflow files. A schedule change updates this section in the same change.

| Workflow | File | Trigger |
| --- | --- | --- |
| Benchmark | `.github/workflows/benchmark.yml` | Push to `main` and `cursor/**` (path filter); weekly Sunday 02:00 UTC (`0 2 * * 0`); `workflow_dispatch` with `suite` and `live` |
| CI Benchmark (PR) | `.github/workflows/ci-benchmark.yml` | `pull_request` to `main` (path filter). No schedule. |
| Nightly Evolution | `.github/workflows/nightly-evolution.yml` | Daily 04:00 UTC (`0 4 * * *`); `workflow_dispatch` with `runs`, `force`, and `promote` |

Default mode is simulate. A scheduled Benchmark run, or a dispatch with `live` set, uses `OPENROUTER_API_KEY` when that secret exists and stays on `--simulate` when it does not. PR smoke always uses `--simulate`.

The weekly summary job writes `reports/summary.md` and the Actions step summary from one Markdown string. If `SLACK_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL`, or `BENCHMARK_SUMMARY_WEBHOOK` is set, that same Markdown is posted. A missing secret skips the post and the job still succeeds.

## Cron (Phase 5)

This host timer is separate from the GitHub Actions schedules above. Hourly check (only evolves when the run interval is met):

```cron
0 * * * * cd /path/to/dual-llm-router && ./scripts/cron_evolve.sh >> .autoclaw/evals/cron.log 2>&1
```

Force an evolution pass during the cron tick:

```bash
EVOLUTION_FORCE=1 ./scripts/cron_evolve.sh
```

## Alerting

Set a webhook (Slack/Discord/custom) via env or config:

```bash
export EVOLUTION_ALERT_WEBHOOK=https://hooks.example.com/evolution
```

```yaml
# config/evolution.yaml
evolution:
  alerting:
    enabled: true
    min_delta: 0.05
    webhook_url: null  # prefer env var in production
```

## Implementation checklist

| Phase | Item | Status |
|---|---|---|
| 1 | `.autoclaw/evals/` structure | Done (`scripts/reset.py`) |
| 1 | `evals/scoring.py` | Done |
| 1 | `evals/mutation.py` | Done |
| 1 | Genome JSON templates | Done (`evals/templates/`) |
| 2 | `evals/evolution_engine.py` | Done |
| 2 | `router/router.py` (`EvolvingRouter`) | Done |
| 2 | `evals/ab_test.py` | Done |
| 3 | `scripts/evolve.py` | Done |
| 3 | `scripts/analyze.py` | Done |
| 3 | Logging throughout | Done (`logging` in engine/alerts/router) |
| 4 | Unit tests | Done (`tests/test_{evolution,mutation,scoring,ab_test}.py`) |
| 4 | Simulated data path | Done (`evolve.py --runs`) |
| 4 | Lineage tracking verified | Done (edges in `lineage.json` + tests) |
| 5 | Cron job | Done (`scripts/cron_evolve.sh`) |
| 5 | Alerting | Done (`evals/alerts.py`) |
| 5 | Documentation | Done (this file) |
