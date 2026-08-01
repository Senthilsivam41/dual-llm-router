"""Full feature implementation."""

TASK = {
    "id": "hard_feature_from_scratch",
    "category": "hard",
    "domain": "feature",
    "spec": (
        "Build a mini markdown-to-HTML converter supporting headings, bold/italic, links, and "
        "fenced code blocks. Expose `convert(md: str) -> str` and ship pytest fixtures for each "
        "supported construct."
    ),
    "acceptance_criteria": [
        "Headings h1-h3 convert correctly",
        "Bold and italic markers convert",
        "Links convert to anchor tags",
        "Fenced code blocks preserved with <pre><code>",
        "pytest suite passes",
    ],
    "complexity_score": 0.75,
    "expected_cost": 0.45,
    "expected_time": 120,
    "difficulty": 4,
    "tags": ["python", "feature", "parsing"],
}
