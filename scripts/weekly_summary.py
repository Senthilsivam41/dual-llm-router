#!/usr/bin/env python3
"""Write the weekly benchmark summary and optionally post it.

Missing SLACK_WEBHOOK_URL, DISCORD_WEBHOOK_URL, and BENCHMARK_SUMMARY_WEBHOOK
skip the post. The process still exits 0.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.summary_webhook import notify_weekly_summary, weekly_summary_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly benchmark summary")
    parser.add_argument("--reports", default="reports", help="Directory of benchmark JSON")
    parser.add_argument(
        "--output",
        default="reports/summary.md",
        help="Markdown file written with the same text as the step summary",
    )
    args = parser.parse_args()

    text = weekly_summary_markdown(Path(args.reports))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).write_text(text, encoding="utf-8")
    else:
        print(text)

    result = notify_weekly_summary(text)
    if result["skipped"]:
        print("Weekly summary webhook skipped (no secret).")
        return 0
    if result["sent"]:
        print("Posted weekly summary to " + ", ".join(result["sent"]) + ".")
    if result["failed"]:
        print("Weekly summary webhook failed for " + ", ".join(result["failed"]) + ".")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
