"""Latency-sensitive optimization."""

TASK = {
    "id": "extreme_performance_critical",
    "category": "extreme",
    "domain": "performance",
    "spec": (
        "Optimize a request fan-out simulator in `fanout.py` to keep p95 latency under a defined "
        "budget using concurrency limits, caching, and cancellation. Provide a microbenchmark and "
        "prove p95 improvement without changing response semantics."
    ),
    "acceptance_criteria": [
        "Semantics of successful responses unchanged",
        "p95 latency improves vs baseline script",
        "Concurrency is bounded (no unbounded task explosion)",
        "Benchmark script and pytest correctness suite included",
    ],
    "complexity_score": 0.92,
    "expected_cost": 0.9,
    "expected_time": 260,
    "difficulty": 5,
    "tags": ["python", "performance", "latency"],
}
