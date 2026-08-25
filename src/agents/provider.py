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


def validate_provider_credentials(model_name: str, api_key: str) -> None:
    if model_name.startswith("openrouter/") and not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter models")


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
            return provider(**kwargs)
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
