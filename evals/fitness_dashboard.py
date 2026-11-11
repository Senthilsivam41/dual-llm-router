"""Durable fitness trend report. The console summary in scripts/analyze.py stays."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from evals.evolution_engine import EvolutionEngine


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def dashboard_dir_for(engine: EvolutionEngine) -> Path:
    return engine.project_root / "evolution" / "dashboard"


def _top_rows(scores: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    ranked = sorted(
        scores.items(),
        key=lambda item: float((item[1] or {}).get("composite") or 0.0),
        reverse=True,
    )
    rows = []
    for variant_id, score in ranked[:limit]:
        payload = score or {}
        rows.append(
            {
                "variant_id": variant_id,
                "composite": float(payload.get("composite") or 0.0),
                "success_rate": float(payload.get("success_rate") or 0.0),
                "sample_size": int(payload.get("sample_size") or 0),
            }
        )
    return rows


def _trend(series: List[Dict[str, Any]]) -> str:
    if len(series) < 2:
        return "flat"
    delta = float(series[-1]["pair_composite"]) - float(series[0]["pair_composite"])
    if delta >= 0.01:
        return "up"
    if delta <= -0.01:
        return "down"
    return "flat"


def build_fitness_report(engine: EvolutionEngine) -> Dict[str, Any]:
    """Fitness history plus the current active-pair scores."""
    evaluation = engine.evaluate_current_variants()
    series: List[Dict[str, Any]] = []
    for entry in engine.get_best_config_history():
        hermes_score = float(entry.get("hermes_score") or 0.0)
        laguna_score = float(entry.get("laguna_score") or 0.0)
        series.append(
            {
                "run_count": entry.get("run_count"),
                "hermes": entry.get("hermes"),
                "laguna": entry.get("laguna"),
                "hermes_score": hermes_score,
                "laguna_score": laguna_score,
                "pair_composite": round((hermes_score + laguna_score) / 2, 4),
            }
        )
    return {
        "generated_at": _utc_now(),
        "run_count": engine.run_count,
        "active_hermes": engine.active_hermes,
        "active_laguna": engine.active_laguna,
        "current_hermes": evaluation.get("current_hermes") or {},
        "current_laguna": evaluation.get("current_laguna") or {},
        "history": series,
        "trend": _trend(series),
        "top_hermes": _top_rows(evaluation.get("hermes_scores") or {}),
        "top_laguna": _top_rows(evaluation.get("laguna_scores") or {}),
    }


def fitness_fingerprint(report: Dict[str, Any]) -> Dict[str, Any]:
    """Identity of a report ignoring the generation timestamp."""
    return {
        "run_count": report.get("run_count"),
        "active_hermes": report.get("active_hermes"),
        "active_laguna": report.get("active_laguna"),
        "trend": report.get("trend"),
        "current_hermes": report.get("current_hermes") or {},
        "current_laguna": report.get("current_laguna") or {},
        "history": report.get("history") or [],
        "top_hermes": report.get("top_hermes") or [],
        "top_laguna": report.get("top_laguna") or [],
    }


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _sparkline(values: List[float]) -> str:
    if len(values) < 2:
        return "<p>Not enough evolution steps for a trend line.</p>"
    width = 640
    height = 160
    low = min(values)
    high = max(values)
    span = high - low or 1.0
    points = []
    last_index = len(values) - 1
    for index, value in enumerate(values):
        x = 0.0 if last_index == 0 else index * width / last_index
        y = height - ((value - low) / span) * (height - 8) - 4
        points.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'role="img" aria-label="Pair composite fitness over evolution steps">'
        f'<polyline fill="none" stroke="#1d4e89" stroke-width="2" points="{" ".join(points)}" />'
        "</svg>"
    )


def _metric_table(rows: List[Dict[str, Any]], empty: str) -> str:
    if not rows:
        return f"<p>{_esc(empty)}</p>"
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td><code>{_esc(row.get('variant_id'))}</code></td>"
            f"<td>{float(row.get('composite') or 0):.4f}</td>"
            f"<td>{float(row.get('success_rate') or 0):.4f}</td>"
            f"<td>{int(row.get('sample_size') or 0)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Variant</th><th>Composite</th>"
        "<th>Success</th><th>Samples</th></tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def render_fitness_html(report: Dict[str, Any]) -> str:
    history = report.get("history") or []
    values = [float(entry.get("pair_composite") or 0.0) for entry in history]
    history_rows = []
    for entry in history:
        history_rows.append(
            "<tr>"
            f"<td>{_esc(entry.get('run_count'))}</td>"
            f"<td><code>{_esc(entry.get('hermes'))}</code></td>"
            f"<td>{float(entry.get('hermes_score') or 0):.4f}</td>"
            f"<td><code>{_esc(entry.get('laguna'))}</code></td>"
            f"<td>{float(entry.get('laguna_score') or 0):.4f}</td>"
            f"<td>{float(entry.get('pair_composite') or 0):.4f}</td>"
            "</tr>"
        )
    history_table = (
        "<p>No evolution steps recorded yet.</p>"
        if not history_rows
        else (
            "<table><thead><tr><th>Run</th><th>Hermes</th><th>Score</th>"
            "<th>Laguna</th><th>Score</th><th>Pair</th></tr></thead><tbody>"
            + "".join(history_rows)
            + "</tbody></table>"
        )
    )
    current_hermes = report.get("current_hermes") or {}
    current_laguna = report.get("current_laguna") or {}
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Fitness trend</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem; color: #1c1c1c; background: #f7f4ef; }}
    h1, h2 {{ font-weight: normal; }}
    table {{ border-collapse: collapse; margin: 1rem 0 2rem; }}
    th, td {{ border-bottom: 1px solid #d5d0c8; text-align: left; padding: 0.35rem 0.75rem; }}
    code {{ font-family: ui-monospace, monospace; }}
  </style>
</head>
<body>
  <h1>Fitness trend</h1>
  <p>Generated {_esc(report.get("generated_at"))}. Active pair
    <code>{_esc(report.get("active_hermes"))}</code> /
    <code>{_esc(report.get("active_laguna"))}</code>.
    Runs {_esc(report.get("run_count"))}. Direction <strong>{_esc(report.get("trend"))}</strong>.</p>
  <p>Hermes composite {float(current_hermes.get("composite") or 0):.4f}
    (success {float(current_hermes.get("success_rate") or 0):.4f}).
    Laguna composite {float(current_laguna.get("composite") or 0):.4f}
    (success {float(current_laguna.get("success_rate") or 0):.4f}).</p>
  {_sparkline(values)}
  <h2>Evolution steps</h2>
  {history_table}
  <h2>Top Hermes variants</h2>
  {_metric_table(report.get("top_hermes") or [], "No Hermes scores yet.")}
  <h2>Top Laguna variants</h2>
  {_metric_table(report.get("top_laguna") or [], "No Laguna scores yet.")}
</body>
</html>
"""


