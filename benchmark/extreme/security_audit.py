"""Find and fix vulnerabilities."""

TASK = {
    "id": "extreme_security_audit",
    "category": "extreme",
    "spec": (
        "Audit `insecure_app/` for path traversal, command injection, and unsafe pickle usage. "
        "Patch each issue with secure defaults, add regression tests, and write SECURITY_FIXES.md "
        "listing CVEs-style findings."
    ),
    "acceptance_criteria": [
        "Path traversal blocked for file endpoints",
        "Shell commands no longer concatenate unsanitized input",
        "Pickle load of untrusted data removed or gated",
        "Regression tests fail on old vulnerable patterns",
        "SECURITY_FIXES.md documents each fix",
    ],
    "complexity_score": 0.95,
    "expected_cost": 1.0,
    "expected_time": 240,
    "difficulty": 5,
    "tags": ["python", "security"],
}
