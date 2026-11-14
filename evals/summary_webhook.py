"""Optional Slack or Discord delivery for the weekly benchmark summary.

The posted body is the same Markdown written to the Actions step summary.
A missing webhook secret skips delivery.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from evals.alerts import post_json_webhook

DISCORD_LIMIT = 1900


def weekly_summary_markdown(reports_dir: Path) -> str:
    """Summarize benchmark JSON artifacts the way the weekly job always has."""
    root = Path(reports_dir)
    files = sorted(root.rglob("*.json")) if root.exists() else []
    lines = [
        "## Weekly benchmark summary",
        "",
        f"Artifact JSON files: **{len(files)}**",
        "",
    ]
    shown = files[:40]
    for path in shown:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            lines.append(f"- `{path}`: parse error ({exc})")
            continue
        if not isinstance(data, dict):
            lines.append(f"- `{path.name}`: keys=[]")
            continue
        overall = data.get("overall") or data.get("variants") or data
        if isinstance(overall, dict) and "success_rate" in overall:
            lines.append(
                f"- `{path.name}`: success={overall.get('success_rate')} "
                f"quality={overall.get('avg_quality', overall.get('quality_score', 'n/a'))}"
            )
        elif data.get("winner"):
            lines.append(
                f"- `{path.name}`: winner=`{data.get('winner')}` "
                f"ranking={data.get('ranking')}"
            )
        else:
            lines.append(f"- `{path.name}`: keys={list(data)[:8]}")
    omitted = len(files) - len(shown)
    if omitted:
        lines.append(f"- {omitted} more JSON files omitted")
    lines.append("")
    return "\n".join(lines)


def webhook_destinations(environ: Mapping[str, str] | None = None) -> List[Tuple[str, str]]:
    """Return (kind, url) pairs for configured secrets. Blank values are ignored."""
    env = os.environ if environ is None else environ
    found: List[Tuple[str, str]] = []
    seen = set()
    slack = env.get("SLACK_WEBHOOK_URL", "").strip()
    discord = env.get("DISCORD_WEBHOOK_URL", "").strip()
    generic = env.get("BENCHMARK_SUMMARY_WEBHOOK", "").strip()
    if slack:
        found.append(("slack", slack))
        seen.add(slack)
    if discord:
        found.append(("discord", discord))
        seen.add(discord)
    if generic and generic not in seen:
        kind = "discord" if "discord.com/api/webhooks" in generic else "slack"
        found.append((kind, generic))
    return found


def message_payload(kind: str, text: str) -> Dict[str, Any]:
    if kind == "discord":
        body = text if len(text) <= DISCORD_LIMIT else text[:DISCORD_LIMIT] + "\n…"
        return {"content": body}
    return {"text": text}


def notify_weekly_summary(
    text: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> Dict[str, Any]:
    """Post the summary. No configured secret returns skipped=True and sends nothing."""
    destinations = webhook_destinations(environ)
    if not destinations:
        return {"skipped": True, "sent": [], "failed": []}

    sent: List[str] = []
    failed: List[str] = []
    for kind, url in destinations:
        if post_json_webhook(url, message_payload(kind, text)):
            sent.append(kind)
        else:
            failed.append(kind)
    return {"skipped": False, "sent": sent, "failed": failed}
