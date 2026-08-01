# Current status

**Updated:** 2026-08-01  
**Branch:** `cursor/prompt-evolution-loop`  
**HEAD (local at update):** `047bb80` — Add feasible CI/CD workflows for PR smoke, weekly benchmarks, and nightly evolution.

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
| Nightly Evolution | `.github/workflows/nightly-evolution.yml` | Daily 04:00 UTC, dispatch | Simulated evolve + analyze artifacts |

Default mode is **simulate**. Live OpenRouter only if `OPENROUTER_API_KEY` is set (schedule / dispatch `--live`).

Docs: [`benchmark/benchmark-cicd.md`](../benchmark/benchmark-cicd.md), [`benchmark/benchmark_publishing_results.md`](../benchmark/benchmark_publishing_results.md).

## Shipped on this branch (recent)

1. Prompt co-evolution loop → restructured into `evals/` + `router/` + `scripts/`
2. Difficulty-tiered benchmark suite + dashboard / comparative runner
3. Published results: `benchmark_results_<YYYYMMDD_HHMMSSZ>.md` (+ system metrics, domains)
4. Guide tasks: `easy_basic_function`, `easy_file_creation`, `medium_class_with_methods`, `medium_api_endpoint`
5. Feasible CI/CD (PR smoke, weekly suite/comparative, nightly evolution)

## Verification snapshot

- Unit gates (local): evolution / scoring / mutation / A/B / benchmark / publisher / P0 — passing
- Comparative after `evolve --runs 40 --force` produces parseable `reports/comparative.json`
- Pre-existing: `tests/test_p1_functionality.py` still fails (P1 features not implemented)

## Known gaps

1. Optional `OPENROUTER_API_KEY` not required for CI; live weekly runs need the secret
2. Slack notifications deferred (step summaries used instead)
3. P1 functionality tests unfinished
4. Human-intervention rate not yet instrumented in simulate path
5. Branch may be behind remote bot publish commits — ff-pull before push
