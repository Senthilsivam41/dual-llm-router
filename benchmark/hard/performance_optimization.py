"""Optimize for speed/memory."""

TASK = {
    "id": "hard_performance_optimization",
    "category": "hard",
    "domain": "performance",
    "spec": (
        "Optimize `slow_search.py` naive substring search over a large corpus. Provide a faster "
        "implementation (e.g. Aho-Corasick / rolling hash / index) with the same public API and "
        "benchmarks showing >=2x speedup on the included fixture."
    ),
    "acceptance_criteria": [
        "Public API remains compatible",
        "Results match the naive implementation",
        "Documented benchmark shows >=2x speedup",
        "pytest correctness tests pass",
    ],
    "complexity_score": 0.8,
    "expected_cost": 0.55,
    "expected_time": 150,
    "difficulty": 4,
    "tags": ["python", "performance"],
}
