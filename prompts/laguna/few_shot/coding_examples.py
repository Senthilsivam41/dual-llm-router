"""Few-shot coding execution examples for Laguna executor."""

CODING_FEW_SHOT = [
    {
        "task_spec_goal": "Add an add(a, b) helper and cover it with a unit test",
        "actions": [
            {
                "type": "apply_patch",
                "file_path": "math_utils.py",
                "content": "def add(a, b):\n    return a + b\n",
            },
            {
                "type": "apply_patch",
                "file_path": "test_math_utils.py",
                "content": (
                    "from math_utils import add\n\n"
                    "def test_add():\n"
                    "    assert add(2, 3) == 5\n"
                ),
            },
            {"type": "run_shell", "command": "pytest -q test_math_utils.py"},
        ],
    },
]
