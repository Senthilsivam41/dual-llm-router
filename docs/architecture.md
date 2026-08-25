# Architecture

Dual-LLM Router separates **planning** from **execution**, then optionally co-evolves both prompts from scored run history.

## Runtime pipeline

```text
User / Trigger
      │
      v
[Planner: Hermes 4]  →  TaskSpec JSON
 prompts/hermes/*         (goal, files, acceptance criteria, plan)
      │
      v
[Executor: Laguna S 2.1] → apply_patch / run_shell
 prompts/laguna/*
      │
      v
Verification + metrics (pass rate, cost, latency)
      │
      v
.run result → .autoclaw/evals/run_results.json
```

Entry points:

| Layer | Path | Role |
| --- | --- | --- |
| Core agents / orchestrator | `src/` | Planner, executor, `DualLLMRouterOrchestrator` |
| Evolving facade | `router/` | `DualLLMRouter`, `EvolvingRouter`, `CoEvolver` |
| Prompts | `prompts/{hermes,laguna,critic}/` | Base + few-shot; evolved variants gitignored |
| Evolution | `evals/` | Scoring, mutation, A/B, alerts, benchmarks, publisher |
| Tasks | `benchmark/{easy,medium,hard,extreme}/` | Progressive, domain-tagged suite |
| CLI | `scripts/` | reset / evolve / analyze / benchmark / publish |
| Runtime state | `.autoclaw/` (gitignored) | Genomes, logs, economy |

## Co-evolution loop

Every N runs (see `config/evolution.yaml`):

1. **Score** active Hermes/Laguna variants from `run_results.json`
2. **Mutate** challenger genomes
3. **A/B test** when sample sizes allow
4. **Promote** winners into active genomes under `.autoclaw/agents/genomes/`

Nightly CI evolves in simulation and uploads artifacts; genomes are **not** auto-committed to `main` (see [`../memory/FUTURE.md`](../memory/FUTURE.md)).

## Evaluation surface

- Task runner: `evals/benchmark_runner.py`
- Comparative A/B: `evals/comparative_benchmark.py`
- Dashboard / system metrics: `evals/benchmark_dashboard.py`
- Published Markdown: `benchmark/published/benchmark_results_<timestamp>.md`

## Ecosystem role

Per the Labbys product portfolio, Dual-LLM Router is the **plan-and-execute** layer: a reusable engine behind applications or agent-synthetix, optionally fed by a model gateway (e.g. Camper Vane) and observed by Agent Lens.

See also: [`Project_Proposal.md`](Project_Proposal.md), [`Evolution.md`](Evolution.md), [`../portfolio.yaml`](../portfolio.yaml).
