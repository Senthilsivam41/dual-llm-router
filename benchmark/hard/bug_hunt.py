"""Hunt down hidden bugs."""

TASK = {
    "id": "hard_bug_hunt",
    "category": "hard",
    "spec": (
        "The cache in `ttl_cache.py` intermittently returns stale or missing values under "
        "concurrent access and TTL expiry. Find and fix race/TTL bugs, add regression tests."
    ),
    "acceptance_criteria": [
        "Expired entries are never returned",
        "Concurrent gets/sets do not corrupt state",
        "Regression tests cover TTL expiry and concurrency",
        "pytest passes",
    ],
    "complexity_score": 0.8,
    "expected_cost": 0.5,
    "expected_time": 140,
    "difficulty": 4,
    "tags": ["python", "concurrency", "bugfix"],
}
