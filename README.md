# Dual-LLM Router

Role-specialized agent pipeline: **Hermes 4** plans, **Laguna S 2.1** executes — with optional **prompt co-evolution** that improves both from run history.

| Role | Model | Responsibility |
|---|---|---|
| Planner | Hermes 4 | User request → structured `TaskSpec` JSON |
| Executor | Laguna S 2.1 | `apply_patch` / `run_shell` against acceptance criteria |
| Evolution | Local loop | Mutate prompts, A/B test, promote winners |

Detailed evolution docs: [`docs/Evolution.md`](docs/Evolution.md)  
Original proposal: [`docs/Project_Proposal.md`](docs/Project_Proposal.md)  
Portfolio manifest: [`portfolio.yaml`](portfolio.yaml) · Quickstart: [`docs/quickstart.md`](docs/quickstart.md)

---

## Architecture

### Request pipeline

```
                         ┌──────────────────────────────────────┐
                         │         EvolvingRouter               │
                         │  (active hermes_* / laguna_* genomes)│
                         └──────────────────┬───────────────────┘
                                            │
                                            v
User / Trigger ──► [Planner: Hermes 4] ──► TaskSpec JSON
                   prompts/hermes/*            │
                   goal, target_files,         │
                   acceptance_criteria,        │
                   step_by_step_plan           v
                                   [Executor: Laguna S 2.1]
                                   prompts/laguna/*
                                   apply_patch / run_shell
                                            │
                                            v
                              Verification + metrics
                              (pass rate, cost, latency)
                                            │
                                            v
                                   Run result logged
                             .autoclaw/evals/run_results.json
```
<img width="1024" height="765" alt="image" src="https://github.com/user-attachments/assets/643e0fe9-f621-4616-8017-2d84db249aba" />


### Co-evolution loop

```
 run_results.json
        │
        v
 ┌──────────────┐     every N runs      ┌──────────────┐
 │   Scoring    │ ───────────────────► │   Mutation   │
 │ success/cost │                       │ hermes+laguna│
 │ quality/time │                       │  operators   │
 └──────┬───────┘                       └──────┬───────┘
        │                                      │
        │                                      v
        │                               challenger genomes
        │                               prompts/*/evolved/
        │                                      │
        v                                      v
 ┌──────────────┐     promote winner    ┌──────────────┐
 │  A/B Test    │ ───────────────────► │   Selection  │
 │  + lineage   │                       │ best_configs │
 └──────────────┘                       └──────┬───────┘
                                               │
                                               v
                                    alerts.jsonl / webhook
                                    (significant fitness gain)
```

<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/a5bbbf59-7466-4a9b-a7a2-40fd9accda02" />


**Data plane (gitignored runtime state under `.autoclaw/`):**

| Path | Purpose |
|---|---|
| `agents/genomes/{hermes,laguna}/vN.json` | Prompt genome + capability vector |
| `agents/genomes/lineage.json` | Parent → child ancestry |
| `evals/run_results.json` | Append-only per-run log |
| `evals/evolution_log.json` | Evolution cycle history |
| `evals/ab_tests.json` | A/B test records |
| `evals/best_configs.json` | Current winning variants |
| `evals/alerts.jsonl` | Significant-improvement alerts |
| `economy/{budgets,ledger}.json` | Cost budget scaffolding |

---

## Repository layout

```
dual-llm-router/
├── router/
│   ├── router.py              # DualLLMRouter + EvolvingRouter
│   └── evolver.py             # CoEvolver bridge
├── src/
│   ├── agents/                # PlannerAgent / ExecutorAgent
│   ├── tools/                 # apply_patch, run_shell (+ schemas)
│   ├── schemas/task_spec.py
│   ├── orchestrator.py
│   └── utils/metrics.py
├── prompts/
│   ├── hermes/base.py         # Current Hermes system prompt
│   ├── laguna/base.py         # Current Laguna system prompt
│   ├── critic/system.py
│   └── */evolved/             # Generated variants (gitignored)
├── evals/
│   ├── evolution_engine.py    # Mutate → A/B → select → lineage
│   ├── scoring.py
│   ├── mutation.py
│   ├── ab_test.py
│   ├── alerts.py
│   └── templates/             # Baseline genome JSON templates
├── config/
│   ├── evolution.yaml
│   └── ab_tests.yaml
├── scripts/
│   ├── reset.py               # Bootstrap .autoclaw baselines
│   ├── evolve.py              # Trigger / simulate evolution
│   ├── analyze.py             # Fitness / lineage summary
│   └── cron_evolve.sh         # Periodic evolution check
├── tests/
└── docs/
    ├── Evolution.md
    └── Project_Proposal.md
```

---

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv sync --locked --dev

# Optional live models
cp .env.example .env   # set OPENROUTER_API_KEY

# Bootstrap evolution state
uv run python scripts/reset.py

# One-shot pipeline (no evolution wrapper)
uv run python example_run.py -p "Create math_utils.py with add(a, b) and a unit test"

