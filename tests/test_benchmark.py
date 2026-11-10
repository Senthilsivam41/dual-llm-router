from __future__ import annotations

import json
from pathlib import Path

from benchmark.tasks_loader import load_task_modules
from evals.benchmark_dashboard import BenchmarkDashboard
from evals.benchmark_runner import BenchmarkRunner, BenchmarkTask
from evals.comparative_benchmark import (
    ComparativeBenchmark,
    compare_results,
    matrix_with_evolved_laguna,
)
from evals.evolution_engine import EvolutionEngine
from evals.intervention import intervention_from_pipeline, intervention_rate
from evals.workspace_acceptance import verify_workspace_criteria


def _seed_engine(tmp_path: Path) -> EvolutionEngine:
    (tmp_path / "prompts" / "hermes").mkdir(parents=True)
    (tmp_path / "prompts" / "laguna").mkdir(parents=True)
    (tmp_path / "prompts" / "hermes" / "base.py").write_text(
        'HERMES_SYSTEM_PROMPT = "hermes"\n', encoding="utf-8"
    )
    (tmp_path / "prompts" / "laguna" / "base.py").write_text(
        'LAGUNA_SYSTEM_PROMPT = "laguna"\n', encoding="utf-8"
    )
    genomes = tmp_path / ".autoclaw" / "agents" / "genomes"
    (genomes / "hermes").mkdir(parents=True)
    (genomes / "laguna").mkdir(parents=True)
    for agent in ("hermes", "laguna"):
        (genomes / agent / "v1.json").write_text(
            json.dumps(
                {
                    "variant_id": f"{agent}_v1",
                    "system_prompt_path": f"prompts/{agent}/base.py",
                    "prompt_features": {"verbosity": "medium"},
                }
            ),
            encoding="utf-8",
        )
    (tmp_path / ".autoclaw" / "evals").mkdir(parents=True)
    (tmp_path / ".autoclaw" / "evals" / "best_configs.json").write_text(
        json.dumps(
            {
                "hermes": {"variant_id": "hermes_v1"},
                "laguna": {"variant_id": "laguna_v1"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".autoclaw" / "evals" / "run_results.json").write_text(
        json.dumps({"runs": []}), encoding="utf-8"
    )
    (tmp_path / ".autoclaw" / "evals" / "evolution_log.json").write_text(
        json.dumps({"entries": []}), encoding="utf-8"
    )
    return EvolutionEngine(root=tmp_path)


def test_task_suite_loads_all_categories():
    tasks = load_task_modules()
    assert len(tasks) >= 20
    cats = {t["category"] for t in tasks}
    assert cats == {"easy", "medium", "hard", "extreme"}
    assert all(t.get("domain") for t in tasks)
    ids = {t["id"] for t in tasks}
    assert "easy_basic_function" in ids
    assert "easy_file_creation" in ids
    assert "medium_class_with_methods" in ids
    assert "medium_api_endpoint" in ids


def test_benchmark_runner_simulate(tmp_path: Path):
    engine = _seed_engine(tmp_path)
    runner = BenchmarkRunner(
        engine,
        benchmark_dir=tmp_path / ".autoclaw" / "evals" / "benchmark",
        simulate=True,
        workspace_root=str(tmp_path / "workspace"),
    )
    results = runner.run_benchmark_suite(suite="easy")
    assert results
    assert all(r.category == "easy" for r in results)
    path = runner.save_results()
    assert path.exists()

    dash = BenchmarkDashboard(str(path))
    report = dash.generate_report()
    assert report["total_runs"] == len(results)
    assert "overall" in report
    overall = report["overall"]
    assert "spec_rejection_rate" in overall
    assert "handoff_failure_rate" in overall
    assert "cost_efficiency" in overall
    assert overall["human_intervention_rate"] == 0.0
    assert all(r.human_intervened is False for r in results)
    assert "by_domain" in report
    assert all(r.domain for r in results)


def test_comparative_benchmark(tmp_path: Path):
    engine = _seed_engine(tmp_path)
    runner = BenchmarkRunner(
        engine,
        benchmark_dir=tmp_path / ".autoclaw" / "evals" / "benchmark",
        simulate=True,
        workspace_root=str(tmp_path / "workspace"),
    )
    comparative = ComparativeBenchmark(runner)
    comparison = comparative.compare_variants(
        [("hermes_v1", "laguna_v1")],
        suite="easy",
    )
    assert comparison["winner"] == "hermes_v1+laguna_v1"
    assert "hermes_v1+laguna_v1" in comparison["variants"]
    assert comparison["genomes"] == [
        {"combo": "hermes_v1+laguna_v1", "hermes": "hermes_v1", "laguna": "laguna_v1"}
    ]
    assert comparison["genome_ids"] == ["hermes_v1", "laguna_v1"]

    a = runner.results
    b = list(a)
    out = compare_results(a, b)
    assert out["results_1_count"] == out["results_2_count"]


def test_matrix_adds_evolved_laguna_mutants():
    genomes = {
        "hermes_v1": {"_agent": "hermes"},
        "hermes_v2": {"_agent": "hermes"},
        "laguna_v1": {"_agent": "laguna"},
        "laguna_m2": {"_agent": "laguna"},
    }
    combos = matrix_with_evolved_laguna(
        [("hermes_v1", "laguna_v1"), ("hermes_v2", "laguna_v1")],
        genomes,
    )
    assert combos == [
        ("hermes_v1", "laguna_v1"),
        ("hermes_v2", "laguna_v1"),
        ("hermes_v1", "laguna_m2"),
    ]


def test_intervention_rate_stays_zero_without_a_human_step():
    assert intervention_from_pipeline({"status": "completed"}) == (False, None)
    flagged, reason = intervention_from_pipeline(
        {
            "status": "failed",
            "executor_result": {
                "tool_results": [{"result": {"needs_human": True, "error": "blocked"}}]
            },
        }
    )
    assert flagged is True
    assert reason == "blocked"
    assert intervention_rate([]) == 0.0
    assert intervention_rate(
        [{"human_intervened": False}, {"human_intervened": True}]
    ) == 0.5


def test_generated_workspace_rejects_missing_assertion(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    engine = _seed_engine(tmp_path)

    class FakeRouter:
        def __init__(self, *args, **kwargs):
            self.workspace_root = kwargs["workspace_root"]

        def route_task(self, *args, **kwargs):
            root = Path(self.workspace_root)
            (root / "test_math_ops.py").write_text(
                "def test_other():\n    assert 1 == 1\n",
                encoding="utf-8",
            )
            return {
                "status": "completed",
                "metrics": {"total_cost_usd": 0.01, "breakdown": []},
                "executor_result": {
                    "success": True,
                    "verification_report": {"criteria_passed": True, "details": []},
                },
                "iterations": 1,
                "task_spec": {"goal": "factorial"},
            }

    monkeypatch.setattr("router.router.EvolvingRouter", FakeRouter)
    runner = BenchmarkRunner(
        engine,
        benchmark_dir=tmp_path / ".autoclaw" / "evals" / "benchmark",
        simulate=False,
        workspace_root=str(tmp_path / "workspace"),
    )
    task = BenchmarkTask(
        id="live_assert",
        category="easy",
        spec="Implement factorial",
        acceptance_criteria=["factorial(5) == 120"],
        complexity_score=0.2,
        expected_cost=0.05,
        expected_time=10,
    )
    result = runner.run_single_task(task, "hermes_v1", "laguna_v1")
    assert result.acceptance_criteria_details["factorial(5) == 120"] is False
    assert result.acceptance_criteria_passed is False
    assert result.status == "partial"
    assert result.human_intervened is False
    assert "120" in (result.failure_reason or "")


def test_workspace_accepts_asserted_expected_value(tmp_path: Path):
    (tmp_path / "math_ops.py").write_text(
        "def factorial(n):\n"
        "    if n < 0:\n"
        "        raise ValueError('negative')\n"
        "    result = 1\n"
        "    for i in range(1, n + 1):\n"
        "        result *= i\n"
        "    return result\n",
        encoding="utf-8",
    )
    (tmp_path / "test_math_ops.py").write_text(
        "from math_ops import factorial\n\n"
        "def test_fact():\n"
        "    assert factorial(5) == 120\n",
        encoding="utf-8",
    )
    report = verify_workspace_criteria(str(tmp_path), ["factorial(5) == 120"])
    assert report["details"]["factorial(5) == 120"] is True
    assert report["misses"] == []