def render_fitness_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Fitness trend",
        "",
        f"Generated `{report.get('generated_at')}`.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Active Hermes | `{report.get('active_hermes')}` |",
        f"| Active Laguna | `{report.get('active_laguna')}` |",
        f"| Runs | {report.get('run_count')} |",
        f"| Direction | {report.get('trend')} |",
        "",
        "## Evolution steps",
        "",
        "| Run | Hermes | Score | Laguna | Score | Pair |",
        "| ---: | --- | ---: | --- | ---: | ---: |",
    ]
    history = report.get("history") or []
    if not history:
        lines.append("| — | — | — | — | — | — |")
    for entry in history:
        lines.append(
            f"| {entry.get('run_count')} | `{entry.get('hermes')}` | "
            f"{float(entry.get('hermes_score') or 0):.4f} | `{entry.get('laguna')}` | "
            f"{float(entry.get('laguna_score') or 0):.4f} | "
            f"{float(entry.get('pair_composite') or 0):.4f} |"
        )
    lines.extend(["", "_Generated by `scripts/fitness_dashboard.py`._", ""])
    return "\n".join(lines)


def write_fitness_dashboard(
    engine: EvolutionEngine,
    output_dir: Optional[Path] = None,
    *,
    stamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Write fitness.html, fitness.json, and LATEST.md. Skip a new archive when unchanged."""
    output_dir = Path(output_dir) if output_dir else dashboard_dir_for(engine)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_fitness_report(engine)
    fingerprint = fitness_fingerprint(report)
    material_path = output_dir / "material.json"
    previous: Optional[Dict[str, Any]] = None
    if material_path.exists():
        try:
            loaded = json.loads(material_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = None
        if isinstance(loaded, dict):
            previous = loaded
    if previous and previous.get("fingerprint") == fingerprint:
        return {
            "path": str(output_dir / "LATEST.md"),
            "skipped": True,
            "stamp": previous.get("stamp"),
        }

    stamp = stamp or _stamp()
    archive = output_dir / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    archive_path = archive / f"fitness_{stamp}.json"
    archive_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output_dir / "fitness.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output_dir / "fitness.html").write_text(render_fitness_html(report), encoding="utf-8")
    latest = output_dir / "LATEST.md"
    latest.write_text(render_fitness_markdown(report), encoding="utf-8")
    material_path.write_text(
        json.dumps({"stamp": stamp, "fingerprint": fingerprint}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"path": str(latest), "skipped": False, "stamp": stamp}
