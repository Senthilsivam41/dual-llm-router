#!/usr/bin/env python3
# scripts/evolve.py

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.evolution_engine import EvolutionEngine


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger evolution")
    parser.add_argument("--runs", type=int, default=0, help="Number of runs to simulate")
    parser.add_argument("--force", action="store_true", help="Force evolution even if not due")
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Optional project root override (for isolated state)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    _configure_logging(args.verbose)

    engine = EvolutionEngine(root=Path(args.root) if args.root else None)

    if args.runs > 0:
        for _ in range(args.runs):
            engine.record_run_result(
                {
                    "config": {
                        "hermes_variant": engine.active_hermes,
                        "laguna_variant": engine.active_laguna,
                        "hermes_prompt_path": "prompts/hermes/base.py",
                        "laguna_prompt_path": "prompts/laguna/base.py",
                    },
                    "task": {
                        "spec_id": "sim",
                        "complexity": "medium",
                        "domain": "backend",
                        "expected_cost": 0.15,
                    },
                    "result": {
                        "status": "success",
                        "cost": 0.1,
                        "time_seconds": 30,
                    },
                    "quality_metrics": {
                        "quality_score": 0.85,
                        "code_quality_score": 0.85,
                        "task_spec_clarity": 0.9,
                        "acceptance_criteria_pass": True,
                    },
                }
            )

    if args.force or engine.should_evolve():
        result = engine.evolve()
        print(json.dumps(result, indent=2, default=str))
    else:
        interval = engine.config["check_interval_runs"]
        remaining = interval - (engine.run_count % interval) if interval else 0
        print(
            f"Waiting for evolution "
            f"(next check in ~{remaining} runs; current run #{engine.run_count})"
        )


if __name__ == "__main__":
    main()
