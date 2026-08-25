# Configuration

## Environment

Copy `.env.example` → `.env` for live runs. Secrets stay local (`.env` is gitignored).

| Variable | Required | Default / notes |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | For live LLM calls | Unset → simulate / offline paths |
| `PLANNER_MODEL` | No | `openrouter/nousresearch/hermes-4-70b` |
| `EXECUTOR_MODEL` | No | `openrouter/poolside/laguna-s-2.1` |
| `MAX_TOKENS` | No | `4096` |
| `TEMPERATURE` | No | `0.2` |
| `PROVIDER_TIMEOUT_SECONDS` | No | `120` |
| `PROVIDER_MAX_RETRIES` | No | `2` |

`make doctor` reports whether the API key is set without printing its value.

## Evolution

| File | Purpose |
| --- | --- |
| `config/evolution.yaml` | Check interval, mutation rates, fitness weights |
| `config/ab_tests.yaml` | A/B sample thresholds and promotion rules |

Reset local state:

```bash
python scripts/reset.py
# or
make bootstrap
```

## Benchmarks

| Command | Purpose |
| --- | --- |
| `python scripts/benchmark_runner.py --suite easy --simulate` | Offline suite |
| `python scripts/publish_benchmark_results.py --force --suite easy --simulate` | Write `benchmark/published/` |
| `python scripts/comparative_benchmark.py --suite easy --simulate --variants hermes_v1,laguna_v1 hermes_v2,laguna_v1` | Needs evolve first for `v2+` |

Published reports should be treated as `simulate` unless a live key was used (`--live` / CI live path).

## Portfolio commands

Mapped in [`../portfolio.yaml`](../portfolio.yaml) and [`../Makefile`](../Makefile):

```bash
make setup | bootstrap | doctor | demo | dev | check
```
