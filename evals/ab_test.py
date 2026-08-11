"""
A/B testing framework for comparing variant combinations.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ABTestManager:
    """
    Manages A/B tests for dual-llm-router variants.

    Tracks:
    - Variant configurations
    - Run samples per variant
    - Statistical significance
    """

    def __init__(self, min_samples: int = 20, confidence: float = 0.95):
        self.min_samples = min_samples
        self.confidence = confidence
        self.ab_tests: List[Dict] = []

    def start_test(self, test_id: str, variants: List[Dict]) -> Dict:
        """Start a new A/B test."""
        test = {
            "test_id": test_id,
            "started": _utc_now(),
            "variants": variants,
            "status": "running",
            "results": [],
        }
        self.ab_tests.append(test)
        return test

    def record_result(self, test_id: str, variant: str, result: Dict) -> bool:
        """Record a result for a variant in an A/B test."""
        for test in self.ab_tests:
            if test["test_id"] == test_id and test["status"] == "running":
                test["results"].append(
                    {
                        "variant": variant,
                        "timestamp": _utc_now(),
                        "result": result,
                    }
                )
                return True
        return False

    def check_significance(self, test_id: str) -> Optional[Dict]:
        """Check if an A/B test reached statistical significance."""
        for test in self.ab_tests:
            if test["test_id"] == test_id and test["status"] == "running":
                variant_counts: Dict[str, int] = {}
                for r in test["results"]:
                    variant_counts[r["variant"]] = variant_counts.get(r["variant"], 0) + 1

                variant_ids = [
                    v.get("variant_id", v) if isinstance(v, dict) else v
                    for v in test["variants"]
                ]
                if variant_ids and all(
                    variant_counts.get(str(v), 0) >= self.min_samples for v in variant_ids
                ):
                    result = self._calculate_significance(test)
                    test["status"] = "completed"
                    test["result"] = result
                    return result
        return None

    def _calculate_significance(self, test: Dict) -> Dict:
        """Simplified significance calculation."""
        results = test["results"]

        variant_stats: Dict[str, Dict[str, int]] = {}
        for r in results:
            var = r["variant"]
            if var not in variant_stats:
                variant_stats[var] = {"successes": 0, "total": 0}
            variant_stats[var]["total"] += 1
            if r["result"].get("status") in ("success", "completed"):
                variant_stats[var]["successes"] += 1

        success_rates = {
            var: stats["successes"] / stats["total"]
            for var, stats in variant_stats.items()
            if stats["total"] > 0
        }

        chi2 = 0.0
        p_value = 1.0
        if len(variant_stats) == 2:
            first, second = variant_stats.values()
            pooled = (
                first["successes"] + second["successes"]
            ) / (first["total"] + second["total"])
            variance = pooled * (1.0 - pooled) * (
                (1.0 / first["total"]) + (1.0 / second["total"])
            )
            if variance > 0:
                first_rate = first["successes"] / first["total"]
                second_rate = second["successes"] / second["total"]
                z_score = (first_rate - second_rate) / math.sqrt(variance)
                chi2 = z_score * z_score
                p_value = math.erfc(abs(z_score) / math.sqrt(2.0))
        significant = p_value < (1.0 - self.confidence)

        return {
            "significant": significant,
            "chi2": chi2,
            "p_value": p_value,
            "success_rates": success_rates,
            "winner": max(success_rates, key=success_rates.get) if success_rates else None,
        }

    def get_test_status(self) -> List[Dict]:
        """Get status of all active tests."""
        status = []
        for t in self.ab_tests:
            variant_ids = [
                v.get("variant_id", v) if isinstance(v, dict) else v for v in t["variants"]
            ]
            status.append(
                {
                    "test_id": t["test_id"],
                    "status": t["status"],
                    "variant_counts": {
                        str(var): sum(1 for r in t["results"] if r["variant"] == var)
                        for var in variant_ids
                    },
                }
            )
        return status
