"""
Compare different variant combinations on the same benchmark suite.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from evals.benchmark_runner import BenchmarkResult, BenchmarkRunner
from evals.paths import AUTOCLAW_ROOT

BENCHMARK_STATE_DIR = AUTOCLAW_ROOT / "evals" / "benchmark"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ComparativeBenchmark:
    """Compare different variant combinations on the same benchmark suite."""

    def __init__(self, runner: BenchmarkRunner):
        self.runner = runner

    def compare_variants(
        self,
        variant_combos: List[Tuple[str, str]],
        task_ids: Optional[List[str]] = None,
        suite: Optional[str] = None,
    ) -> Dict:
        results_by_variant: Dict[str, List[BenchmarkResult]] = {}

        for combo in variant_combos:
            label = f"{combo[0]}+{combo[1]}"
            print(f"\nRunning benchmark with {label}")
            results = self.runner.run_benchmark_suite(
                task_ids=task_ids,
                variant_combo=combo,
                suite=suite,
            )
            results_by_variant[label] = results

        comparison = self._calculate_comparison(results_by_variant)
        out = BENCHMARK_STATE_DIR / "comparison.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"generated_at": _utc_now(), **comparison}, f, indent=2)
            f.write("\n")
        return comparison

    def _calculate_comparison(
        self, results_by_variant: Dict[str, List[BenchmarkResult]]
    ) -> Dict:
        comparison: Dict[str, Dict] = {"variants": {}}

        for label, results in results_by_variant.items():
            total = len(results)
            success_count = sum(1 for r in results if r.status == "success")
            success_rate = success_count / total if total else 0.0
            costs = [r.cost for r in results]
            times = [r.time_seconds for r in results]
            quality = [r.quality_score for r in results]
            expected = [r.expected_cost for r in results if r.expected_cost > 0]
            avg_cost = sum(costs) / len(costs) if costs else 0.0
            if expected and avg_cost > 0:
                cost_efficiency = (sum(expected) / len(expected)) / avg_cost
            else:
                cost_efficiency = 0.0

            comparison["variants"][label] = {
                "sample_size": total,
                "success_rate": round(success_rate, 4),
                "avg_cost": round(avg_cost, 4),
                "avg_time_seconds": round(sum(times) / len(times), 1) if times else 0.0,
                "avg_quality": round(sum(quality) / len(quality), 4) if quality else 0.0,
                "avg_executor_calls": round(
                    sum(r.executor_calls for r in results) / total, 1
                )
                if total
                else 0.0,
                "cost_efficiency": round(cost_efficiency, 4),
                "total_cost": round(sum(costs), 4),
                "total_time_seconds": round(sum(times), 1),
            }

        # Rank by success then quality then lower cost.
        ranked = sorted(
            comparison["variants"].items(),
            key=lambda kv: (
                kv[1]["success_rate"],
                kv[1]["avg_quality"],
                -kv[1]["avg_cost"],
            ),
            reverse=True,
        )
        comparison["ranking"] = [name for name, _ in ranked]
        comparison["winner"] = ranked[0][0] if ranked else None
        return comparison


def compare_results(
    results_1: List[BenchmarkResult],
    results_2: List[BenchmarkResult],
) -> Dict:
    """Compare two sets of results (e.g., before vs. after evolution)."""
    if not results_1 or not results_2:
        return {"error": "Empty results"}

    def calc_metrics(results: List[BenchmarkResult]) -> Dict[str, float]:
        n = len(results)
        return {
            "success_rate": sum(1 for r in results if r.status == "success") / n,
            "avg_cost": sum(r.cost for r in results) / n,
            "avg_time": sum(r.time_seconds for r in results) / n,
            "avg_quality": sum(r.quality_score for r in results) / n,
            "avg_iterations": sum(r.iterations for r in results) / n,
        }

    metrics_1 = calc_metrics(results_1)
    metrics_2 = calc_metrics(results_2)

    improvements = {}
    for metric in ("success_rate", "avg_cost", "avg_time", "avg_quality", "avg_iterations"):
        val_1 = metrics_1[metric]
        val_2 = metrics_2[metric]
        lower_better = metric in {"avg_cost", "avg_time", "avg_iterations"}
        if val_1 == 0:
            change = 0.0
            direction = "unchanged"
        elif lower_better:
            improved = val_2 < val_1
            change = abs((val_1 - val_2) / val_1) * 100
            direction = "improved" if improved else "degraded"
        else:
            improved = val_2 > val_1
            change = abs((val_2 - val_1) / val_1) * 100
            direction = "improved" if improved else "degraded"
        improvements[metric] = {
            "before": val_1,
            "after": val_2,
            "change": round(change, 2),
            "direction": direction,
        }

    return {
        "results_1_count": len(results_1),
        "results_2_count": len(results_2),
        "improvements": improvements,
        "is_better": all(v["direction"] == "improved" for v in improvements.values()),
    }


def load_results_file(path: Path) -> List[BenchmarkResult]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("results", [])
    return [BenchmarkResult.from_dict(r) for r in data]
