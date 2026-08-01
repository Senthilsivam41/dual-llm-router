# Dual-LLM Router

Role-specialized agent pipeline: **Hermes 4** plans, **Laguna S 2.1** executes — with optional **prompt co-evolution** that improves both from run history.

| Role | Model | Responsibility |
|---|---|---|
| Planner | Hermes 4 | User request → structured `TaskSpec` JSON |
| Executor | Laguna S 2.1 | `apply_patch` / `run_shell` against acceptance criteria |
| Evolution | Local loop | Mutate prompts, A/B test, promote winners |

Detailed evolution docs: [`docs/Evolution.md`](docs/Evolution.md)  
Original proposal: [`docs/Project_Proposal.md`](docs/Project_Proposal.md)

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

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional live models
cp .env.example .env   # set OPENROUTER_API_KEY

# Bootstrap evolution state
python scripts/reset.py

# One-shot pipeline (no evolution wrapper)
python example_run.py -p "Create math_utils.py with add(a, b) and a unit test"

# Evolution CLI (simulate runs, evolve when due)
python scripts/evolve.py --runs 50
python scripts/evolve.py --force
python scripts/analyze.py
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

## Benchmarks

Difficulty-tiered tasks live under `benchmark/{easy,medium,hard,extreme}/`.

```bash
./benchmark/minimal_setup.sh
python scripts/benchmark_runner.py --suite easy --simulate --list
python scripts/benchmark_runner.py --suite all --variant hermes_v1,laguna_v1 --simulate
python scripts/benchmark_dashboard.py --report overall
python scripts/comparative_benchmark.py --variants hermes_v1,laguna_v1 --suite easy --simulate
```

Metrics definitions: [`benchmark/Key_Metrics_Summary.md`](benchmark/Key_Metrics_Summary.md)  
Suite details: [`benchmark/README.md`](benchmark/README.md)

## Testing

```bash
pytest tests/test_scoring.py tests/test_mutation.py tests/test_ab_test.py tests/test_evolution.py tests/test_benchmark.py -q
pytest tests/test_end_to_end.py tests/test_p0_security.py -q
```

---

## Design notes

- **Split roles on purpose** — planning stays cheap/structured; execution stays tool-heavy.
- **TaskSpec is the contract** — Hermes never calls tools; Laguna never rewrites the user goal freely.
- **Evolution is offline-friendly** — genomes and logs live under `.autoclaw/`; base prompts stay in git under `prompts/`.
- **Promote with evidence** — A/B + lineage so improvements are inspectable, not silent prompt drift.
