#!/usr/bin/env python3
"""CLI: run dual-llm-router benchmark suites."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.benchmark_runner import BenchmarkRunner
from evals.evolution_engine import EvolutionEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run dual-llm-router benchmarks")
    parser.add_argument(
        "--suite",
        choices=["easy", "medium", "hard", "extreme", "all"],
        default="easy",
        help="Difficulty suite to run",
    )
    parser.add_argument(
        "--variant",
        type=str,
        default=None,
        help="Variant combo hermes_id,laguna_id (default: active genomes)",
    )
    parser.add_argument("--task", action="append", dest="tasks", help="Specific task id(s)")
    parser.add_argument("--simulate", action="store_true", help="Force offline simulation")
    parser.add_argument("--list", action="store_true", help="List tasks and exit")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    engine = EvolutionEngine()
    runner = BenchmarkRunner(engine, simulate=args.simulate)

    if args.list:
        for task in runner.list_tasks(None if args.suite == "all" else args.suite):
            print(f"{task.id:35s}  {task.category:8s}  d={task.difficulty}  {task.spec[:60]}...")
        return

    combo = None
    if args.variant:
        parts = [p.strip() for p in args.variant.split(",")]
        if len(parts) != 2:
            parser.error("--variant must be hermes_id,laguna_id")
        combo = (parts[0], parts[1])

    results = runner.run_benchmark_suite(
        task_ids=args.tasks,
        variant_combo=combo,
        suite=None if args.suite == "all" else args.suite,
    )
    out = runner.save_results()
    summary = {
        "tasks": len(results),
        "success": sum(1 for r in results if r.status == "success"),
        "avg_quality": round(sum(r.quality_score for r in results) / len(results), 4)
        if results
        else 0,
        "results_path": str(out),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
