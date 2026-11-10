"""Terminal, HTML, and Markdown reports for an issue-to-fix run."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def costs_by_role(metrics: dict[str, Any]) -> dict[str, float]:
    planner = 0.0
    executor = 0.0
    for row in metrics.get("breakdown") or []:
        cost = float(row.get("cost_estimate_usd") or 0.0)
        node = str(row.get("node", "")).lower()
        if "planner" in node:
            planner += cost
        elif "executor" in node:
            executor += cost
    total = float(metrics.get("total_cost_usd") or (planner + executor))
    return {
        "planner": round(planner, 6),
        "executor": round(executor, 6),
        "total": round(total, 6),
    }


def build_run_record(
    pipeline: dict[str, Any],
    *,
    models: dict[str, str],
    kind: str = "live",
    success_rate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    executor = pipeline.get("executor_result") or {}
    report = executor.get("verification_report") or {}
    pytest_info = report.get("pytest") or {}
    status = pipeline.get("status")
    if status == "planning_failed":
        verdict = "planning_failed"
    elif status == "completed":
        verdict = "verified"
    else:
        verdict = "failed"
    recorded_label = None
    if kind == "recorded":
        recorded_label = "Recorded run, not live"
    return {
        "kind": kind,
        "recorded_label": recorded_label,
        "finished_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "verdict": verdict,
        "status": status,
        "error": pipeline.get("error"),
        "models": models,
        "sandbox": {
            "mode": pytest_info.get("sandbox"),
            "warning": pytest_info.get("warning"),
        },
        "planner_accuracy": pipeline.get("planner_accuracy"),
        "planner_disagreements": pipeline.get("planner_disagreements") or [],
        "planner_attempts": pipeline.get("planner_attempts"),
        "attempts": executor.get("attempts") or [],
        "checks": report.get("checks") or [],
        "costs": costs_by_role(pipeline.get("metrics") or {}),
        "task_spec": pipeline.get("task_spec"),
        "success_rate": success_rate,
    }


def render_terminal(record: dict[str, Any]) -> str:
    costs = record.get("costs") or {}
    lines = [
        f"Issue-to-fix  {record.get('verdict')}",
    ]
    if record.get("recorded_label"):
        lines.append(str(record["recorded_label"]))
    rate = record.get("success_rate") or {}
    if rate.get("total"):
        median_attempts = rate.get("median_attempts")
        attempt_word = "attempt" if median_attempts == 1 else "attempts"
        lines.append(
            "Verified in {verified} of {total} runs, median {median_attempts} {attempt_word}, "
            "median cost ${median_cost_usd}".format(
                verified=rate.get("verified"),
                total=rate.get("total"),
                median_attempts=median_attempts,
                attempt_word=attempt_word,
                median_cost_usd=rate.get("median_cost_usd"),
            )
        )
    accuracy = record.get("planner_accuracy")
    if accuracy is not None:
        lines.append(f"Planner accuracy: {float(accuracy):.0%} of report values")
    sandbox = record.get("sandbox") or {}
    if sandbox.get("warning"):
        lines.append(str(sandbox["warning"]))
    elif sandbox.get("mode"):
        lines.append(f"Sandbox: {sandbox['mode']}")
    lines.append(f"Attempts: {len(record.get('attempts') or [])}")
    lines.append(
        "Cost: planner ${planner:.6f}  executor ${executor:.6f}  total ${total:.6f}".format(
            planner=float(costs.get("planner") or 0),
            executor=float(costs.get("executor") or 0),
            total=float(costs.get("total") or 0),
        )
    )
    lines.append("")
    lines.append("Checks")
    for check in record.get("checks") or []:
        assertion = check.get("assertion") or {}
        where = ""
        if assertion:
            where = f"  {assertion.get('path')}:{assertion.get('line')}  {assertion.get('text')}"
        label = "required" if check.get("required") else "optional"
        lines.append(
            f"  {check.get('id')}  {check.get('source')}  {label}  "
            f"{check.get('expected_value')}  {'pass' if check.get('passed') else 'fail'}{where}"
        )
        if check.get("source") == "edge" and check.get("reason"):
            lines.append(f"    reason: {check['reason']}")
    if record.get("error"):
        lines.append("")
        lines.append(f"Error: {record['error']}")
    disagreements = record.get("planner_disagreements") or []
    if disagreements:
        lines.append("")
        lines.append("Planner arithmetic disagreements (report value still gates the tests)")
        for row in disagreements:
            lines.append(
                f"  {row.get('id')}  report {row.get('expected_value')}  "
                f"planner {row.get('planner_value')}"
            )
    return "\n".join(lines)


def render_markdown(record: dict[str, Any]) -> str:
    body = ["## Issue-to-fix", "", f"**Verdict:** {record.get('verdict')}"]
    if record.get("recorded_label"):
        body.append("")
        body.append(f"**{record['recorded_label']}**")
    body.append("")
    body.append("```")
    body.append(render_terminal(record))
    body.append("```")
    body.append("")
    return "\n".join(body)


def render_html(record: dict[str, Any]) -> str:
    title = html.escape(str(record.get("verdict") or "issue-to-fix"))
    banner = ""
    if record.get("recorded_label"):
        banner = f"<p class='banner'>{html.escape(str(record['recorded_label']))}</p>"
    rows = []
    for check in record.get("checks") or []:
        assertion = check.get("assertion") or {}
        location = ""
        if assertion:
            location = f"{assertion.get('path')}:{assertion.get('line')} {assertion.get('text')}"
        status = "pass" if check.get("passed") else "fail"
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(check.get('id')))}</td>"
            f"<td>{html.escape(str(check.get('source')))}</td>"
            f"<td>{'required' if check.get('required') else 'optional'}</td>"
            f"<td>{html.escape(str(check.get('expected_value')))}</td>"
            f"<td class='{status}'>{status}</td>"
            f"<td>{html.escape(location)}</td>"
            f"<td>{html.escape(str(check.get('reason') or ''))}</td>"
            "</tr>"
        )
    table = (
        "<table><thead><tr><th>Check</th><th>Source</th><th>Label</th>"
        "<th>Expected</th><th>Result</th><th>Assertion</th><th>Reason</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    pre = html.escape(render_terminal(record))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Issue-to-fix {title}</title>
<style>
body {{ font: 16px/1.45 "Iowan Old Style", Palatino, Georgia, serif; margin: 2rem auto; max-width: 52rem; color: #1c1915; background: #f7f3ea; }}
h1 {{ font-weight: 600; letter-spacing: -0.02em; }}
.banner {{ background: #1c1915; color: #f7f3ea; display: inline-block; padding: 0.2rem 0.6rem; }}
table {{ width: 100%; border-collapse: collapse; background: white; }}
th, td {{ text-align: left; padding: 0.45rem 0.5rem; border-bottom: 1px solid #e4dccb; font-family: ui-monospace, monospace; font-size: 13px; vertical-align: top; }}
.pass {{ color: #1f6b3a; }}
.fail {{ color: #8d2a2a; }}
pre {{ white-space: pre-wrap; background: white; padding: 1rem; }}
</style>
</head>
<body>
<h1>Issue-to-fix</h1>
{banner}
<pre>{pre}</pre>
{table}
</body>
</html>
"""


