#!/usr/bin/env bash
# Periodic evolution check for dual-llm-router.
# Install (hourly):
#   0 * * * * cd /path/to/dual-llm-router && ./scripts/cron_evolve.sh >> .autoclaw/evals/cron.log 2>&1

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "No python interpreter found" >&2
  exit 1
fi

mkdir -p "$ROOT/.autoclaw/evals"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] cron_evolve start"

# Run the evolve CLI. It only mutates/promotes when should_evolve() is true,
# unless EVOLUTION_FORCE=1 is set.
FORCE_ARGS=()
if [[ "${EVOLUTION_FORCE:-0}" == "1" ]]; then
  FORCE_ARGS+=(--force)
fi

"$PYTHON" "$ROOT/scripts/evolve.py" "${FORCE_ARGS[@]}"
"$PYTHON" "$ROOT/scripts/analyze.py" || true

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] cron_evolve done"
