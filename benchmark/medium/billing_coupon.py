"""Invoice coupon bug used by the issue-to-fix showcase."""

from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[2] / "examples" / "issue_to_fix"

TASK = {
    "id": "medium_billing_coupon",
    "category": "medium",
    "domain": "debugging",
    "spec": (
        "Fix billing.py so invoice_total matches the Expected amounts in issue.md. "
        "Apply the fixed coupon before tax, sum line items before rounding to cents, "
        "and add pytest tests that assert those expected values."
    ),
    "acceptance_criteria": [
        "A $10 coupon on a $100 order with 8% tax charges the Expected amount, not the Charged amount",
        "Line items 1.235 and 1.235 with no tax charge the Expected amount",
        "pytest tests assert the Expected amounts and pass",
    ],
    "complexity_score": 0.45,
    "expected_cost": 0.01,
    "expected_time": 40,
    "difficulty": 2,
    "tags": ["python", "bugfix", "billing"],
    "seed_files": {
        "billing.py": (FIXTURE / "billing.py").read_text(encoding="utf-8"),
        "issue.md": (FIXTURE / "issue.md").read_text(encoding="utf-8"),
    },
    "max_iterations": 3,
}