def render_compare_html(dual: dict[str, Any], single: dict[str, Any]) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Issue-to-fix comparison</title>
<style>
body {{ font: 16px/1.45 "Iowan Old Style", Palatino, Georgia, serif; margin: 2rem auto; max-width: 64rem; color: #1c1915; background: #f7f3ea; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
pre {{ white-space: pre-wrap; background: white; padding: 1rem; }}
@media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>Why two models</h1>
<div class="grid">
<section><h2>Planner and executor</h2><pre>{html.escape(render_terminal(dual))}</pre></section>
<section><h2>One model, both roles</h2><pre>{html.escape(render_terminal(single))}</pre></section>
</div>
</body>
</html>
"""


def write_run_folder(folder: Path, record: dict[str, Any], html_text: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    (folder / "report.html").write_text(html_text, encoding="utf-8")


def publish_success_rate(record: dict[str, Any], path: Path) -> None:
    """Append one live verdict. Does not replace a committed sample run."""
    if record.get("kind") != "live":
        return
    payload: dict[str, Any] = {"runs": []}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    attempts = record.get("attempts") or []
    payload.setdefault("runs", []).append(
        {
            "at": record.get("finished_at"),
            "verified": record.get("verdict") == "verified",
            "attempts": len(attempts),
            "cost_usd": (record.get("costs") or {}).get("total"),
        }
    )
    runs = payload["runs"]
    verified = sum(1 for run in runs if run.get("verified"))
    payload["verified"] = verified
    payload["total"] = len(runs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = path.with_suffix(".md")
    summary.write_text(
        "\n".join(
            [
                "# Showcase success rate",
                "",
                f"Verified in {verified} of {len(runs)} live showcase runs.",
                "",
                "This file is refreshed by the weekly job. It does not replace the committed sample under `examples/issue_to_fix/recorded/`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
