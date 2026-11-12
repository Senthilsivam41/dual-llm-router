"""Aggregate and render the paired reconciliation experiments."""

from __future__ import annotations

import html
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.showcase.report import write_run_folder

ARMS = {
    "first": "First attempt",
    "generic": "Generic retries",
    "diagnostics": "Retries with diagnostics",
    "candidate": "Development-guided prompt",
}
COMPARISONS = {
    "retry_feedback": ("generic", "diagnostics"),
    "prompt_feedback": ("first", "candidate"),
    "generic_vs_first": ("first", "generic"),
    "diagnostics_vs_first": ("first", "diagnostics"),
}
PRICE_SNAPSHOT = {
    "fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash": {
        "input": 0.30, "output": 1.20,
        "source": "https://fireworks.ai/models/deepseek-ai/deepseek-v4p1-flash",
    },
    "fireworks_ai/accounts/fireworks/models/glm-5p3-flash": {
        "input": 0.15, "output": 0.50,
        "source": "https://fireworks.ai/models/fireworks/glm-5p3-flash",
    },
}


def paired_effect(
    trials: list[dict[str, Any]], before: str, after: str, *, resamples: int = 10_000,
) -> dict[str, Any]:
    groups: dict[str, list[int]] = defaultdict(list)
    families: dict[str, dict[str, int]] = defaultdict(
        lambda: {"pairs": 0, "gains": 0, "regressions": 0}
    )
    for trial in trials:
        left, right = (trial["arms"].get(arm, {}).get("passed") for arm in (before, after))
        if left is None or right is None:
            continue
        delta = int(right) - int(left)
        groups[trial["scenario"]].append(delta)
        family = families[trial["family"]]
        family["pairs"] += 1
        family["gains"] += delta == 1
        family["regressions"] += delta == -1
    clusters = [(sum(values), len(values)) for values in groups.values()]
    pairs = sum(count for _, count in clusters)
    result = {
        "pairs": pairs, "scenarios": len(clusters), "by_family": dict(families),
        "delta_pp": None, "ci95_pp": None, "verdict": "inconclusive",
    }
    if not pairs:
        return result
    delta = sum(total for total, _ in clusters) / pairs
    result["delta_pp"] = delta * 100
    if len(clusters) < 2:
        return result
    rng = random.Random(20261112)
    samples = []
    for _ in range(resamples):
        sample = rng.choices(clusters, k=len(clusters))
        samples.append(sum(total for total, _ in sample) / sum(count for _, count in sample))
    samples.sort()
    interval = [samples[int((resamples - 1) * p)] for p in (0.025, 0.975)]
    result["ci95_pp"] = [bound * 100 for bound in interval]
    if delta >= 0.10 and interval[0] > 0:
        result["verdict"] = "improved"
    elif interval[1] < 0:
        result["verdict"] = "regressed"
    elif interval == [0, 0]:
        result["verdict"] = "flat"
    return result


def _trial_cost(
    trial: dict[str, Any], arm: str, prices: dict[str, Any],
) -> tuple[float | None, int]:
    executions = trial["executions"]
    segments = [trial["planning"]]
    if arm in {"generic", "diagnostics"} and "first" in executions:
        segments.append(executions["first"])
    if arm in executions:
        segments.append(executions[arm])
    calls = [call for segment in segments for call in segment["model_calls"]]
    if len(calls) != trial["arms"][arm]["calls"]:
        return None, 0
    total = 0.0
    estimated = 0
    for call in calls:
        value = call["cost_estimate_usd"]
        if value > 0:
            total += value
            estimated += call["cost_source"] == "estimate"
            continue
        rates = prices.get(call["model"])
        if rates is None or not (call["prompt_tokens"] or call["completion_tokens"]):
            return None, estimated
        total += (call["prompt_tokens"] * rates["input"]
                  + call["completion_tokens"] * rates["output"]) / 1_000_000
        estimated += 1
    return total, estimated


def _arm_summary(trials: list[dict[str, Any]], name: str, prices: dict[str, Any]) -> dict[str, Any]:
    eligible = [trial for trial in trials if name in trial["arms"]]
    observed = [trial for trial in eligible if trial["arms"][name]["passed"] is not None]
    rows = [trial["arms"][name] for trial in observed]
    passed = sum(row["passed"] for row in rows)
    cost_rows = [_trial_cost(trial, name, prices) for trial in observed]
    known_costs = [cost for cost, _ in cost_rows if cost is not None]
    cost = sum(known_costs) if len(known_costs) == len(cost_rows) else None
    times = sorted(row["wall_seconds"] for row in rows)
    first_failures = [
        trial for trial in observed if trial["arms"]["first"]["passed"] is False
    ]
    return {
        "passed": passed, "scored": len(rows), "incomplete": len(eligible) - len(rows),
        "pass_rate": passed / len(rows) if rows else None,
        "recovered": sum(trial["arms"][name]["passed"] for trial in first_failures),
        "first_failures": len(first_failures),
        "cost_per_verified_task_usd": cost / passed if cost is not None and passed else None,
        "median_wall_seconds": statistics.median(times) if times else None,
        "p95_wall_seconds": times[math.ceil(0.95 * len(times)) - 1] if times else None,
        "model_calls": sum(trial["arms"][name]["calls"] for trial in eligible),
        "estimated_cost_calls": sum(estimated for _, estimated in cost_rows),
    }


