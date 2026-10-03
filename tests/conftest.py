"""Keep the suite hermetic when CI has no provider secrets."""

import pytest

from src.config import config


@pytest.fixture(autouse=True)
def hermetic_provider_credentials(monkeypatch):
    """Mocked agent tests still pass credential checks without a live key.

    Tests that assert the missing-key failure path override this themselves.
    """
    monkeypatch.setattr(config, "openrouter_api_key", "test-key")
    monkeypatch.setattr(config, "fireworks_api_key", "test-fireworks-key")
