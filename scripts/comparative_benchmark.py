#!/usr/bin/env python3
"""CLI: compare variant combos or two saved result files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.benchmark_runner import BenchmarkRunner
from evals.comparative_benchmark import ComparativeBenchmark, compare_results, load_results_file
from evals.evolution_engine import EvolutionEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparative benchmark for dual-llm-router")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("RESULTS_A", "RESULTS_B"),
        help="Compare two saved results.json files",
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        help="Variant combos as hermes,laguna (space-separated)",
    )
    parser.add_argument("--suite", default="easy", choices=["easy", "medium", "hard", "extreme", "all"])
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()

    if args.compare:
        a = load_results_file(Path(args.compare[0]))
        b = load_results_file(Path(args.compare[1]))
        print(json.dumps(compare_results(a, b), indent=2))
        return

    if not args.variants:
        parser.error("Provide --variants hermes_v1,laguna_v1 ... or --compare A B")

    combos = []
    for item in args.variants:
        parts = [p.strip() for p in item.split(",")]
        if len(parts) != 2:
            parser.error(f"Invalid variant combo: {item}")
        combos.append((parts[0], parts[1]))

    runner = BenchmarkRunner(EvolutionEngine(), simulate=args.simulate)
    comparative = ComparativeBenchmark(runner)
    result = comparative.compare_variants(
        combos,
        suite=None if args.suite == "all" else args.suite,
    )
    runner.save_results()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
