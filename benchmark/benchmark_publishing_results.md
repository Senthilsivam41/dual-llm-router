# Metrics & Benchmarking Guide

How this repo measures Hermes→Laguna co-evolution quality, cost, and reliability — and how results are published.

Related docs: [`task-level-metrics.md`](task-level-metrics.md), [`system-level-metrics.md`](system-level-metrics.md), [`Key_Metrics_Summary.md`](Key_Metrics_Summary.md), [`published/README.md`](published/README.md).

---

## 1. Metrics to measure

### A. Task-level (per run)

| Metric | Why it matters | Where it lives |
| --- | --- | --- |
| Success rate | Did the task complete? | `BenchmarkResult.status == "success"` |
| Cost efficiency | Spending vs budget | `actual_cost / expected_cost` (dashboard overall) |
| Quality score | Output goodness | Heuristic checks + acceptance criteria |
| Time-to-complete | Speed | `time_seconds` |
| Executor iterations | Retry pressure | `iterations` / `executor_calls` |
| Spec rejection rate | Bad Hermes specs | `planning_failed` aggregate |
| Handoff failure rate | Hermes→Laguna breaks | `handoff_failed` aggregate |
| Code quality | Generated code health | `code_quality` dict on result |

### B. System-level (aggregate)

| Metric | Definition | Target |
| --- | --- | --- |
| Throughput | Tasks/hour | Higher |
| Cost per task | $/task | Decreasing |
| Overall success rate | % successful | >90% |
| Spec acceptance rate | 1 − rejection | >80% |
| Avg iterations | Mean executor loops | <5 |
| Evolution improvement | Fitness gain / generation | Positive trend |

Dashboard overall keys: `success_rate`, `cost_efficiency`, `spec_rejection_rate`, `spec_acceptance_rate`, `handoff_failure_rate`, `throughput_tasks_per_hour`.

---

## 2. Progressive benchmark suite

Tasks live under `benchmark/{easy,medium,hard,extreme}/` as modules exporting `TASK`. Loader: `benchmark/tasks_loader.py`.

Each task includes:

- `id`, `category`, `domain`
- `spec`, `acceptance_criteria`
- `complexity_score`, `expected_cost`, `expected_time`, `difficulty`, `tags`
- optional `seed_code` / `expected_code`

Domains in the suite include: `basic`, `oop`, `debugging`, `refactor`, `backend`, `testing`, `architecture`, `performance`, `security`, `systems`, `feature`.

Guide-aligned additions:

| ID | Category | Domain |
| --- | --- | --- |
| `easy_basic_function` | easy | basic |
| `easy_file_creation` | easy | basic |
| `medium_class_with_methods` | medium | oop |
| `medium_api_endpoint` | medium | backend |

---

## 3. Execution & reporting stack

| Piece | Path |
| --- | --- |
| Runner | `evals/benchmark_runner.py` |
| Comparative A/B | `evals/comparative_benchmark.py` |
| Dashboard | `evals/benchmark_dashboard.py` |
| Publisher | `evals/benchmark_publisher.py` |
| CLI | `scripts/benchmark_*.py`, `scripts/publish_benchmark_results.py` |

Flow:

1. Load tasks → run via `EvolvingRouter` (or `--simulate`)
2. Write `.autoclaw/evals/benchmark/results.json`
3. Aggregate report → `report.json` + console dashboard
4. On major-path changes, publish Markdown under `benchmark/published/`

Published naming:

```text
benchmark/published/benchmark_results_<YYYYMMDD_HHMMSSZ>.md
benchmark/published/LATEST.md
benchmark/published/INDEX.md
```

Published Markdown includes overall metrics, **system metrics** (spec rejection / handoff), by category / variant / domain, and per-task rows.

---

## 4. Scoring integration

Benchmark runs feed `EvolutionEngine.record_run_result()` so fitness / A/B selection sees:

- status, cost, time, iterations, executor_calls
- quality_score + acceptance_criteria_pass
- task domain / complexity / expected_cost

Composite fitness weights remain in `evals/scoring.py` / `config/evolution.yaml`.

---

## 5. Quick start

```bash
# List / run simulated suite
python scripts/benchmark_runner.py --suite easy --simulate --list
python scripts/benchmark_runner.py --suite easy --simulate

# Dashboard
python scripts/benchmark_dashboard.py --report overall

# Publish (force offline sample)
python scripts/publish_benchmark_results.py --force --suite easy --simulate

# Publish only when major code paths changed
python scripts/publish_benchmark_results.py --if-major --suite all --simulate

# Live (needs OPENROUTER_API_KEY)
python scripts/benchmark_runner.py --suite medium --variant hermes_v1,laguna_v1
```

Shell helpers: `benchmark/minimal_setup.sh`, `benchmark/full_benchmark.sh`.

CI: `.github/workflows/benchmark.yml` runs simulate + publish on major-path PRs/pushes.

---

## 6. Targets cheat sheet

| Metric | Target |
| --- | --- |
| Success rate | >0.90 |
| Cost efficiency (actual/expected) | <1.0 |
| Quality score | >0.80 |
| Avg iterations | <5 |
| Avg time | <60s |
| Spec rejection rate | <0.20 |
| Spec acceptance rate | >0.80 |
| Handoff failure rate | <0.15 |
| Human intervention rate | <0.05 (tracked outside simulate) |

---

## 7. Adding a task

1. Create `benchmark/<tier>/<name>.py` with a `TASK` dict (include `domain`).
2. Run `python scripts/benchmark_runner.py --suite <tier> --simulate --list` to confirm load.
3. Prefer acceptance criteria that are checkable offline when possible.
4. Re-publish after meaningful runner/prompt changes:

```bash
python scripts/publish_benchmark_results.py --force --suite all --simulate
```
