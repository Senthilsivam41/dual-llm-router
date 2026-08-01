"""Canonical filesystem paths for evolution state under .autoclaw/."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTOCLAW_ROOT = PROJECT_ROOT / ".autoclaw"

AGENTS_ROOT = AUTOCLAW_ROOT / "agents"
GENOMES_ROOT = AGENTS_ROOT / "genomes"
HERMES_GENOMES = GENOMES_ROOT / "hermes"
LAGUNA_GENOMES = GENOMES_ROOT / "laguna"
LINEAGE_PATH = GENOMES_ROOT / "lineage.json"
TRUST_SCORES_PATH = AGENTS_ROOT / "trust" / "trust_scores.json"
CAPABILITY_VECTORS_PATH = AGENTS_ROOT / "capabilities" / "capability_vectors.json"

EVALS_STATE_ROOT = AUTOCLAW_ROOT / "evals"
EVOLUTION_LOG_PATH = EVALS_STATE_ROOT / "evolution_log.json"
RUN_RESULTS_PATH = EVALS_STATE_ROOT / "run_results.json"
AB_TESTS_PATH = EVALS_STATE_ROOT / "ab_tests.json"
BEST_CONFIGS_PATH = EVALS_STATE_ROOT / "best_configs.json"
ALERTS_LOG_PATH = EVALS_STATE_ROOT / "alerts.jsonl"
TEMPLATES_ROOT = Path(__file__).resolve().parent / "templates"

ECONOMY_ROOT = AUTOCLAW_ROOT / "economy"
BUDGETS_PATH = ECONOMY_ROOT / "budgets.json"
LEDGER_PATH = ECONOMY_ROOT / "ledger.json"

PROMPTS_ROOT = PROJECT_ROOT / "prompts"
CONFIG_ROOT = PROJECT_ROOT / "config"
EVOLUTION_CONFIG_PATH = CONFIG_ROOT / "evolution.yaml"
AB_TESTS_CONFIG_PATH = CONFIG_ROOT / "ab_tests.yaml"
