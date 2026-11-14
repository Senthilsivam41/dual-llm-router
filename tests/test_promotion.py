"""Gates for copying winning genomes out of .autoclaw/."""

from __future__ import annotations

import json
from pathlib import Path

from evals.evolution_engine import EvolutionEngine
from evals.promotion import apply_promotion, evaluate_promotion
from scripts.promote_genomes import main as promote_main
from test_evolution import _seed_project


def _engine(tmp_path: Path) -> EvolutionEngine:
    root = _seed_project(tmp_path)
    return EvolutionEngine(
        root=root,
        config={
            "check_interval_runs": 50,
            "hermes": {"mutation_rate": 1.0, "max_mutations_per_run": 1},
            "laguna": {"mutation_rate": 1.0, "max_mutations_per_run": 1},
            "scoring": {},
            "selection": {"elite_size": 2},
            "promotion": {
                "min_delta": 0.05,
                "min_samples": 5,
                "regression_tolerance": 0.0,
            },
            "ab_testing": {"min_samples_per_variant": 20, "confidence_interval": 0.95},
        },
    )


def _run(
    hermes: str = "hermes_v1",
    laguna: str = "laguna_v1",
    *,
    status: str = "success",
    quality: float = 0.2,
    cost: float = 0.2,
    time_seconds: float = 50,
) -> dict:
    return {
        "config": {"hermes_variant": hermes, "laguna_variant": laguna},
        "task": {"spec_id": "sim", "expected_cost": 0.15},
        "result": {"status": status, "cost": cost, "time_seconds": time_seconds},
        "quality_metrics": {"quality_score": quality},
    }


def _record_pair(engine: EvolutionEngine, count: int, **kwargs) -> None:
    hermes = kwargs.pop("hermes", engine.active_hermes)
    laguna = kwargs.pop("laguna", engine.active_laguna)
    for _ in range(count):
        engine.record_run_result(_run(hermes, laguna, **kwargs))


def _install_hermes(engine: EvolutionEngine, variant_id: str, suffix: str) -> None:
    parent = engine.genomes["hermes_v1"]
    genome = {key: value for key, value in parent.items() if not str(key).startswith("_")}
    genome["variant_id"] = variant_id
    genome["parent_id"] = "hermes_v1"
    genome["system_prompt"] = str(parent.get("system_prompt", "")) + suffix
    genome["_agent"] = "hermes"
    engine.genomes[variant_id] = genome
    engine.active_hermes = variant_id


