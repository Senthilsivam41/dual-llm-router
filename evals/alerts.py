"""Alerting for significant evolution improvements."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import ALERTS_LOG_PATH

logger = logging.getLogger("evals.alerts")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def detect_significant_improvement(
    evaluation_before: Dict[str, Any],
    best: Dict[str, Any],
    *,
    min_delta: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Compare previous composite fitness vs newly selected variants.

    Returns a list of alert payloads when improvement exceeds min_delta.
    """
    alerts: List[Dict[str, Any]] = []
    for agent in ("hermes", "laguna"):
        previous = float(
            (evaluation_before.get(f"current_{agent}") or {}).get("composite", 0.0) or 0.0
        )
        selected = best.get(agent) or {}
        new_score = float(selected.get("score", 0.0) or 0.0)
        delta = new_score - previous
        if delta >= min_delta:
            alerts.append(
                {
                    "type": "significant_improvement",
                    "agent": agent,
                    "variant_id": selected.get("variant_id"),
                    "previous_score": round(previous, 4),
                    "new_score": round(new_score, 4),
                    "delta": round(delta, 4),
                    "timestamp": _utc_now(),
                }
            )
    return alerts


def _append_alert_log(alert: Dict[str, Any], path: Path = ALERTS_LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(alert) + "\n")


def _post_webhook(url: str, payload: Dict[str, Any], timeout: float = 5.0) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return 200 <= getattr(resp, "status", 200) < 300
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("Webhook alert failed: %s", exc)
        return False


def emit_alerts(
    alerts: List[Dict[str, Any]],
    *,
    webhook_url: Optional[str] = None,
    log_path: Path = ALERTS_LOG_PATH,
) -> None:
    """Persist alerts locally and optionally POST to a webhook."""
    if not alerts:
        return

    webhook = webhook_url or os.getenv("EVOLUTION_ALERT_WEBHOOK")
    for alert in alerts:
        logger.info(
            "ALERT significant_improvement agent=%s variant=%s delta=+%.4f (%.4f -> %.4f)",
            alert.get("agent"),
            alert.get("variant_id"),
            alert.get("delta", 0.0),
            alert.get("previous_score", 0.0),
            alert.get("new_score", 0.0),
        )
        _append_alert_log(alert, log_path)
        if webhook:
            _post_webhook(webhook, alert)
