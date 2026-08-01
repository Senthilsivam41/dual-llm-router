"""
Publish benchmark runs as versioned Markdown reports.

Standard location:
  benchmark/published/benchmark_results_<YYYYMMDD_HHMMSSZ>.md
  benchmark/published/LATEST.md
  benchmark/published/INDEX.md
  benchmark/published/index.json
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from evals.benchmark_dashboard import BenchmarkDashboard
from evals.paths import BENCHMARK_PUBLISHED_DIR, BENCHMARK_STATE_DIR, PROJECT_ROOT

logger = logging.getLogger("evals.benchmark_publisher")

MAJOR_CHANGE_PATH_PREFIXES = (
    "src/",
    "router/",
    "evals/",
    "prompts/",
    "benchmark/",
    "config/evolution.yaml",
    "config/ab_tests.yaml",
    "scripts/benchmark_",
    "scripts/evolve.py",
    "scripts/reset.py",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(dt: Optional[datetime] = None) -> str:
    moment = dt or _utc_now()
    return moment.strftime("%Y%m%d_%H%M%SZ")


def _git(cmd: Sequence[str]) -> str:
    try:
        out = subprocess.check_output(
            ["git", *cmd],
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def git_metadata() -> Dict[str, str]:
    return {
        "commit": _git(["rev-parse", "--short", "HEAD"]) or "unknown",
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown",
        "subject": _git(["log", "-1", "--pretty=%s"]) or "",
    }


def changed_files(base_ref: str = "HEAD~1") -> List[str]:
    """Return changed paths for major-change detection."""
    # Prefer merge-base style range; fall back to unstaged+staged for local use.
    for candidate in (
        ["diff", "--name-only", f"{base_ref}...HEAD"],
        ["diff", "--name-only", f"{base_ref}", "HEAD"],
    ):
        diff = _git(candidate)
        if diff:
            return [line for line in diff.splitlines() if line]

    unstaged = _git(["diff", "--name-only", "HEAD"])
    staged = _git(["diff", "--cached", "--name-only"])
    return sorted(set(filter(None, unstaged.splitlines() + staged.splitlines())))


def is_major_change(files: Sequence[str]) -> bool:
    """True when any changed path touches core router/evolution/benchmark code."""
    for path in files:
        if path.startswith("benchmark/published/"):
            continue
        for prefix in MAJOR_CHANGE_PATH_PREFIXES:
            if path == prefix.rstrip("/") or path.startswith(prefix):
                return True
    return False


def render_markdown(
    report: Dict[str, Any],
    *,
    results: List[Dict[str, Any]],
    meta: Dict[str, str],
    suite: str,
    variant: str,
    simulate: bool,
    trigger: str,
) -> str:
    overall = report.get("overall") or {}
    generated = report.get("generated_at") or _utc_now().isoformat().replace("+00:00", "Z")
    lines = [
        f"# Benchmark Results — {generated}",
        "",
        "## Run metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Timestamp (UTC) | `{generated}` |",
        f"| Git commit | `{meta.get('commit', 'unknown')}` |",
        f"| Branch | `{meta.get('branch', 'unknown')}` |",
        f"| Commit subject | {meta.get('subject') or '—'} |",
        f"| Suite | `{suite}` |",
        f"| Variant combo | `{variant}` |",
        f"| Mode | `{'simulate' if simulate else 'live'}` |",
        f"| Trigger | `{trigger}` |",
        f"| Total tasks | {report.get('total_runs', 0)} |",
        "",
        "## Overall metrics",
        "",
        "| Metric | Value | Target |",
        "| --- | --- | --- |",
        f"| Success rate | {float(overall.get('success_rate', 0)):.4f} | >0.90 |",
        f"| Avg cost (USD) | {float(overall.get('avg_cost', 0)):.4f} | decreasing |",
        f"| Cost efficiency (actual/expected) | {float(overall.get('cost_efficiency', 0)):.4f} | <1.0 |",
        f"| Avg time (s) | {float(overall.get('avg_time_seconds', 0)):.4f} | <60 |",
        f"| Avg quality | {float(overall.get('avg_quality', 0)):.4f} | >0.80 |",
        f"| Avg iterations | {float(overall.get('avg_iterations', 0)):.4f} | <5 |",
        f"| Total cost | {float(overall.get('total_cost', 0)):.4f} | — |",
        f"| Throughput (tasks/hr) | {float(overall.get('throughput_tasks_per_hour', 0)):.4f} | higher |",
        "",
        "## System metrics",
        "",
        "| Metric | Value | Target |",
        "| --- | --- | --- |",
        f"| Spec rejection rate | {float(overall.get('spec_rejection_rate', 0)):.4f} | <0.20 |",
        f"| Spec acceptance rate | {float(overall.get('spec_acceptance_rate', 0)):.4f} | >0.80 |",
        f"| Handoff failure rate | {float(overall.get('handoff_failure_rate', 0)):.4f} | <0.15 |",
        "",
        "## By category",
        "",
        "| Category | Count | Success | Avg cost | Avg time | Avg quality |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, metrics in sorted((report.get("by_category") or {}).items()):
        lines.append(
            f"| {category} | {metrics.get('count', 0)} | "
            f"{float(metrics.get('success_rate', 0)):.4f} | "
            f"{float(metrics.get('avg_cost', 0)):.4f} | "
            f"{float(metrics.get('avg_time', 0)):.4f} | "
            f"{float(metrics.get('avg_quality', 0)):.4f} |"
        )

    lines.extend(
        [
            "",
            "## By variant combo",
            "",
            "| Combo | Count | Success | Avg cost | Avg time | Avg quality |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for combo, metrics in sorted((report.get("by_variant") or {}).items()):
        lines.append(
            f"| `{combo}` | {metrics.get('count', 0)} | "
            f"{float(metrics.get('success_rate', 0)):.4f} | "
            f"{float(metrics.get('avg_cost', 0)):.4f} | "
            f"{float(metrics.get('avg_time', 0)):.4f} | "
            f"{float(metrics.get('avg_quality', 0)):.4f} |"
        )

    lines.extend(
        [
            "",
            "## By domain",
            "",
            "| Domain | Count | Success | Avg cost | Avg quality |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for domain, metrics in sorted((report.get("by_domain") or {}).items()):
        lines.append(
            f"| {domain} | {metrics.get('count', 0)} | "
            f"{float(metrics.get('success_rate', 0)):.4f} | "
            f"{float(metrics.get('avg_cost', 0)):.4f} | "
            f"{float(metrics.get('avg_quality', 0)):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Per-task results",
            "",
            "| Task | Category | Domain | Status | Quality | Cost | Time (s) | Hermes | Laguna |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in results:
        lines.append(
            f"| `{row.get('task_id', '')}` | {row.get('category', '')} | "
            f"{row.get('domain', 'general')} | {row.get('status', '')} | "
            f"{float(row.get('quality_score') or 0):.4f} | "
            f"{float(row.get('cost') or 0):.4f} | {float(row.get('time_seconds') or 0):.3f} | "
            f"`{row.get('variant_hermes', '')}` | `{row.get('variant_laguna', '')}` |"
        )

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- Machine-readable JSON: `.autoclaw/evals/benchmark/results.json`",
            "- Dashboard JSON: `.autoclaw/evals/benchmark/report.json`",
            "- Published index: [`INDEX.md`](INDEX.md)",
            "",
            "---",
            "",
            "_Generated by `scripts/publish_benchmark_results.py`._",
            "",
        ]
    )
    return "\n".join(lines)


def update_index(published_dir: Path, entry: Dict[str, str]) -> Path:
    """Maintain INDEX.md from a durable index.json (newest first)."""
    index_json = published_dir / "index.json"
    rows: List[Dict[str, str]] = []
    if index_json.exists():
        try:
            loaded = json.loads(index_json.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                rows = loaded
        except json.JSONDecodeError:
            rows = []

    rows = [r for r in rows if r.get("file") != entry["file"]]
    rows.insert(0, entry)
    index_json.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Published Benchmark Results",
        "",
        "Append-only history of benchmark publications. Newest first.",
        "",
        "Naming standard: `benchmark_results_<YYYYMMDD_HHMMSSZ>.md`",
        "",
        "| Timestamp (UTC) | Report | Commit | Suite | Success rate |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for row in rows:
        fname = row["file"]
        lines.append(
            f"| `{row['timestamp']}` | [{fname}]({fname}) | `{row['commit']}` | "
            f"`{row['suite']}` | {row['success_rate']} |"
        )
    lines.append("")
    index_path = published_dir / "INDEX.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def publish_results(
    *,
    results_path: Optional[Path] = None,
    published_dir: Path = BENCHMARK_PUBLISHED_DIR,
    suite: str = "all",
    variant: str = "hermes_v1,laguna_v1",
    simulate: bool = True,
    trigger: str = "manual",
    timestamp: Optional[datetime] = None,
) -> Path:
    """Write benchmark_results_<timestamp>.md + LATEST.md + INDEX.md."""
    published_dir.mkdir(parents=True, exist_ok=True)
    results_file = Path(results_path or BENCHMARK_STATE_DIR / "results.json")
    dash = BenchmarkDashboard(str(results_file))
    report = dash.generate_report()
    if report.get("error"):
        raise RuntimeError(f"Cannot publish benchmark results: {report['error']}")

    moment = timestamp or _utc_now()
    stamp = _stamp(moment)
    filename = f"benchmark_results_{stamp}.md"
    out_path = published_dir / filename
    meta = git_metadata()
    markdown = render_markdown(
        report,
        results=dash.results,
        meta=meta,
        suite=suite,
        variant=variant,
        simulate=simulate,
        trigger=trigger,
    )
    out_path.write_text(markdown, encoding="utf-8")
    (published_dir / "LATEST.md").write_text(markdown, encoding="utf-8")

    overall = report.get("overall") or {}
    update_index(
        published_dir,
        {
            "timestamp": stamp,
            "file": filename,
            "commit": meta.get("commit", "unknown"),
            "suite": suite,
            "success_rate": f"{float(overall.get('success_rate', 0)):.4f}",
        },
    )

    sidecar = published_dir / f"benchmark_results_{stamp}.json"
    sidecar.write_text(
        json.dumps(
            {
                "timestamp": stamp,
                "meta": meta,
                "suite": suite,
                "variant": variant,
                "simulate": simulate,
                "trigger": trigger,
                "report": report,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    logger.info("Published benchmark report to %s", out_path)
    return out_path
