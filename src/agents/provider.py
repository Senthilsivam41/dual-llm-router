from __future__ import annotations

from typing import Any, Callable, Dict

_TRANSIENT_PROVIDER_ERRORS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
)
try:
    from litellm.exceptions import (
        APIConnectionError,
        InternalServerError,
        RateLimitError,
        Timeout,
    )
except ImportError:
    pass
else:
    _TRANSIENT_PROVIDER_ERRORS += (
        Timeout,
        APIConnectionError,
        RateLimitError,
        InternalServerError,
    )


def _is_fireworks_model(model_name: str) -> bool:
    return model_name.startswith(("fireworks_ai/", "fireworks/"))


def resolve_api_key(model_name: str) -> str:
    """Pick the credential that matches the model provider."""
    from ..config import config

    if _is_fireworks_model(model_name):
        return config.fireworks_api_key
    return config.openrouter_api_key


def response_format_for(model_name: str) -> dict[str, str] | None:
    """Fireworks reasoning models return empty content when JSON mode is forced."""
    if _is_fireworks_model(model_name):
        return None
    return {"type": "json_object"}


def validate_provider_credentials(model_name: str, api_key: str) -> None:
    if model_name.startswith("openrouter/") and not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter models")
    if _is_fireworks_model(model_name) and not api_key:
        raise RuntimeError("FIREWORKS_API_KEY is required for Fireworks models")


def call_with_retry(
    provider: Callable[..., Any],
    *,
    max_retries: int,
    sleep: Callable[[float], None],
    kwargs: Dict[str, Any],
) -> Any:
    retries = max(0, max_retries)
    for attempt in range(retries + 1):
        try:
            payload = {key: value for key, value in kwargs.items() if value is not None}
            return provider(**payload)
        except _TRANSIENT_PROVIDER_ERRORS:
            if attempt >= retries:
                raise
            sleep(min(0.25 * (2**attempt), 2.0))
    raise RuntimeError("Provider retry loop exited unexpectedly")


def response_cost(response: Any) -> float | None:
    hidden = getattr(response, "_hidden_params", None)
    if not isinstance(hidden, dict):
        return None
    cost = hidden.get("response_cost")
    return float(cost) if cost is not None else None
