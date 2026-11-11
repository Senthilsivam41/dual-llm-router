#!/usr/bin/env python3
"""Decide whether the active genome pair may leave .autoclaw/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.evolution_engine import EvolutionEngine
from evals.promotion import apply_promotion, evaluate_promotion, promotion_dir_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote the active Hermes/Laguna pair when fitness gates pass.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write evolution/promoted when status is baseline or promote",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 when the decision is rejected",
    )
    parser.add_argument("--root", type=str, default=None, help="Project root override")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Snapshot directory (default: <root>/evolution/promoted)",
    )
    parser.add_argument("--snapshot-id", type=str, default=None)
    args = parser.parse_args(argv)

    engine = EvolutionEngine(root=Path(args.root) if args.root else None)
    output = Path(args.output) if args.output else promotion_dir_for(engine)
    decision = evaluate_promotion(engine, output_dir=output)
    if args.apply and decision["status"] in {"baseline", "promote"}:
        snapshot = apply_promotion(
            engine,
            decision,
            output_dir=output,
            snapshot_id=args.snapshot_id,
        )
        decision["applied_path"] = str(snapshot)
    print(json.dumps(decision, indent=2))
    print(
        f"promotion: {decision['status']}",
        file=sys.stderr,
    )
    if args.strict and decision["status"] == "rejected":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
