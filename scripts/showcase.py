#!/usr/bin/env python3
"""Run the bundled invoice bug showcase, or replay a recorded run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.showcase.session import run_showcase


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue-to-fix showcase")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Also run the executor model in both roles",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the HTML report in a browser",
    )
    parser.add_argument(
        "--publish-rate",
        action="store_true",
        help="Append this live verdict to benchmark/published/showcase_success_rate.json",
    )
    args = parser.parse_args()
    return run_showcase(
        compare=args.compare,
        open_browser=not args.no_open,
        publish_rate=args.publish_rate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