def test_rejects_thin_evidence_and_dry_run_writes_nothing(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _record_pair(engine, 2)
    decision = evaluate_promotion(engine)
    assert decision["status"] == "rejected"
    assert any("sample_size" in reason for reason in decision["reasons"])
    code = promote_main(["--root", str(engine.project_root), "--strict"])
    assert code == 2
    assert not (engine.project_root / "evolution" / "promoted" / "snapshots").exists()


def test_rejects_secret_material(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _record_pair(engine, 8)
    engine.genomes["hermes_v1"]["api_key"] = "not-a-real-key"
    decision = evaluate_promotion(engine)
    assert decision["status"] == "rejected"
    assert any("secret material" in reason for reason in decision["reasons"])


def test_rejects_secret_text_and_a_later_secret_field(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    output = engine.project_root / "evolution" / "promoted"
    _record_pair(engine, 8)
    engine.genomes["hermes_v1"]["system_prompt"] += '\n"api_key": "supersecret"\n'
    quoted = evaluate_promotion(engine, output_dir=output)
    assert quoted["status"] == "rejected"
    assert any("secret material" in reason for reason in quoted["reasons"])

    engine.genomes["hermes_v1"]["system_prompt"] = engine.genomes["hermes_v1"]["system_prompt"].split(
        "\n\"api_key\""
    )[0] + "\nsk-proj-abcdefghijklmnopqrstuvwxyz\n"
    hyphenated = evaluate_promotion(engine, output_dir=output)
    assert hyphenated["status"] == "rejected"

    engine.genomes["hermes_v1"]["system_prompt"] = engine.genomes["hermes_v1"]["system_prompt"].split(
        "\nsk-proj-"
    )[0]
    baseline = evaluate_promotion(engine, output_dir=output)
    assert baseline["status"] == "baseline"
    apply_promotion(engine, baseline, output_dir=output, snapshot_id="baseline-secret")
    engine.genomes["hermes_v1"]["api_key"] = "not-a-real-key"
    later = evaluate_promotion(engine, output_dir=output)
    assert later["status"] == "rejected"
    assert any("secret material" in reason for reason in later["reasons"])


def test_baseline_then_unchanged(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _record_pair(engine, 8)
    output = engine.project_root / "evolution" / "promoted"
    decision = evaluate_promotion(engine, output_dir=output)
    assert decision["status"] == "baseline"
    snapshot = apply_promotion(engine, decision, output_dir=output, snapshot_id="baseline-1")
    stored = json.loads((snapshot / "hermes.json").read_text(encoding="utf-8"))
    assert stored["variant_id"] == "hermes_v1"
    assert "_agent" not in stored
    assert "_path" not in stored
    again = evaluate_promotion(engine, output_dir=output)
    assert again["status"] == "unchanged"
    try:
        apply_promotion(engine, again, output_dir=output, snapshot_id="baseline-2")
    except ValueError as exc:
        assert "cannot apply" in str(exc)
    else:
        raise AssertionError("unchanged decision was applied")


def test_promotes_improved_pair_and_rejects_regression(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    output = engine.project_root / "evolution" / "promoted"
    _record_pair(engine, 8)
    baseline = evaluate_promotion(engine, output_dir=output)
    apply_promotion(engine, baseline, output_dir=output, snapshot_id="baseline-1")

    _install_hermes(engine, "hermes_v2", "\n# slightly clearer\n")
    _record_pair(engine, 8, hermes="hermes_v2", quality=0.22, cost=0.2, time_seconds=50)
    stalled = evaluate_promotion(engine, output_dir=output)
    assert stalled["status"] == "rejected"
    assert any("min_delta" in reason for reason in stalled["reasons"])

    _install_hermes(engine, "hermes_v3", "\n# regress success\n")
    for _ in range(4):
        engine.record_run_result(
            _run("hermes_v3", "laguna_v1", status="success", quality=0.95, cost=0.05, time_seconds=10)
        )
    for _ in range(4):
        engine.record_run_result(
            _run("hermes_v3", "laguna_v1", status="failure", quality=0.95, cost=0.05, time_seconds=10)
        )
    regressed = evaluate_promotion(engine, output_dir=output)
    assert regressed["status"] == "rejected"
    assert any("success_rate" in reason for reason in regressed["reasons"])

    _install_hermes(engine, "hermes_v4", "\n# clear improvement\n")
    _record_pair(
        engine,
        8,
        hermes="hermes_v4",
        quality=0.9,
        cost=0.1,
        time_seconds=20,
    )
    promoted = evaluate_promotion(engine, output_dir=output)
    assert promoted["status"] == "promote"
    apply_promotion(engine, promoted, output_dir=output, snapshot_id="promote-1")
    latest = json.loads((output / "LATEST.json").read_text(encoding="utf-8"))
    assert latest["snapshot_id"] == "promote-1"
    assert latest["hermes"]["variant_id"] == "hermes_v4"
    assert (output / "INDEX.md").exists()


def test_blocks_unresolved_challenger(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    output = engine.project_root / "evolution" / "promoted"
    _record_pair(engine, 8)
    baseline = evaluate_promotion(engine, output_dir=output)
    apply_promotion(engine, baseline, output_dir=output, snapshot_id="baseline-1")
    _install_hermes(engine, "hermes_v4", "\n# challenger\n")
    _record_pair(engine, 8, hermes="hermes_v4", quality=0.9, cost=0.1, time_seconds=20)
    engine.ab_manager.ab_tests.append(
        {
            "test_id": "ab_open",
            "status": "running",
            "variants": [
                {"variant_id": "hermes_v1", "role": "control"},
                {"variant_id": "hermes_v4", "role": "challenger"},
            ],
            "results": [],
        }
    )
    decision = evaluate_promotion(engine, output_dir=output)
    assert decision["status"] == "rejected"
    assert any("ab_inconclusive" in reason for reason in decision["reasons"])


def test_rejects_unreadable_latest(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    output = engine.project_root / "evolution" / "promoted"
    output.mkdir(parents=True)
    (output / "LATEST.json").write_text("{", encoding="utf-8")
    decision = evaluate_promotion(engine, output_dir=output)
    assert decision["status"] == "rejected"
    assert any("unreadable" in reason for reason in decision["reasons"])


def test_cli_apply_writes_snapshot(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _record_pair(engine, 8)
    code = promote_main(
        [
            "--root",
            str(engine.project_root),
            "--apply",
            "--snapshot-id",
            "cli-baseline",
        ]
    )
    assert code == 0
    manifest = (
        engine.project_root
        / "evolution"
        / "promoted"
        / "snapshots"
        / "cli-baseline"
        / "manifest.json"
    )
    assert json.loads(manifest.read_text(encoding="utf-8"))["status"] == "baseline"