# Issue-to-fix showcase. Without FIREWORKS_API_KEY this replays the committed recording.
make showcase
make showcase-compare

# Evolution CLI (simulate runs, evolve when due)
uv run python scripts/evolve.py --runs 50
uv run python scripts/evolve.py --force
uv run python scripts/analyze.py
```

### Use the evolving router in code

```python
from router import EvolvingRouter

router = EvolvingRouter(workspace_root="./workspace")
result = router.route_task(
    "Create math_utils.py with add(a, b) and a unit test",
    execute_tools=True,
)
```

### Cron (optional)

```cron
0 * * * * cd /path/to/dual-llm-router && ./scripts/cron_evolve.sh >> .autoclaw/evals/cron.log 2>&1
```

Alert webhook (optional):

```bash
export EVOLUTION_ALERT_WEBHOOK=https://hooks.example.com/evolution
```

---

## How a run is scored

Composite fitness for a `(hermes_variant, laguna_variant)` pair (see `config/evolution.yaml`):

| Signal | Default weight |
|---|---|
| Success rate | 0.35 |
| Cost efficiency | 0.30 |
| Quality score | 0.25 |
| Time efficiency | 0.10 |

Evolution triggers every `check_interval_runs` (default **50**). Challengers are created with hermes/laguna mutation operators, A/B tested, and winners written to `best_configs.json`.

---

## Showcase

`make showcase` runs one bundled bug. `examples/issue_to_fix/billing.py` applies a $10 coupon after tax and rounds each line before summing. `issue.md` states the charged and expected amounts.

The planner turns that report into a `TaskSpec` with structured `checks`. The executor writes the fix and the pytest tests. The router runs those tests in a restricted subprocess, or in Docker when that image can import pytest, and counts a check only when its expected amount appears as a number inside an `assert` of a passing test. Report amounts are copied from `issue.md`. The planner also computes them. A disagreement is scored as planner accuracy and does not replace the report value. Edge cases are labeled required or optional, and at least one edge case must be required. Required checks decide the verdict. The executor gets up to three attempts with the pytest output and the unmatched checks. The plan stays fixed.

The pinned models are Fireworks `deepseek-v4p1-flash` (planner) and `glm-5p3-flash` (executor). Override them with `SHOWCASE_PLANNER_MODEL` and `SHOWCASE_EXECUTOR_MODEL`, or with `PLANNER_MODEL` and `EXECUTOR_MODEL` when those are not the repo's OpenRouter defaults. A preflight call checks both models. There is no fallback.

Without `FIREWORKS_API_KEY`, the command explains what is missing and opens the recorded sample in `examples/issue_to_fix/recorded/`. That sample is one of five live runs: verified in 5 of 5, median 1 attempt, median cost $0.002041. `make showcase-compare` runs the same fixture with the executor model in both roles.

The benchmark task `medium_billing_coupon` uses the same fixture, so evolution can score planner accuracy. A non-blocking GitHub Action runs the showcase when a pull request touches the agents, prompts, or fixture, and on the weekly schedule. It writes a job summary from `run.json`, uploads `report.html`, and refreshes `benchmark/published/showcase_success_rate.json` without replacing the committed sample.

## Benchmarks

Difficulty-tiered tasks live under `benchmark/{easy,medium,hard,extreme}/`.

```bash
./benchmark/minimal_setup.sh
uv run python scripts/benchmark_runner.py --suite easy --simulate --list
uv run python scripts/benchmark_runner.py --suite all --variant hermes_v1,laguna_v1 --simulate
uv run python scripts/benchmark_dashboard.py --report overall
uv run python scripts/comparative_benchmark.py --variants hermes_v1,laguna_v1 --suite easy --simulate

# Publish versioned Markdown under benchmark/published/
uv run python scripts/publish_benchmark_results.py --if-major --suite easy --simulate
```

Published reports: [`benchmark/published/`](benchmark/published/) (`benchmark_results_<timestamp>.md`)
Metrics definitions: [`benchmark/Key_Metrics_Summary.md`](benchmark/Key_Metrics_Summary.md)
Suite details: [`benchmark/README.md`](benchmark/README.md)
CI/CD workflows: [`benchmark/benchmark-cicd.md`](benchmark/benchmark-cicd.md) (PR smoke, weekly suite, nightly evolution)
Agent memory / index status: [`memory/STATUS.md`](memory/STATUS.md)

## Testing

```bash
uv run pytest tests/test_scoring.py tests/test_mutation.py tests/test_ab_test.py tests/test_evolution.py tests/test_benchmark.py -q
uv run pytest tests/test_end_to_end.py tests/test_p0_security.py -q
```

---

## Design notes

- **Split roles on purpose** — planning stays cheap/structured; execution stays tool-heavy.
- **TaskSpec is the contract** — Hermes never calls tools; Laguna never rewrites the user goal freely.
- **Evolution is offline-friendly** — genomes and logs live under `.autoclaw/`; base prompts stay in git under `prompts/`.
- **Promote with evidence** — A/B + lineage so improvements are inspectable, not silent prompt drift.
