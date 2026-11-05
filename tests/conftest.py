"""Point the suite at Fireworks when that key is configured."""

import pytest

from src.config import config

FIREWORKS_PLANNER_MODEL = "fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash"
FIREWORKS_EXECUTOR_MODEL = "fireworks_ai/accounts/fireworks/models/glm-5p3-flash"


@pytest.fixture(autouse=True)
def fireworks_test_credentials(monkeypatch):
    """Use FIREWORKS_API_KEY for default planner and executor models.

    A dummy key is installed only when the environment has none, so mocked
    tests still pass in a checkout with no secrets. Tests that require a
    missing OpenRouter key clear that credential themselves.
    """
    if not config.fireworks_api_key:
        monkeypatch.setattr(config, "fireworks_api_key", "test-fireworks-key")
    if config.planner_model.startswith("openrouter/"):
        monkeypatch.setattr(config, "planner_model", FIREWORKS_PLANNER_MODEL)
    if config.executor_model.startswith("openrouter/"):
        monkeypatch.setattr(config, "executor_model", FIREWORKS_EXECUTOR_MODEL)
    if not config.openrouter_api_key:
        monkeypatch.setattr(config, "openrouter_api_key", "test-key")
