# Benchmark Suite

Difficulty-tiered tasks for evaluating Hermes/Laguna variant combinations.

```
benchmark/
├── easy/       # single function, class, refactor, bugfix
├── medium/     # multi-file, moderate logic, coverage, edge cases
├── hard/       # architecture, performance, bug hunt, feature
├── extreme/    # system design, security, latency, multi-service
├── tasks_loader.py
├── minimal_setup.sh
├── full_benchmark.sh
└── *.md        # metric definitions
```

## Quick start

```bash
# Offline / CI simulation
./benchmark/minimal_setup.sh

# Full simulated suite + comparison
./benchmark/full_benchmark.sh

# Specific suite with live OpenRouter (needs OPENROUTER_API_KEY)
python scripts/benchmark_runner.py --suite medium --variant hermes_v1,laguna_v1
python scripts/benchmark_dashboard.py --report overall
```

Runtime JSON lands in `.autoclaw/evals/benchmark/results.json`.

## Published reports (standard)

Versioned Markdown reports are written to [`published/`](published/):

```text
benchmark/published/benchmark_results_<YYYYMMDD_HHMMSSZ>.md
benchmark/published/LATEST.md
benchmark/published/INDEX.md
```

```bash
# Publish when the current commit touches major code paths
python scripts/publish_benchmark_results.py --if-major --suite easy --simulate

# Always run + publish
python scripts/publish_benchmark_results.py --force --suite all --simulate
```

CI (`.github/workflows/benchmark.yml`) runs this on major-path pushes/PRs and commits the report under `benchmark/published/`.
