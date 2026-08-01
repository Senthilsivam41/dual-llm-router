#!/usr/bin/env python3
"""Write a GitHub Actions step summary from benchmark results / report JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.benchmark_dashboard import BenchmarkDashboard


def _append_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(text)
            if not text.endswith("\n"):
                f.write("\n")
    else:
        print(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="CI benchmark step summary")
    parser.add_argument("--results", type=str, default=None, help="results.json path")
    parser.add_argument("--report", type=str, default=None, help="Prebuilt report JSON")
    parser.add_argument("--title", type=str, default="Benchmark")
    args = parser.parse_args()

    if args.report and Path(args.report).exists():
        data = json.loads(Path(args.report).read_text(encoding="utf-8"))
        overall = data.get("overall") or data
        lines = [
            f"### {args.title}",
            "",
            "```json",
            json.dumps(overall, indent=2)[:4000],
            "```",
            "",
        ]
        _append_summary("\n".join(lines))
        return 0

    dash = BenchmarkDashboard(args.results)
    md = dash.write_github_summary()
    # Replace default heading with custom title.
    if md.startswith("### "):
        md = f"### {args.title}\n" + "\n".join(md.splitlines()[1:])
    _append_summary(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
