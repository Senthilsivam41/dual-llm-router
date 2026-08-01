#!/usr/bin/env python3
# scripts/analyze.py

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.evolution_engine import EvolutionEngine


def main() -> None:
    engine = EvolutionEngine()
    history = engine.get_best_config_history()

    print("Evolution Progress")
    print("=" * 60)

    if not history:
        print("No evolution history yet.")
        print(f"Recent runs: {engine.run_count}")
        print(f"Active Hermes: {engine.active_hermes}")
        print(f"Active Laguna: {engine.active_laguna}")
        return

    print(f"\nRecent runs: {engine.run_count}")
    print(f"Active Hermes: {engine.active_hermes}")
    print(f"Active Laguna: {engine.active_laguna}")

    print("\nFitness Trend:")
    for entry in history[-10:]:
        print(
            f"  Run #{entry['run_count']:3d} | "
            f"Hermes: {entry['hermes']} ({entry['hermes_score']:.4f}) | "
            f"Laguna: {entry['laguna']} ({entry['laguna_score']:.4f})"
        )

    print("\nTop Variants:")
    top = engine.evaluate_current_variants()
    for variant, scores in sorted(
        top["hermes_scores"].items(),
        key=lambda x: x[1]["composite"],
        reverse=True,
    )[:3]:
        print(f"  Hermes {variant}: {scores['composite']:.4f}")


if __name__ == "__main__":
    main()
