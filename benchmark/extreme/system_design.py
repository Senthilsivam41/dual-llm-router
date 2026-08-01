"""Design + implement."""

TASK = {
    "id": "extreme_system_design",
    "category": "extreme",
    "domain": "architecture",
    "spec": (
        "Design and implement a local job queue with enqueue/dequeue, retries with backoff, "
        "dead-letter handling, and a small CLI. Persist jobs to disk so a process restart recovers "
        "pending work. Include architecture notes in README_QUEUE.md and tests."
    ),
    "acceptance_criteria": [
        "Jobs survive process restart",
        "Failed jobs retry with backoff then dead-letter",
        "CLI can enqueue and worker can process jobs",
        "Architecture notes document components",
        "pytest coverage for retry/dead-letter paths",
    ],
    "complexity_score": 0.95,
    "expected_cost": 1.2,
    "expected_time": 300,
    "difficulty": 5,
    "tags": ["python", "system-design", "persistence"],
}
