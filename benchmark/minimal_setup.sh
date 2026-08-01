#!/usr/bin/env bash
# Minimal benchmark setup for dual-llm-router
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p .autoclaw/evals/benchmark/tasks

cat > .autoclaw/evals/benchmark/tasks/sample_task.json << 'EOF'
{
    "id": "sample_simple_function",
    "category": "easy",
    "spec": "Write a Python function that adds two numbers and returns the result.",
    "acceptance_criteria": [
        "Function should return sum of two numbers",
        "Function should handle zero correctly",
        "Function should handle negative numbers"
    ],
    "complexity_score": 0.1,
    "expected_cost": 0.02,
    "expected_time": 5,
    "difficulty": 1,
    "tags": ["python", "basic"]
}
EOF

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" scripts/reset.py
"$PYTHON" scripts/benchmark_runner.py --suite easy --simulate --task sample_simple_function || \
  "$PYTHON" scripts/benchmark_runner.py --suite easy --simulate
"$PYTHON" scripts/benchmark_dashboard.py --report overall