def summarize(record: dict[str, Any]) -> dict[str, Any]:
    trials = record["trials"]
    prices = record.get("pricing", {}).get("usd_per_million_tokens", {})
    retry_opportunities = sum(
        (trial["executions"].get("first") or {}).get("public_pass") is False for trial in trials
    )
    effects = {
        key: paired_effect(trials, before, after)
        for key, (before, after) in COMPARISONS.items()
    }
    if not retry_opportunities:
        for key in ("retry_feedback", "generic_vs_first", "diagnostics_vs_first"):
            effects[key]["verdict"] = "inconclusive"
    return {
        "arms": {
            name: _arm_summary(trials, name, prices)
            for name in ARMS if any(name in trial["arms"] for trial in trials)
        },
        "effects": effects,
        "attempted_study_calls": sum(
            trial["planning"]["calls"] + sum(execution["calls"] for execution in trial["executions"].values())
            for trial in record["development"] + trials
        ),
        "incomplete": [
            {"scenario": trial["scenario"], "trial": trial["repetition"],
             "arm": arm, "error": result["infrastructure_error"]}
            for trial in record["development"] + trials
            for arm, result in trial["arms"].items() if result["passed"] is None
        ],
        "retry_opportunities": retry_opportunities,
    }


def _display(value: float | None, spec: str) -> str:
    return "—" if value is None else format(value, spec)


def _rows(summary: dict[str, Any]) -> list[list[str]]:
    return [
        [
            ARMS[name], f"{row['passed']}/{row['scored']}", _display(row["pass_rate"], ".1%"),
            f"{row['recovered']}/{row['first_failures']}" if name != "first" else "—",
            _display(row["cost_per_verified_task_usd"], ".6f"),
            _display(row["median_wall_seconds"], ".2f"), _display(row["p95_wall_seconds"], ".2f"),
            str(row["model_calls"]), str(row["incomplete"]),
        ]
        for name, row in summary["arms"].items()
    ]


HEADERS = (
    "Arm", "Passed / scored", "Pass rate", "Recovered / first failures",
    "USD / verified task", "Median seconds", "p95 seconds", "Calls", "Incomplete",
)


def _effect_lines(summary: dict[str, Any]) -> list[str]:
    lines = []
    for key, effect in summary["effects"].items():
        before, after = COMPARISONS[key]
        interval = effect["ci95_pp"]
        ci = "unavailable" if interval is None else f"[{interval[0]:+.1f}, {interval[1]:+.1f}] pp"
        delta = _display(effect["delta_pp"], "+.1f")
        lines.append(
            f"{ARMS[after]} vs {ARMS[before]} — {delta} pp, 95% interval {ci}, "
            f"{effect['pairs']} paired trials across {effect['scenarios']} scenarios ({effect['verdict']})."
        )
    return lines


