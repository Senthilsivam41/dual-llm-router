from __future__ import annotations

import json
from pathlib import Path

from benchmark.tasks_loader import load_task_modules
from evals.benchmark_dashboard import BenchmarkDashboard
from evals.benchmark_runner import BenchmarkRunner
from evals.comparative_benchmark import ComparativeBenchmark, compare_results
from evals.evolution_engine import EvolutionEngine


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

    a = runner.results
    b = list(a)
    out = compare_results(a, b)
    assert out["results_1_count"] == out["results_2_count"]
