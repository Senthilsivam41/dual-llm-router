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

Results land in `.autoclaw/evals/benchmark/results.json`.
