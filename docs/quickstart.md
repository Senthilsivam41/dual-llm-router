# Quickstart

Credential-free path first. Live OpenRouter is optional.

## Prerequisites

- Python 3.10+ (3.12 recommended)
- Optional: [uv](https://github.com/astral-sh/uv)

## Setup

```bash
make setup
# or: uv sync
cp .env.example .env   # only needed for live LLM calls
make bootstrap         # installs + resets .autoclaw/ evolution state
make doctor            # diagnose without printing secrets
```

## Five-minute demo (no API key)

```bash
make demo
```

This resets evolution state, runs the **easy** benchmark suite in `--simulate` mode, and prints the dashboard.

## Live path (optional)

```bash
export OPENROUTER_API_KEY=...   # or fill .env
python scripts/benchmark_runner.py --suite easy --variant hermes_v1,laguna_v1
python scripts/evolve.py --runs 40 --force
```

## Quality gate

```bash
make check
```

## More

- Architecture: [`architecture.md`](architecture.md)
- Configuration: [`configuration.md`](configuration.md)
- Evolution details: [`Evolution.md`](Evolution.md)
- Benchmarks / CI: [`../benchmark/README.md`](../benchmark/README.md), [`../benchmark/benchmark-cicd.md`](../benchmark/benchmark-cicd.md)
- Product memory: [`../memory/STATUS.md`](../memory/STATUS.md)
