"""
Calculate fitness scores for agent variants based on run history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .paths import RUN_RESULTS_PATH

RUNS_FILE = RUN_RESULTS_PATH


def load_run_results(runs_file: Optional[Path] = None) -> List[Dict]:
    """Load all run results (append-only log)."""
    path = Path(runs_file or RUNS_FILE)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("runs", data.get("results", []))


def save_run_result(run_data: Dict, runs_file: Optional[Path] = None) -> None:
    """Append one run result to the append-only log."""
    path = Path(runs_file or RUNS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    runs = load_run_results(path)
    runs.append(run_data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "updated_at": run_data.get("timestamp"),
                "total_runs": len(runs),
                "runs": runs,
            },
            f,
            indent=2,
        )
        f.write("\n")


def calculate_fitness(
    runs: List[Dict],
    hermes_variant: str,
    laguna_variant: str,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Calculate composite fitness score for a (hermes, laguna) pair.

    Returns weighted fitness components.
    """
    matching = [
        r
        for r in runs
        if r.get("config", {}).get("hermes_variant") == hermes_variant
        and r.get("config", {}).get("laguna_variant") == laguna_variant
    ]

    if len(matching) < 5:
        return {
            "success_rate": 0.0,
            "cost_efficiency": 0.0,
            "quality_score": 0.0,
            "time_efficiency": 0.0,
            "sample_size": len(matching),
            "composite": 0.0,
        }

    successful = [
        r
        for r in matching
        if r.get("result", {}).get("status") in ("success", "completed")
    ]
    success_rate = len(successful) / len(matching)

    costs = [float(r.get("result", {}).get("cost", 0) or 0) for r in matching]
    expected_costs = [
        float(r.get("task", {}).get("expected_cost", 0) or 0) for r in matching
    ]
    ratios = [
        (exp / cost) if cost > 0 else 0.0
        for cost, exp in zip(costs, expected_costs)
        if exp > 0
    ]
    # Prefer expected/actual (higher when cheaper than expected); clamp to [0, 1.5].
    if ratios:
        cost_efficiency = min(1.5, sum(min(1.5, r) for r in ratios) / len(ratios)) / 1.5
    else:
        avg_cost = sum(costs) / len(costs) if costs else 0.0
        cost_efficiency = max(0.0, 1.0 - avg_cost)

    quality_scores = []
    for r in matching:
        qm = r.get("quality_metrics", {}) or {}
        score = qm.get("quality_score")
        if score is None:
            score = qm.get("code_quality_score")
        if score is None and qm.get("task_spec_clarity") is not None:
            # Blend available heuristics when quality_score is absent.
            parts = [
                qm.get("task_spec_clarity"),
                qm.get("code_quality_score"),
                qm.get("test_coverage"),
            ]
            parts = [float(p) for p in parts if p is not None]
            score = sum(parts) / len(parts) if parts else None
        if score is not None:
            quality_scores.append(float(score))
    quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    times = [float(r.get("result", {}).get("time_seconds", 0) or 0) for r in matching]
    avg_time = sum(times) / len(times) if times else 0.0
    time_efficiency = max(0.0, 1.0 - (avg_time / 60.0))

    weights = weights or {
        "success_rate": 0.35,
        "cost_efficiency": 0.30,
        "quality_score": 0.25,
        "time_efficiency": 0.10,
    }
    composite = (
        success_rate * weights["success_rate"]
        + cost_efficiency * weights["cost_efficiency"]
        + quality_score * weights["quality_score"]
        + time_efficiency * weights["time_efficiency"]
    )

    return {
        "success_rate": round(success_rate, 4),
        "cost_efficiency": round(cost_efficiency, 4),
        "quality_score": round(quality_score, 4),
        "time_efficiency": round(time_efficiency, 4),
        "sample_size": len(matching),
        "composite": round(composite, 4),
        "avg_cost": round(sum(costs) / len(costs), 4) if costs else 0.0,
        "avg_time": round(avg_time, 1),
    }


def score_variant(
    runs: List[Dict],
    hermes_variant: str,
    laguna_variant: str,
) -> Dict[str, float]:
    """Score a specific (hermes, laguna) variant combination."""
    return calculate_fitness(runs, hermes_variant, laguna_variant)


def get_top_variants(
    runs: List[Dict],
    top_n: int = 5,
) -> List[Tuple[Tuple[str, str], Dict[str, float]]]:
    """Get top N variant combinations by composite score."""
    hermes_variants = sorted(
        {
            r.get("config", {}).get("hermes_variant")
            for r in runs
            if r.get("config", {}).get("hermes_variant")
        }
    )
    laguna_variants = sorted(
        {
            r.get("config", {}).get("laguna_variant")
            for r in runs
            if r.get("config", {}).get("laguna_variant")
        }
    )

    all_scores = {}
    for hv in hermes_variants:
        for lv in laguna_variants:
            all_scores[(hv, lv)] = calculate_fitness(runs, hv, lv)

    sorted_scores = sorted(
        all_scores.items(), key=lambda x: x[1]["composite"], reverse=True
    )
    return sorted_scores[:top_n]
