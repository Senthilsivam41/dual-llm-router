import time
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class CallMetric:
    node: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float
    cost_estimate_usd: float

class MetricsLogger:
    def __init__(self):
        self.metrics: List[CallMetric] = []

    def log_call(
        self,
        node: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_seconds: float,
        cost_per_1k_input: float = 0.001,
        cost_per_1k_output: float = 0.002,
        cost_estimate_usd: float | None = None,
    ) -> CallMetric:
        cost = (
            cost_estimate_usd
            if cost_estimate_usd is not None
            else ((prompt_tokens / 1000.0) * cost_per_1k_input)
            + ((completion_tokens / 1000.0) * cost_per_1k_output)
        )
        metric = CallMetric(
            node=node,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_seconds=latency_seconds,
            cost_estimate_usd=cost,
        )
        self.metrics.append(metric)
        return metric

    def summary(self) -> Dict[str, Any]:
        total_prompt = sum(m.prompt_tokens for m in self.metrics)
        total_completion = sum(m.completion_tokens for m in self.metrics)
        total_latency = sum(m.latency_seconds for m in self.metrics)
        total_cost = sum(m.cost_estimate_usd for m in self.metrics)
        return {
            "total_calls": len(self.metrics),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_latency_seconds": round(total_latency, 3),
            "total_cost_usd": round(total_cost, 6),
            "breakdown": [m.__dict__ for m in self.metrics],
        }
