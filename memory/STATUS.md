# Current status

**Updated:** 2026-11-12  
**Branch:** `feature/plan-use-case`  
**Base:** `origin/main` after PR #8 merged the evolution loop.

## Portfolio productization (2026-08-25)

- Root [`portfolio.yaml`](../portfolio.yaml) follows `portfolio.dev/v1` (Labbys template)
- `make setup|bootstrap|doctor|demo|dev|check` via [`Makefile`](../Makefile)
- Docs: [`docs/quickstart.md`](../docs/quickstart.md), [`docs/architecture.md`](../docs/architecture.md), [`docs/configuration.md`](../docs/configuration.md)

## Product shape

Dual-agent router (Hermes planner → Laguna executor) with prompt co-evolution:

| Layer | Path | Role |
| --- | --- | --- |
| Runtime agents | `src/` | Planner / executor / orchestrator |
| Evolving router | `router/` | `DualLLMRouter`, `EvolvingRouter`, `CoEvolver` |
| Prompts | `prompts/{hermes,laguna,critic}/` | Base + few-shot; `evolved/` gitignored |
| Evolution | `evals/` | Engine, scoring, mutation, A/B, alerts, benchmarks |
| Tasks | `benchmark/{easy,medium,hard,extreme}/` | Progressive suite (~21 tasks, domain-tagged) |
| Publish | `benchmark/published/` | Timestamped Markdown + `LATEST` / `INDEX` |
| Fitness | `evolution/dashboard/` | HTML + JSON fitness trend |
| Promoted genomes | `evolution/promoted/` | Gated snapshots of the active pair |
| Scripts | `scripts/` | evolve / reset / analyze / benchmark / publish / CI summary |
| Config | `config/evolution.yaml`, `config/ab_tests.yaml` | Evolution + A/B knobs |
| Runtime state | `.autoclaw/` (gitignored) | Genomes, logs, economy |

## Indexes (2026-08-01)

| System | Location | Status | Stats |
| --- | --- | --- | --- |
| **Codegraph** | `.codegraph/` (local, gitignored) | Done — `codegraph init` | **92 files**, **679 nodes**, **1,300 edges** |
| **Codebase-memory MCP** | `.codebase-memory/graph.db.zst` | Done — `index_repository(mode=full, persistence=true)` | **897 nodes**, **3,476 edges** (commit `047bb80`) |

Verified: `codegraph_explore` resolves `BenchmarkRunner` / `publish_results` / `EvolutionEngine` with callers.

Refresh after major edits:

```bash
codegraph sync          # incremental
# or
codegraph index         # full rebuild

# MCP artifact (optional shareable graph):
# Call index_repository on dual-llm-router with persistence=true
```

## CI/CD

| Workflow | File | Trigger | Purpose |
| --- | --- | --- | --- |
| Benchmark | `.github/workflows/benchmark.yml` | Push (path), weekly Sun 02:00 UTC, dispatch | Tests, publish Markdown, full suite + comparative + summary |
| CI Benchmark (PR) | `.github/workflows/ci-benchmark.yml` | PR → main (path) | Easy smoke (simulate) + unit/P0 |
| Nightly Evolution | `.github/workflows/nightly-evolution.yml` | Daily 04:00 UTC, dispatch | Simulated evolve, fitness dashboard, gated promotion decision |

Default mode is **simulate**. Live OpenRouter only if `OPENROUTER_API_KEY` is set (schedule / dispatch `--live`).

Docs: [`benchmark/benchmark-cicd.md`](../benchmark/benchmark-cicd.md), [`benchmark/benchmark_publishing_results.md`](../benchmark/benchmark_publishing_results.md).

## Shipped on this branch (recent)

1. Prompt co-evolution loop → restructured into `evals/` + `router/` + `scripts/`
2. Difficulty-tiered benchmark suite + dashboard / comparative runner
3. Published results: `benchmark_results_<YYYYMMDD_HHMMSSZ>.md` (+ system metrics, domains)
4. Guide tasks: `easy_basic_function`, `easy_file_creation`, `medium_class_with_methods`, `medium_api_endpoint`
5. Feasible CI/CD (PR smoke, weekly suite/comparative, nightly evolution)
6. Issue-to-fix showcase: `examples/issue_to_fix/`, structured `checks`, pytest assertion verifier, `make showcase`
7. P2 evolution productization: gated genome snapshots, durable fitness dashboard, [ADR 0001](../docs/adr/0001-careful-genome-promotion.md)
8. P3 docs and polish: Evolution CI schedule table, secrets-gated weekly summary webhook, P1 functionality tests kept as the live contract

## Verification snapshot

- Unit gates (local): evolution / scoring / mutation / A/B / benchmark / publisher / P0 — passing
- Comparative after `evolve --runs 40 --force` produces parseable `reports/comparative.json`
- CI pytest includes `tests/test_p1_functionality.py`. Provider calls in tests use dummy credentials from `tests/conftest.py`.

## Known gaps

1. Optional `OPENROUTER_API_KEY` is not required for CI. Live weekly runs use the secret when it is set and otherwise stay on `--simulate`.
2. Weekly summary posts to Slack or Discord only when `SLACK_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL`, or `BENCHMARK_SUMMARY_WEBHOOK` is set. Missing secrets leave the step summary in place and do not fail the job. A configured webhook that rejects the post fails the job.
3. Human-intervention rate is on each benchmark result and in the published system metrics. Simulate runs record `human_intervened=false`, so the rate is 0 rather than missing.
