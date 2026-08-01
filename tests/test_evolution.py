# tests/test_evolution.py

from __future__ import annotations

import json
from pathlib import Path

from evals.evolution_engine import EvolutionEngine
from evals.scoring import calculate_fitness


def _seed_project(tmp_path: Path) -> Path:
    """Create an isolated project root with prompts + .autoclaw baselines."""
    # Point reset helpers at tmp by temporarily swapping path constants via local reset.
    (tmp_path / "prompts" / "hermes" / "evolved").mkdir(parents=True)
    (tmp_path / "prompts" / "laguna" / "evolved").mkdir(parents=True)
    (tmp_path / "prompts" / "hermes" / "few_shot").mkdir(parents=True, exist_ok=True)
    (tmp_path / "prompts" / "laguna" / "few_shot").mkdir(parents=True, exist_ok=True)

    # Copy base prompts from the real project for mutation reading.
    from prompts.hermes.base import HERMES_SYSTEM_PROMPT
    from prompts.laguna.base import LAGUNA_SYSTEM_PROMPT

    (tmp_path / "prompts" / "hermes" / "base.py").write_text(
        f'HERMES_SYSTEM_PROMPT = {HERMES_SYSTEM_PROMPT!r}\nSYSTEM_PROMPT = HERMES_SYSTEM_PROMPT\n',
        encoding="utf-8",
    )
    (tmp_path / "prompts" / "laguna" / "base.py").write_text(
        f'LAGUNA_SYSTEM_PROMPT = {LAGUNA_SYSTEM_PROMPT!r}\nSYSTEM_PROMPT = LAGUNA_SYSTEM_PROMPT\n',
        encoding="utf-8",
    )

    hermes = {
        "variant_id": "hermes_v1",
        "created": "2025-01-15T10:00:00Z",
        "parent_id": None,
        "mutation_source": "base",
        "system_prompt_path": "prompts/hermes/base.py",
        "few_shot_path": "prompts/hermes/few_shot/coding_examples.py",
        "system_prompt": HERMES_SYSTEM_PROMPT,
        "capability_vector": {"code_generation": 0.92},
        "trust_history": {"total_runs": 0, "success_rate": 0.0},
        "prompt_features": {"verbosity": "medium", "persona": "Senior Python Engineer"},
    }
    laguna = {
        "variant_id": "laguna_v1",
        "created": "2025-01-15T10:00:00Z",
        "parent_id": None,
        "mutation_source": "base",
        "system_prompt_path": "prompts/laguna/base.py",
        "few_shot_path": "prompts/laguna/few_shot/coding_examples.py",
        "system_prompt": LAGUNA_SYSTEM_PROMPT,
        "capability_vector": {"code_generation": 0.90},
        "trust_history": {"total_runs": 0, "success_rate": 0.0},
        "prompt_features": {"verbosity": "detailed"},
    }
    hdir = tmp_path / ".autoclaw" / "agents" / "genomes" / "hermes"
    ldir = tmp_path / ".autoclaw" / "agents" / "genomes" / "laguna"
    hdir.mkdir(parents=True)
    ldir.mkdir(parents=True)
    (hdir / "v1.json").write_text(json.dumps(hermes, indent=2), encoding="utf-8")
    (ldir / "v1.json").write_text(json.dumps(laguna, indent=2), encoding="utf-8")
    (tmp_path / ".autoclaw" / "evals").mkdir(parents=True)
    (tmp_path / ".autoclaw" / "evals" / "run_results.json").write_text(
        json.dumps({"total_runs": 0, "runs": []}), encoding="utf-8"
    )
    (tmp_path / ".autoclaw" / "evals" / "evolution_log.json").write_text(
        json.dumps({"entries": []}), encoding="utf-8"
    )
    (tmp_path / ".autoclaw" / "evals" / "best_configs.json").write_text(
        json.dumps(
            {
                "hermes": {"variant_id": "hermes_v1", "system_prompt_path": "prompts/hermes/base.py"},
                "laguna": {"variant_id": "laguna_v1", "system_prompt_path": "prompts/laguna/base.py"},
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def _rich_run(hermes="hermes_v1", laguna="laguna_v1", status="success", cost=0.1):
    return {
        "config": {
            "hermes_variant": hermes,
            "laguna_variant": laguna,
            "hermes_prompt_path": "prompts/hermes/base.py",
            "laguna_prompt_path": "prompts/laguna/base.py",
        },
        "task": {
            "spec_id": "task_sim",
            "complexity": "medium",
            "domain": "backend",
            "expected_cost": 0.15,
        },
        "result": {
            "status": status,
            "cost": cost,
            "time_seconds": 30,
            "iterations": 1,
            "executor_calls": 2,
        },
        "quality_metrics": {
            "task_spec_clarity": 0.92,
            "code_quality_score": 0.88,
            "quality_score": 0.88,
            "test_coverage": 0.85,
            "acceptance_criteria_pass": status == "success",
            "cost_efficiency": 0.59,
        },
    }


class TestEvolutionEngine:
    def test_init(self, tmp_path: Path):
        root = _seed_project(tmp_path)
        engine = EvolutionEngine(
            root=root,
            config={"check_interval_runs": 50, "hermes": {"mutation_rate": 0.3, "max_mutations_per_run": 2}, "laguna": {"mutation_rate": 0.4, "max_mutations_per_run": 3}, "scoring": {}, "selection": {"elite_size": 2}},
        )
        assert engine.active_hermes == "hermes_v1"
        assert engine.active_laguna == "laguna_v1"

    def test_record_run(self, tmp_path: Path):
        root = _seed_project(tmp_path)
        engine = EvolutionEngine(
            root=root,
            config={"check_interval_runs": 50, "hermes": {"max_mutations_per_run": 1, "mutation_rate": 1.0}, "laguna": {"max_mutations_per_run": 1, "mutation_rate": 1.0}, "scoring": {}, "selection": {"elite_size": 2}},
        )
        engine.record_run_result({"status": "success", "cost": 0.1, "time_seconds": 30})
        assert engine.run_count == 1

    def test_should_evolve(self, tmp_path: Path):
        root = _seed_project(tmp_path)
        engine = EvolutionEngine(
            root=root,
            config={"check_interval_runs": 50, "hermes": {"max_mutations_per_run": 1, "mutation_rate": 1.0}, "laguna": {"max_mutations_per_run": 1, "mutation_rate": 1.0}, "scoring": {}, "selection": {"elite_size": 2}},
        )
        assert not engine.should_evolve()
        engine.run_count = 50
        assert engine.should_evolve()

    def test_evaluate_variants(self, tmp_path: Path):
        root = _seed_project(tmp_path)
        engine = EvolutionEngine(
            root=root,
            config={"check_interval_runs": 50, "hermes": {"max_mutations_per_run": 1, "mutation_rate": 1.0}, "laguna": {"max_mutations_per_run": 1, "mutation_rate": 1.0}, "scoring": {}, "selection": {"elite_size": 2}},
        )
        for _ in range(10):
            engine.record_run_result(_rich_run())
        evaluation = engine.evaluate_current_variants()
        assert "hermes_v1" in evaluation["hermes_scores"]

    def test_evolve(self, tmp_path: Path):
        root = _seed_project(tmp_path)
        engine = EvolutionEngine(
            root=root,
            config={
                "check_interval_runs": 50,
                "hermes": {"max_mutations_per_run": 2, "mutation_rate": 1.0},
                "laguna": {"max_mutations_per_run": 2, "mutation_rate": 1.0},
                "scoring": {
                    "success_rate": 0.35,
                    "cost_efficiency": 0.30,
                    "quality_score": 0.25,
                    "time_efficiency": 0.10,
                },
                "selection": {"elite_size": 2},
            },
        )
        for _ in range(50):
            engine.record_run_result(_rich_run())

        result = engine.evolve()
        assert "hermes_variant" in result
        assert "laguna_variant" in result
        # New mutated genomes should have been created.
        assert result["new_hermes"] or result["new_laguna"]


def test_calculate_fitness_requires_samples():
    runs = [_rich_run() for _ in range(3)]
    score = calculate_fitness(runs, "hermes_v1", "laguna_v1")
    assert score["sample_size"] == 3
    assert score["composite"] == 0.0

    runs = [_rich_run() for _ in range(5)]
    score = calculate_fitness(runs, "hermes_v1", "laguna_v1")
    assert score["sample_size"] == 5
    assert score["composite"] > 0


def test_lineage_tracks_parent_child_edges(tmp_path: Path):
    root = _seed_project(tmp_path)
    engine = EvolutionEngine(
        root=root,
        config={
            "check_interval_runs": 50,
            "hermes": {"max_mutations_per_run": 2, "mutation_rate": 1.0},
            "laguna": {"max_mutations_per_run": 2, "mutation_rate": 1.0},
            "scoring": {
                "success_rate": 0.35,
                "cost_efficiency": 0.30,
                "quality_score": 0.25,
                "time_efficiency": 0.10,
            },
            "selection": {"elite_size": 2},
            "ab_testing": {
                "enabled": True,
                "min_samples_per_variant": 5,
                "confidence_interval": 0.95,
            },
            "alerting": {"enabled": True, "min_delta": 0.05},
        },
    )
    for _ in range(10):
        engine.record_run_result(_rich_run())

    result = engine.evolve()
    lineage = json.loads((root / ".autoclaw" / "agents" / "genomes" / "lineage.json").read_text())
    assert lineage["edges"], "expected parent→child lineage edges"
    children = {e["child"] for e in lineage["edges"]}
    assert set(result["new_hermes"]).issubset(children) or set(result["new_laguna"]).issubset(
        children
    )
    assert (root / ".autoclaw" / "evals" / "ab_tests.json").exists()
