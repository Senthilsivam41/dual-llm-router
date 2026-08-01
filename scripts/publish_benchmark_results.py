#!/usr/bin/env python3
"""
Run (optional) + publish benchmark results to benchmark/published/.

Examples:
  # Publish only if this commit touched major paths
  python scripts/publish_benchmark_results.py --if-major --suite easy --simulate

  # Always run + publish
  python scripts/publish_benchmark_results.py --force --suite all --simulate
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.benchmark_publisher import (
    changed_files,
    is_major_change,
    publish_results,
)
from evals.benchmark_runner import BenchmarkRunner
from evals.evolution_engine import EvolutionEngine
from evals.paths import BENCHMARK_PUBLISHED_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish timestamped benchmark Markdown results")
    parser.add_argument("--suite", default="easy", choices=["easy", "medium", "hard", "extreme", "all"])
    parser.add_argument("--variant", default="hermes_v1,laguna_v1")
    parser.add_argument("--simulate", action="store_true", default=True)
    parser.add_argument("--live", action="store_true", help="Use live OpenRouter instead of simulate")
    parser.add_argument("--force", action="store_true", help="Publish even without major changes")
    parser.add_argument(
        "--if-major",
        action="store_true",
        help="Skip unless commit changes major code paths",
    )
    parser.add_argument(
        "--base-ref",
        default="HEAD~1",
        help="Git ref to diff against for major-change detection",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Publish from existing .autoclaw results without re-running",
    )
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    files = changed_files(args.base_ref)
    major = is_major_change(files)
    if args.if_major and not args.force and not major:
        print("No major code changes detected; skipping benchmark publish.")
        if files:
            print("Changed files:")
            for f in files:
                print(f"  - {f}")
        return 0

    simulate = not args.live
    if args.live:
        simulate = False

    if not args.skip_run:
        parts = [p.strip() for p in args.variant.split(",")]
        if len(parts) != 2:
            parser.error("--variant must be hermes_id,laguna_id")
        engine = EvolutionEngine()
        runner = BenchmarkRunner(engine, simulate=simulate)
        runner.run_benchmark_suite(
            variant_combo=(parts[0], parts[1]),
            suite=None if args.suite == "all" else args.suite,
        )
        runner.save_results()

    out = publish_results(
        suite=args.suite,
        variant=args.variant,
        simulate=simulate,
        trigger=args.trigger,
    )
    print(f"Published: {out}")
    print(f"Latest:    {BENCHMARK_PUBLISHED_DIR / 'LATEST.md'}")
    print(f"Index:     {BENCHMARK_PUBLISHED_DIR / 'INDEX.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
