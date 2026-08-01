"""Few-shot coding TaskSpec examples for Hermes planner."""

CODING_FEW_SHOT = [
    {
        "user": "Create math_utils.py with add(a, b) and a unit test.",
        "task_spec": {
            "goal": "Add an add(a, b) helper and cover it with a unit test",
            "target_files": ["math_utils.py", "test_math_utils.py"],
            "acceptance_criteria": [
                "math_utils.py exists and defines add(a, b)",
                "test_math_utils.py exists and pytest passes",
            ],
            "step_by_step_plan": [
                "Create math_utils.py with add(a, b)",
                "Create test_math_utils.py asserting add(2, 3) == 5",
                "Run pytest on test_math_utils.py",
            ],
            "notes": "Keep the implementation minimal.",
        },
    },
]
