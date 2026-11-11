#!/usr/bin/env python3
"""Write the durable fitness dashboard under evolution/dashboard/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.evolution_engine import EvolutionEngine
from evals.fitness_dashboard import dashboard_dir_for, write_fitness_dashboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the fitness trend dashboard")
    parser.add_argument("--root", type=str, default=None, help="Project root override")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Dashboard directory (default: <root>/evolution/dashboard)",
    )
    args = parser.parse_args(argv)
    engine = EvolutionEngine(root=Path(args.root) if args.root else None)
    output = Path(args.output) if args.output else dashboard_dir_for(engine)
    written = write_fitness_dashboard(engine, output)
    print(json.dumps(written, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
