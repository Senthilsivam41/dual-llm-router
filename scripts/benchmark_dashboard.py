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
    parser.add_argument(
        "--save",
        "--output",
        dest="output",
        type=str,
        default=None,
        help="Write report JSON to path (alias: --output)",
    )
    args = parser.parse_args()

    dash = BenchmarkDashboard(args.results)

    if args.report == "comparison":
        if not args.compare_a or not args.compare_b:
            # Variant breakdown from a single results file (CI comparative artifact).
            report = dash.generate_report()
            comparison = {
                "generated_at": report.get("generated_at"),
                "by_variant": report.get("by_variant", {}),
                "overall": report.get("overall", {}),
            }
            print(json.dumps(comparison, indent=2))
            if args.output:
                out = Path(args.output)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
                print(f"\nSaved report to {out}")
            return
        comparison = dash.generate_comparison_report(args.compare_a, args.compare_b)
        print(json.dumps(comparison, indent=2))
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
            print(f"\nSaved report to {out}")
        return

    if args.report == "json":
        report = dash.generate_report()
        print(json.dumps(report, indent=2))
    else:
        dash.print_report()

    if args.output:
        path = dash.save_report(Path(args.output))
        print(f"\nSaved report to {path}")


if __name__ == "__main__":
    main()
