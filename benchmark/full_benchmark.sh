#!/usr/bin/env bash
# Full benchmark flow for dual-llm-router
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

SIM_FLAG=()
if [[ "${BENCHMARK_SIMULATE:-1}" == "1" ]] || [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  SIM_FLAG=(--simulate)
fi

echo "==> Reset evolution baselines"
"$PYTHON" scripts/reset.py

echo "==> Run suite with baseline variants"
"$PYTHON" scripts/benchmark_runner.py --suite all --variant hermes_v1,laguna_v1 "${SIM_FLAG[@]}"
cp .autoclaw/evals/benchmark/results.json .autoclaw/evals/benchmark/results_v1.json

echo "==> Optional second pass (same baseline unless evolved variants exist)"
"$PYTHON" scripts/benchmark_runner.py --suite all --variant hermes_v1,laguna_v1 "${SIM_FLAG[@]}"
cp .autoclaw/evals/benchmark/results.json .autoclaw/evals/benchmark/results_v2.json

echo "==> Compare result files"
"$PYTHON" scripts/comparative_benchmark.py \
  --compare .autoclaw/evals/benchmark/results_v1.json .autoclaw/evals/benchmark/results_v2.json

echo "==> Dashboard"
"$PYTHON" scripts/benchmark_dashboard.py --report overall --save .autoclaw/evals/benchmark/report.json

echo "==> Publish Markdown results"
"$PYTHON" scripts/publish_benchmark_results.py \
  --force --skip-run --suite all --variant hermes_v1,laguna_v1 \
  --trigger full_benchmark_sh "${SIM_FLAG[@]}"
