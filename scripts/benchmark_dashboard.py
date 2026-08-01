#!/usr/bin/env python3
# scripts/benchmark_dashboard.py

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.benchmark_dashboard import BenchmarkDashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark dashboard / reports")
    parser.add_argument("--results", type=str, default=None, help="Path to results.json")
    parser.add_argument(
        "--report",
        choices=["overall", "comparison", "json"],
        default="overall",
    )
    parser.add_argument("--compare-a", type=str, default=None)
    parser.add_argument("--compare-b", type=str, default=None)
    parser.add_argument("--save", type=str, default=None, help="Write report JSON to path")
    args = parser.parse_args()

    dash = BenchmarkDashboard(args.results)

    if args.report == "comparison":
        if not args.compare_a or not args.compare_b:
            parser.error("comparison requires --compare-a and --compare-b")
        comparison = dash.generate_comparison_report(args.compare_a, args.compare_b)
        print(json.dumps(comparison, indent=2))
        return

    if args.report == "json":
        report = dash.generate_report()
        print(json.dumps(report, indent=2))
    else:
        dash.print_report()

    if args.save:
        path = dash.save_report(Path(args.save))
        print(f"\nSaved report to {path}")


if __name__ == "__main__":
    main()
