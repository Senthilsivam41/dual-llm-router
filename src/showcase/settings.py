"""Pinned models for the issue-to-fix showcase.

Repo-wide PLANNER_MODEL / EXECUTOR_MODEL stay on the OpenRouter defaults.
The showcase uses those variables only when they are set to something else.
"""

from __future__ import annotations

import os

PINNED_PLANNER = "fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash"
PINNED_EXECUTOR = "fireworks_ai/accounts/fireworks/models/glm-5p3-flash"

_REPO_DEFAULT_PLANNER = "openrouter/nousresearch/hermes-4-70b"
_REPO_DEFAULT_EXECUTOR = "openrouter/poolside/laguna-s-2.1"

USER_PROMPT = (
    "Fix the invoice bug described in issue.md. "
    "Update billing.py and add pytest tests that assert each check's expected value."
)


def _choose(specific: str, general: str, repo_default: str, pinned: str) -> str:
    override = os.getenv(specific)
    if override:
        return override
    general_value = os.getenv(general)
    if general_value and general_value != repo_default:
        return general_value
    return pinned


def showcase_models() -> tuple[str, str]:
    planner = _choose(
        "SHOWCASE_PLANNER_MODEL",
        "PLANNER_MODEL",
        _REPO_DEFAULT_PLANNER,
        PINNED_PLANNER,
    )
    executor = _choose(
        "SHOWCASE_EXECUTOR_MODEL",
        "EXECUTOR_MODEL",
        _REPO_DEFAULT_EXECUTOR,
        PINNED_EXECUTOR,
    )
    return planner, executor
