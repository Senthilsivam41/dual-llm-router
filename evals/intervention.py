"""Human-intervention accounting for benchmark and live runs.

A run with no human step records ``human_intervened=False``. The rate is
then zero, not a missing field.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def intervention_from_pipeline(pipeline: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Return whether this pipeline run recorded a human step, and why."""
    if pipeline.get("human_intervened") is True:
        reason = pipeline.get("human_intervention_reason") or "human_step"
        return True, str(reason)

    if pipeline.get("status") == "needs_human":
        return True, str(pipeline.get("error") or "needs_human")

    executor = pipeline.get("executor_result") or {}
    for tool in executor.get("tool_results") or []:
        result = tool.get("result") or {}
        if result.get("needs_human") is True:
            return True, str(result.get("error") or "tool_needs_human")
    return False, None


def intervention_rate(results: List[Dict[str, Any]]) -> float:
    """Fraction of runs that needed a human. Empty input is 0.0."""
    if not results:
        return 0.0
    intervened = sum(1 for row in results if row.get("human_intervened") is True)
    return round(intervened / len(results), 4)
