from __future__ import annotations

import json
from pathlib import Path

from evals.benchmark_publisher import is_major_change, publish_results
from evals.benchmark_runner import BenchmarkRunner
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


def test_is_major_change_detects_core_paths():
    assert is_major_change(["src/agents/planner.py"])
    assert is_major_change(["evals/benchmark_runner.py"])
    assert is_major_change(["prompts/hermes/base.py"])
    assert not is_major_change(["README.md", "docs/Evolution.md"])
    assert not is_major_change(["benchmark/published/LATEST.md"])


def test_publish_writes_timestamped_markdown(tmp_path: Path):
    engine = _seed_engine(tmp_path)
    state = tmp_path / ".autoclaw" / "evals" / "benchmark"
    runner = BenchmarkRunner(
        engine,
        benchmark_dir=state,
        simulate=True,
        workspace_root=str(tmp_path / "workspace"),
    )
    runner.run_benchmark_suite(suite="easy")
    results_path = runner.save_results()

    published = tmp_path / "benchmark" / "published"
    out = publish_results(
        results_path=results_path,
        published_dir=published,
        suite="easy",
        variant="hermes_v1,laguna_v1",
        simulate=True,
        trigger="test",
    )
    assert out.exists()
    assert out.name.startswith("benchmark_results_")
    assert out.name.endswith(".md")
    assert (published / "LATEST.md").exists()
    assert (published / "INDEX.md").exists()
    assert (published / "index.json").exists()
    body = out.read_text(encoding="utf-8")
    assert "Overall metrics" in body
    assert "System metrics" in body
    assert "Spec rejection rate" in body
    assert "By domain" in body
    assert "easy_simple_function" in body or "easy_basic_function" in body
