#!/usr/bin/env python3
"""Reset evolution state under .autoclaw/ to base configs."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.paths import (
    AB_TESTS_PATH,
    BEST_CONFIGS_PATH,
    BUDGETS_PATH,
    CAPABILITY_VECTORS_PATH,
    ECONOMY_ROOT,
    EVALS_STATE_ROOT,
    EVOLUTION_LOG_PATH,
    GENOMES_ROOT,
    HERMES_GENOMES,
    LAGUNA_GENOMES,
    LEDGER_PATH,
    LINEAGE_PATH,
    RUN_RESULTS_PATH,
    TEMPLATES_ROOT,
    TRUST_SCORES_PATH,
)
from prompts.hermes.base import HERMES_SYSTEM_PROMPT
from prompts.laguna.base import LAGUNA_SYSTEM_PROMPT


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _genome(agent: str, prompt: str) -> dict:
    template_path = TEMPLATES_ROOT / f"{agent}_v1.json"
    if template_path.exists():
        genome = json.loads(template_path.read_text(encoding="utf-8"))
    else:
        genome = {
            "variant_id": f"{agent}_v1",
            "parent_id": None,
            "mutation_source": "base",
            "system_prompt_path": f"prompts/{agent}/base.py",
            "few_shot_path": f"prompts/{agent}/few_shot/coding_examples.py",
            "capability_vector": {},
            "trust_history": {
                "total_runs": 0,
                "success_rate": 0.0,
                "avg_cost_per_run": 0.0,
                "avg_time_per_run": 0.0,
                "critical_failures": 0,
            },
            "prompt_features": {"verbosity": "medium"},
        }
    genome["created"] = _utc_now()
    genome["system_prompt"] = prompt
    genome["variant_id"] = f"{agent}_v1"
    return genome


def reset_state(*, wipe_evolved_prompts: bool = True) -> None:
    for path in (
        EVOLUTION_LOG_PATH,
        RUN_RESULTS_PATH,
        AB_TESTS_PATH,
        BEST_CONFIGS_PATH,
        LINEAGE_PATH,
        TRUST_SCORES_PATH,
        CAPABILITY_VECTORS_PATH,
        BUDGETS_PATH,
        LEDGER_PATH,
    ):
        if path.exists():
            path.unlink()

    if HERMES_GENOMES.exists():
        shutil.rmtree(HERMES_GENOMES)
    if LAGUNA_GENOMES.exists():
        shutil.rmtree(LAGUNA_GENOMES)

    HERMES_GENOMES.mkdir(parents=True, exist_ok=True)
    LAGUNA_GENOMES.mkdir(parents=True, exist_ok=True)
    EVALS_STATE_ROOT.mkdir(parents=True, exist_ok=True)
    ECONOMY_ROOT.mkdir(parents=True, exist_ok=True)

    hermes_v1 = _genome("hermes", HERMES_SYSTEM_PROMPT)
    laguna_v1 = _genome("laguna", LAGUNA_SYSTEM_PROMPT)
    _write(HERMES_GENOMES / "v1.json", hermes_v1)
    _write(LAGUNA_GENOMES / "v1.json", laguna_v1)

    _write(
        LINEAGE_PATH,
        {
            "updated_at": _utc_now(),
            "variants": {
                "hermes": "hermes_v1",
                "laguna": "laguna_v1",
            },
            "edges": [],
        },
    )
    _write(
        TRUST_SCORES_PATH,
        {
            "updated_at": _utc_now(),
            "scores": {"hermes_v1": 1.0, "laguna_v1": 1.0},
        },
    )
    _write(
        CAPABILITY_VECTORS_PATH,
        {
            "updated_at": _utc_now(),
            "vectors": {
                "hermes_v1": hermes_v1["capability_vector"],
                "laguna_v1": laguna_v1["capability_vector"],
            },
        },
    )
    _write(EVOLUTION_LOG_PATH, {"entries": [], "total_runs": 0})
    _write(RUN_RESULTS_PATH, {"total_runs": 0, "last_evolution_check": 0, "runs": []})
    _write(AB_TESTS_PATH, {"updated_at": _utc_now(), "tests": []})
    _write(
        BEST_CONFIGS_PATH,
        {
            "updated_at": _utc_now(),
            "hermes": {
                "variant_id": "hermes_v1",
                "score": 0.0,
                "system_prompt_path": "prompts/hermes/base.py",
            },
            "laguna": {
                "variant_id": "laguna_v1",
                "score": 0.0,
                "system_prompt_path": "prompts/laguna/base.py",
            },
        },
    )
    _write(
        BUDGETS_PATH,
        {
            "updated_at": _utc_now(),
            "daily_budget_usd": 5.0,
            "per_run_budget_usd": 0.25,
            "currency": "USD",
        },
    )
    _write(LEDGER_PATH, {"updated_at": _utc_now(), "entries": []})

    if wipe_evolved_prompts:
        for agent in ("hermes", "laguna"):
            for evolved in (
                PROJECT_ROOT / "prompts" / agent / "evolved",
                PROJECT_ROOT / "prompts" / agent / "few_shot" / "evolved",
            ):
                if evolved.exists():
                    for child in evolved.iterdir():
                        if child.name == ".gitkeep":
                            continue
                        if child.is_file():
                            child.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset .autoclaw evolution state to base configs")
    parser.add_argument(
        "--keep-evolved-prompts",
        action="store_true",
        help="Do not delete prompts/*/evolved generated files",
    )
    args = parser.parse_args()
    reset_state(wipe_evolved_prompts=not args.keep_evolved_prompts)
    print("Reset complete.")
    print(f"  genomes: {GENOMES_ROOT}")
    print(f"  evolution_log: {EVOLUTION_LOG_PATH}")
    print(f"  best_configs: {BEST_CONFIGS_PATH}")


if __name__ == "__main__":
    main()
