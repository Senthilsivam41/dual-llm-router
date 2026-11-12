"""Durable fitness dashboard beyond the analyze.py console summary."""

from __future__ import annotations

import json
from pathlib import Path

from evals.evolution_engine import EvolutionEngine
from evals.fitness_dashboard import render_fitness_html, write_fitness_dashboard
from test_evolution import _seed_project


def _engine_with_history(tmp_path: Path) -> EvolutionEngine:
    root = _seed_project(tmp_path)
    log = {
        "entries": [
            {
                "run_count": 10,
                "selected": {
                    "hermes": {"variant_id": "hermes_v1", "score": 0.40},
                    "laguna": {"variant_id": "laguna_v1", "score": 0.40},
                },
            },
            {
                "run_count": 20,
                "selected": {
                    "hermes": {"variant_id": "hermes_v1", "score": 0.60},
                    "laguna": {"variant_id": "laguna_v1", "score": 0.60},
                },
            },
        ]
    }
    (root / ".autoclaw" / "evals" / "evolution_log.json").write_text(
        json.dumps(log),
        encoding="utf-8",
    )
    return EvolutionEngine(
        root=root,
        config={
            "check_interval_runs": 50,
            "hermes": {"max_mutations_per_run": 1, "mutation_rate": 1.0},
            "laguna": {"max_mutations_per_run": 1, "mutation_rate": 1.0},
            "scoring": {},
            "selection": {"elite_size": 2},
        },
    )


def test_dashboard_writes_html_and_skips_unchanged(tmp_path: Path) -> None:
    engine = _engine_with_history(tmp_path)
    output = engine.project_root / "evolution" / "dashboard"
    first = write_fitness_dashboard(engine, output, stamp="20261111_000000Z")
    assert first["skipped"] is False
    html = (output / "fitness.html").read_text(encoding="utf-8")
    assert "Fitness trend" in html
    assert "hermes_v1" in html
    assert "0.6000" in html
    assert "<polyline" in html
    report = json.loads((output / "fitness.json").read_text(encoding="utf-8"))
    assert report["trend"] == "up"
    assert "hermes_v1" in render_fitness_html(report)

    second = write_fitness_dashboard(engine, output, stamp="20261111_010000Z")
    assert second["skipped"] is True
    archives = list((output / "archive").glob("fitness_*.json"))
    assert len(archives) == 1


def test_dashboard_renders_without_history(tmp_path: Path) -> None:
    root = _seed_project(tmp_path)
    engine = EvolutionEngine(
        root=root,
        config={
            "hermes": {"max_mutations_per_run": 1},
            "laguna": {"max_mutations_per_run": 1},
            "scoring": {},
            "selection": {},
        },
    )
    written = write_fitness_dashboard(engine, root / "evolution" / "dashboard")
    text = Path(written["path"]).read_text(encoding="utf-8")
    assert "Fitness trend" in text
    assert "hermes_v1" in text