def _details(record: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    details = [
        f"Models — planner `{record['models']['planner']}`, executor `{record['models']['executor']}`.",
        f"Executed {len(record['development'])} development and {len(record['trials'])} evaluation trials.",
        f"Attempted study model calls — {summary['attempted_study_calls']}.",
        f"First attempts eligible for retry — {summary['retry_opportunities']}.",
        "Arm cost and timing cover scored trials and include the shared planning step and public verification. "
        "Private scoring and study orchestration are measured outside the arm.",
    ]
    if any(row["estimated_cost_calls"] for row in summary["arms"].values()):
        details.append("Some calls used estimated costs. Per-arm estimated call counts are in run.json.")
    if record.get("pricing"):
        details.append(
            "For zero-cost adapter responses with recorded token usage, the estimate applies the "
            f"Fireworks list prices checked on {record['pricing']['checked_on']}, "
            "with all input tokens priced at the uncached rate."
        )
    candidate = record["candidate"]
    if candidate and candidate.get("variant_id"):
        details.append(f"Prompt candidate — `{candidate['variant_id']}`, guidance from {', '.join(candidate['selected_codes'])}.")
    elif candidate and candidate.get("status") == "no_scored_development_trials":
        details.append("Infrastructure errors prevented development scoring and candidate generation.")
    elif candidate:
        details.append("Development produced zero actionable failures, so the prompt comparison has zero pairs.")
    if record.get("blocker"):
        details.append(f"Preflight or study interruption — {record['blocker']}")
    if summary["incomplete"]:
        details.append(f"Incomplete arm outcomes — {len(summary['incomplete'])}. See run.json for trial identifiers and error types.")
    if record.get("replayed"):
        details.insert(0, "Replay of a saved recording. This invocation made zero live model calls.")
    if record["mode"] == "scripted":
        details.insert(0, "Scripted model responses for demonstration. Quality, timing, and cost are illustrative.")
    return details


def render_markdown(record: dict[str, Any], summary: dict[str, Any]) -> str:
    lines = [
        "# Invoice reconciliation feedback benchmark", "",
        f"**{record['mode'].capitalize()} {record['scope']} · {record['status']}**", "",
        *[f"- {line}" for line in _details(record, summary)], "",
    ]
    lines.extend(
        ["| " + " | ".join(HEADERS) + " |", "| " + " | ".join("---" for _ in HEADERS) + " |"]
    )
    lines.extend("| " + " | ".join(row) + " |" for row in _rows(summary))
    lines.extend(["", "## Paired comparisons", "", *[f"- {line}" for line in _effect_lines(summary)]])
    lines.extend(["", "## Gains and regressions by family", ""])
    for name in ("retry_feedback", "prompt_feedback"):
        for family, row in summary["effects"][name]["by_family"].items():
            lines.append(
                f"- {name}, {family} — {row['gains']} gains and {row['regressions']} regressions "
                f"over {row['pairs']} pairs."
            )
    prices = record.get("pricing", {}).get("usd_per_million_tokens", {})
    if prices:
        lines.extend(["", "## Pricing sources", ""])
        for model, rates in prices.items():
            lines.append(
                f"- `{model}` uses ${rates['input']:.2f} per million input tokens and "
                f"${rates['output']:.2f} per million output tokens. [Fireworks model pricing]({rates['source']})"
            )
    return "\n".join(lines) + "\n"


def render_html(record: dict[str, Any], summary: dict[str, Any]) -> str:
    def tags(tag: str, values: list[str] | tuple[str, ...]) -> str:
        return "".join(f"<{tag}>{html.escape(value)}</{tag}>" for value in values)

    def evidence(data: Any) -> str:
        return f"<pre>{html.escape(json.dumps(data, indent=2, ensure_ascii=False))}</pre>"

    rows = "".join(f"<tr>{tags('td', row)}</tr>" for row in _rows(summary))
    details = tags("li", _details(record, summary))
    effects = tags("li", _effect_lines(summary))
    family = evidence({
        key: summary["effects"][key]["by_family"] for key in ("retry_feedback", "prompt_feedback")
    })
    example = ""
    if record["trials"]:
        selected = next(
            (trial for trial in record["trials"] if "diagnostics" in trial["executions"]),
            record["trials"][0],
        )
        executions = selected["executions"]
        first = executions.get("first", {})
        diagnostic = executions.get("diagnostics", first)
        example = f"""
        <h2>Example trial</h2><p>{html.escape(selected['scenario'])}</p>
        <details open><summary>Accepted plan</summary>{evidence(selected['planning']['task_spec'])}</details>
        <div class="comparison">
          <section><h3>First verdict</h3>{evidence(first.get('diagnostic'))}</section>
          <section><h3>Feedback and final verdict</h3>{evidence({
            'feedback': [attempt['feedback'] for attempt in diagnostic.get('attempts', []) if attempt.get('feedback')],
            'verdict': diagnostic.get('diagnostic'),
            'private_pass': diagnostic.get('private_pass'),
        })}</section>
        </div>"""
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Invoice reconciliation feedback benchmark</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;color:#17222b;background:#f3f6f7;margin:0}}
main{{max-width:1180px;margin:auto;padding:32px 20px}} h1,h2,h3{{line-height:1.15}}
table{{border-collapse:collapse;width:100%;background:white}} th,td{{text-align:left;padding:.65rem;border-bottom:1px solid #cbd6dc}}
.scroll{{overflow:auto}} pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.85rem}}
.comparison{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,22rem),1fr));gap:1rem}}
section,details{{background:#fff;padding:1rem;border:1px solid #cbd6dc;border-radius:8px}}
</style><main>
<h1>Invoice reconciliation feedback benchmark</h1>
<p><strong>{html.escape(record['mode'].capitalize())} {html.escape(record['scope'])} · {html.escape(record['status'])}</strong></p>
<ul>{details}</ul><div class="scroll"><table><thead><tr>{tags('th', HEADERS)}</tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>Paired comparisons</h2><ul>{effects}</ul>
<details><summary>Gains and regressions by family</summary>{family}</details>{example}
</main></html>
"""


def checkpoint(folder: Path, record: dict[str, Any]) -> None:
    temporary = folder / "run.json.tmp"
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.replace(folder / "run.json")


def write_report(folder: Path, record: dict[str, Any]) -> None:
    prices = {model: PRICE_SNAPSHOT[model] for model in record["models"].values() if model in PRICE_SNAPSHOT}
    if prices:
        record.setdefault("pricing", {
            "checked_on": "2026-11-12",
            "usd_per_million_tokens": prices,
        })
    summary = summarize(record)
    record["summary"] = summary
    write_run_folder(folder, record, render_html(record, summary))
    (folder / "report.md").write_text(render_markdown(record, summary), encoding="utf-8")
