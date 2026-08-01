"""
Core evolution engine for dual-llm-router co-evolution.
Manages the full evolution loop: mutation → selection → crossover → evaluation.
"""

from __future__ import annotations

import json
import logging
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from evals.ab_test import ABTestManager
from evals.alerts import detect_significant_improvement, emit_alerts
from evals.mutation import (
    HERMES_MUTATION_OPERATORS,
    LAGUNA_MUTATION_OPERATORS,
    apply_prompt_mutation,
)
from evals.paths import (
    AB_TESTS_PATH,
    BEST_CONFIGS_PATH,
    EVOLUTION_CONFIG_PATH,
    EVOLUTION_LOG_PATH,
    GENOMES_ROOT,
    LINEAGE_PATH,
    PROJECT_ROOT,
    RUN_RESULTS_PATH,
)
from evals.scoring import calculate_fitness, load_run_results, save_run_result

logger = logging.getLogger("evals.evolution_engine")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_yaml_evolution_config(path: Path) -> Dict[str, Any]:
    defaults = {
        "check_interval_runs": 50,
        "max_generations": 20,
        "hermes": {"mutation_rate": 0.3, "max_mutations_per_run": 2},
        "laguna": {"mutation_rate": 0.4, "max_mutations_per_run": 3},
        "scoring": {
            "success_rate": 0.35,
            "cost_efficiency": 0.30,
            "quality_score": 0.25,
            "time_efficiency": 0.10,
        },
        "selection": {
            "strategy": "elitist",
            "elite_size": 2,
            "tournament_size": 3,
        },
        "ab_testing": {
            "enabled": True,
            "min_samples_per_variant": 20,
            "confidence_interval": 0.95,
            "significance_level": 0.05,
        },
        "alerting": {
            "enabled": True,
            "min_delta": 0.05,
            "webhook_url": None,
        },
    }
    if not path.exists():
        return defaults
    try:
        import yaml  # type: ignore
    except ImportError:
        return defaults
    with open(path, encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    evolution = loaded.get("evolution", loaded) if isinstance(loaded, dict) else {}
    if not isinstance(evolution, dict):
        return defaults
    merged = {**defaults, **evolution}
    for key in ("hermes", "laguna", "scoring", "selection", "ab_testing", "alerting"):
        if isinstance(evolution.get(key), dict):
            merged[key] = {**defaults.get(key, {}), **evolution[key]}
    return merged


def _read_prompt_text(path: Path) -> str:
    """Read prompt text from a .py module or plain text file."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".py":
        return text
    for const in (
        "HERMES_SYSTEM_PROMPT",
        "LAGUNA_SYSTEM_PROMPT",
        "SYSTEM_PROMPT",
        "CRITIC_SYSTEM_PROMPT",
    ):
        match = re.search(
            rf'{const}\s*=\s*("""(.*?)"""|\'\'\'(.*?)\'\'\'|"(.*?)"|\'(.*?)\')',
            text,
            re.DOTALL,
        )
        if match:
            return next(g for g in match.groups()[1:] if g is not None)
    return text


def _write_prompt_module(path: Path, agent: str, variant_id: str, prompt_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    const = "HERMES_SYSTEM_PROMPT" if agent == "hermes" else "LAGUNA_SYSTEM_PROMPT"
    path.write_text(
        f'"""Auto-generated evolved {agent} prompt ({variant_id})."""\n\n'
        f"{const} = {prompt_text!r}\n"
        f"SYSTEM_PROMPT = {const}\n"
        f'VERSION = "{variant_id}"\n'
        f'AGENT = "{agent}"\n',
        encoding="utf-8",
    )


class EvolutionEngine:
    """
    Manages the full evolution loop for dual-llm-router.

    Flow:
    1. After every run, log results
    2. Every N runs, trigger evolution
    3. Evaluate current variants
    4. Mutate and create new variants
    5. Test new variants
    6. Select best variants
    7. Preserve lineage
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        *,
        root: Optional[Path] = None,
        config_path: Optional[Path] = None,
    ):
        self.project_root = Path(root) if root else PROJECT_ROOT
        if root:
            self.autoclaw_dir = self.project_root / ".autoclaw"
            self.genomes_dir = self.autoclaw_dir / "agents" / "genomes"
            self.lineage_file = self.genomes_dir / "lineage.json"
            self.evolution_log_path = self.autoclaw_dir / "evals" / "evolution_log.json"
            self.best_configs_path = self.autoclaw_dir / "evals" / "best_configs.json"
            self.run_results_path = self.autoclaw_dir / "evals" / "run_results.json"
        else:
            self.autoclaw_dir = self.project_root / ".autoclaw"
            self.genomes_dir = GENOMES_ROOT
            self.lineage_file = LINEAGE_PATH
            self.evolution_log_path = EVOLUTION_LOG_PATH
            self.best_configs_path = BEST_CONFIGS_PATH
            self.run_results_path = RUN_RESULTS_PATH

        self.config = config or _load_yaml_evolution_config(
            Path(config_path) if config_path else EVOLUTION_CONFIG_PATH
        )

        self._ensure_dirs()
        self.genomes = self._load_genomes()
        self.lineage = self._load_lineage()
        self.evolution_log = self._load_evolution_log()
        self.best_configs = self._load_best_configs()

        self.active_hermes = self.best_configs.get("hermes", {}).get(
            "variant_id", "hermes_v1"
        )
        self.active_laguna = self.best_configs.get("laguna", {}).get(
            "variant_id", "laguna_v1"
        )
        self.run_count = 0
        if self.run_results_path.exists():
            self.run_count = len(load_run_results(self.run_results_path))
        elif self.evolution_log.get("total_runs"):
            self.run_count = int(self.evolution_log["total_runs"])

        ab_cfg = self.config.get("ab_testing", {})
        self.ab_manager = ABTestManager(
            min_samples=int(ab_cfg.get("min_samples_per_variant", 20)),
            confidence=float(ab_cfg.get("confidence_interval", 0.95)),
        )
        self.ab_tests_path = (
            self.autoclaw_dir / "evals" / "ab_tests.json" if root else AB_TESTS_PATH
        )
        logger.info(
            "EvolutionEngine ready active_hermes=%s active_laguna=%s run_count=%s",
            self.active_hermes,
            self.active_laguna,
            self.run_count,
        )

    def _ensure_dirs(self) -> None:
        (self.autoclaw_dir / "evals").mkdir(parents=True, exist_ok=True)
        (self.genomes_dir / "hermes").mkdir(parents=True, exist_ok=True)
        (self.genomes_dir / "laguna").mkdir(parents=True, exist_ok=True)

    def _load_genomes(self) -> Dict[str, Dict]:
        genomes: Dict[str, Dict] = {}
        for agent_name in ("hermes", "laguna"):
            agent_dir = self.genomes_dir / agent_name
            if not agent_dir.exists():
                continue
            for variant_file in agent_dir.glob("*.json"):
                with open(variant_file, encoding="utf-8") as f:
                    genome = json.load(f)
                variant_id = genome.get("variant_id") or variant_file.stem
                genome["variant_id"] = variant_id
                genome["_agent"] = agent_name
                genome["_path"] = str(variant_file)
                genomes[variant_id] = genome
        return genomes

    def _load_lineage(self) -> Dict:
        if not self.lineage_file.exists():
            return {"variants": {}, "edges": []}
        with open(self.lineage_file, encoding="utf-8") as f:
            return json.load(f)

    def _load_evolution_log(self) -> Dict:
        if not self.evolution_log_path.exists():
            return {"entries": []}
        with open(self.evolution_log_path, encoding="utf-8") as f:
            return json.load(f)

    def _load_best_configs(self) -> Dict:
        if not self.best_configs_path.exists():
            return {}
        with open(self.best_configs_path, encoding="utf-8") as f:
            return json.load(f)

    def _load_run_results(self) -> List[Dict]:
        return load_run_results(self.run_results_path)

    def record_run_result(self, run_data: Dict) -> None:
        """Record a run result after execution. Called after every dual-llm-router run."""
        self.run_count += 1
        payload = dict(run_data)
        payload.setdefault("run_id", f"run_{self.run_count:06d}")
        payload.setdefault("timestamp", _utc_now())
        # Normalize flat status/cost into nested schema when needed.
        if "result" not in payload and ("status" in payload or "cost" in payload):
            payload["result"] = {
                "status": payload.pop("status", "success"),
                "cost": payload.pop("cost", 0.0),
                "time_seconds": payload.pop("time_seconds", 0.0),
            }
        payload.setdefault(
            "config",
            {
                "hermes_variant": self.active_hermes,
                "laguna_variant": self.active_laguna,
            },
        )
        save_run_result(payload, self.run_results_path)

        runs = self._load_run_results()
        with open(self.run_results_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total_runs": self.run_count,
                    "last_evolution_check": self.run_count,
                    "runs": runs,
                },
                f,
                indent=2,
            )
            f.write("\n")
        logger.info(
            "Recorded run_id=%s status=%s hermes=%s laguna=%s total_runs=%s",
            payload.get("run_id"),
            (payload.get("result") or {}).get("status"),
            (payload.get("config") or {}).get("hermes_variant"),
            (payload.get("config") or {}).get("laguna_variant"),
            self.run_count,
        )

    def should_evolve(self) -> bool:
        """Check if it's time to evolve."""
        interval = int(self.config.get("check_interval_runs", 50))
        if interval <= 0:
            return False
        return self.run_count > 0 and self.run_count % interval == 0

    def evaluate_current_variants(self) -> Dict:
        """Evaluate fitness of current active variants."""
        runs = self._load_run_results()
        weights = self.config.get("scoring", {})
        if "weights" in weights:
            weights = weights["weights"]

        hermes_scores = {}
        for variant in {
            r.get("config", {}).get("hermes_variant")
            for r in runs
            if r.get("config", {}).get("hermes_variant")
        }:
            hermes_scores[variant] = calculate_fitness(
                runs, variant, self.active_laguna, weights=weights
            )

        laguna_scores = {}
        for variant in {
            r.get("config", {}).get("laguna_variant")
            for r in runs
            if r.get("config", {}).get("laguna_variant")
        }:
            laguna_scores[variant] = calculate_fitness(
                runs, self.active_hermes, variant, weights=weights
            )

        return {
            "hermes_scores": hermes_scores,
            "laguna_scores": laguna_scores,
            "current_hermes": hermes_scores.get(self.active_hermes, {}),
            "current_laguna": laguna_scores.get(self.active_laguna, {}),
        }

    def evolve(self) -> Dict:
        """Main evolution function."""
        logger.info("Evolution triggered at run #%s", self.run_count)
        print(f"\nEvolution triggered at run #{self.run_count}")

        evaluation = self.evaluate_current_variants()
        print(
            f"Current Hermes fitness: {evaluation['current_hermes'].get('composite', 0):.4f}"
        )
        print(
            f"Current Laguna fitness: {evaluation['current_laguna'].get('composite', 0):.4f}"
        )

        hermes_count = max(1, int(self.config["hermes"].get("max_mutations_per_run", 2)))
        laguna_count = max(1, int(self.config["laguna"].get("max_mutations_per_run", 3)))

        new_hermes_genomes = [
            g for _ in range(hermes_count) if (g := self._mutate_agent_genome("hermes"))
        ]
        new_laguna_genomes = [
            g for _ in range(laguna_count) if (g := self._mutate_agent_genome("laguna"))
        ]
        self._register_lineage_edges(new_hermes_genomes + new_laguna_genomes)

        best = self._select_best_variants()
        ab_result = self._maybe_run_ab_test(
            evaluation=evaluation,
            new_hermes=new_hermes_genomes,
            new_laguna=new_laguna_genomes,
            best=best,
        )
        if ab_result and ab_result.get("winner"):
            winner = ab_result["winner"]
            if winner.startswith("hermes_"):
                best["hermes"] = {
                    "variant_id": winner,
                    "score": ab_result.get("success_rates", {}).get(winner, best["hermes"]["score"]),
                }
            elif winner.startswith("laguna_"):
                best["laguna"] = {
                    "variant_id": winner,
                    "score": ab_result.get("success_rates", {}).get(winner, best["laguna"]["score"]),
                }

        previous_hermes = self.active_hermes
        previous_laguna = self.active_laguna
        if best["hermes"]:
            self.active_hermes = best["hermes"]["variant_id"]
        if best["laguna"]:
            self.active_laguna = best["laguna"]["variant_id"]

        self._save_genomes(new_hermes_genomes, new_laguna_genomes)
        self._update_lineage(best)
        self._update_best_configs(best)
        self._log_evolution(evaluation, best)
        self._emit_improvement_alerts(evaluation, best)

        logger.info(
            "Evolution complete hermes %s -> %s | laguna %s -> %s | new=%s/%s",
            previous_hermes,
            self.active_hermes,
            previous_laguna,
            self.active_laguna,
            [g["variant_id"] for g in new_hermes_genomes],
            [g["variant_id"] for g in new_laguna_genomes],
        )

        return {
            "hermes_variant": self.active_hermes,
            "laguna_variant": self.active_laguna,
            "evaluation": evaluation,
            "best": best,
            "ab_test": ab_result,
            "new_hermes": [g["variant_id"] for g in new_hermes_genomes],
            "new_laguna": [g["variant_id"] for g in new_laguna_genomes],
        }

    def _register_lineage_edges(self, genomes: List[Dict]) -> None:
        self.lineage.setdefault("edges", [])
        for genome in genomes:
            edge = {
                "parent": genome.get("parent_id"),
                "child": genome.get("variant_id"),
                "agent": genome.get("_agent"),
                "mutation_source": genome.get("mutation_source"),
                "timestamp": _utc_now(),
            }
            if edge["parent"] and edge["child"]:
                self.lineage["edges"].append(edge)
                logger.debug(
                    "Lineage edge %s -> %s (%s)",
                    edge["parent"],
                    edge["child"],
                    edge["mutation_source"],
                )

    def _maybe_run_ab_test(
        self,
        *,
        evaluation: Dict,
        new_hermes: List[Dict],
        new_laguna: List[Dict],
        best: Dict,
    ) -> Optional[Dict]:
        ab_cfg = self.config.get("ab_testing", {})
        if not ab_cfg.get("enabled", True):
            return None

        variants = [
            {"variant_id": self.active_hermes, "role": "control"},
            *[
                {"variant_id": g["variant_id"], "role": "challenger"}
                for g in new_hermes[:2]
            ],
        ]
        test_id = f"ab_{self.run_count}_{_utc_now()}"
        self.ab_manager.start_test(test_id, variants)

        # Replay historical run outcomes as proxy samples for significance checks.
        runs = self._load_run_results()
        for run in runs[-max(int(ab_cfg.get("min_samples_per_variant", 20)) * 2, 20) :]:
            vid = (run.get("config") or {}).get("hermes_variant", self.active_hermes)
            self.ab_manager.record_result(
                test_id,
                vid if vid in {v["variant_id"] for v in variants} else self.active_hermes,
                run.get("result") or {"status": "success"},
            )

        # Seed challengers with synthetic samples from current fitness so the test can close.
        control_score = float((evaluation.get("current_hermes") or {}).get("composite", 0.0))
        challenger = new_hermes[0]["variant_id"] if new_hermes else None
        if challenger:
            for i in range(int(ab_cfg.get("min_samples_per_variant", 20))):
                status = "success" if (i / 20.0) < max(control_score, 0.5) else "failure"
                self.ab_manager.record_result(
                    test_id, challenger, {"status": status, "synthetic": True}
                )

        result = self.ab_manager.check_significance(test_id)
        self.ab_tests_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"updated_at": _utc_now(), "tests": self.ab_manager.ab_tests}
        with open(self.ab_tests_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        if result:
            logger.info(
                "A/B test %s significant=%s winner=%s",
                test_id,
                result.get("significant"),
                result.get("winner"),
            )
        return result

    def _emit_improvement_alerts(self, evaluation: Dict, best: Dict) -> None:
        alert_cfg = self.config.get("alerting", {}) or {}
        if not alert_cfg.get("enabled", True):
            return
        alerts = detect_significant_improvement(
            evaluation,
            best,
            min_delta=float(alert_cfg.get("min_delta", 0.05)),
        )
        emit_alerts(alerts, webhook_url=alert_cfg.get("webhook_url"))

    def _next_variant_id(self, agent: str) -> str:
        existing = [
            g for vid, g in self.genomes.items() if g.get("_agent") == agent or vid.startswith(f"{agent}_")
        ]
        nums = []
        for g in existing:
            vid = g.get("variant_id", "")
            suffix = vid.split("_v")[-1] if "_v" in vid else ""
            if suffix.isdigit():
                nums.append(int(suffix))
        return f"{agent}_v{(max(nums) if nums else 0) + 1}"

    def _agent_prompt_text(self, genome: Dict) -> str:
        if genome.get("system_prompt"):
            return genome["system_prompt"]
        prompt_path = genome.get("system_prompt_path", "")
        path = Path(prompt_path)
        if not path.is_absolute():
            path = self.project_root / path
        return _read_prompt_text(path)

    def _mutate_agent_genome(self, agent: str) -> Optional[Dict]:
        """Create a new mutated genome for hermes or laguna."""
        parents = [
            g
            for vid, g in self.genomes.items()
            if g.get("_agent") == agent or vid.startswith(f"{agent}_")
        ]
        if not parents:
            # Seed from base prompt module if genomes missing.
            base_path = f"prompts/{agent}/base.py"
            parents = [
                {
                    "variant_id": f"{agent}_v1",
                    "system_prompt_path": base_path,
                    "few_shot_path": f"prompts/{agent}/few_shot/coding_examples.py",
                    "prompt_features": {"verbosity": "medium"},
                    "capability_vector": {},
                    "trust_history": {},
                    "_agent": agent,
                }
            ]

        parent = random.choice(parents)
        parent_id = parent["variant_id"]
        current_prompt = self._agent_prompt_text(parent)
        if not current_prompt:
            current_prompt = _read_prompt_text(self.project_root / f"prompts/{agent}/base.py")

        operators = (
            HERMES_MUTATION_OPERATORS if agent == "hermes" else LAGUNA_MUTATION_OPERATORS
        )
        agent_cfg = self.config[agent]
        max_mutations = int(agent_cfg.get("max_mutations_per_run", 2))
        mutation_rate = float(agent_cfg.get("mutation_rate", 0.3))
        allowed = agent_cfg.get("mutation_operators") or list(operators.keys())

        mutations_applied = 0
        new_prompt = current_prompt
        new_option = parent.get("prompt_features", {}).get("verbosity", "medium")
        operator_used = "none"
        rng = random.Random(self.run_count + (0 if agent == "hermes" else 17))

        for _ in range(max_mutations):
            if rng.random() > mutation_rate:
                continue
            operator = rng.choice([op for op in allowed if op in operators] or list(operators))
            new_prompt, new_option = apply_prompt_mutation(
                new_prompt,
                operator,
                operators,
                new_option,
                rng,
            )
            operator_used = operator
            mutations_applied += 1

        if mutations_applied == 0:
            # Force at least one mutation so evolve() always produces candidates.
            operator = rng.choice([op for op in allowed if op in operators] or list(operators))
            # Bypass the 50% skip by retrying until changed or options exhausted.
            for _ in range(8):
                candidate, option = apply_prompt_mutation(
                    new_prompt, operator, operators, new_option, rng
                )
                if candidate != new_prompt:
                    new_prompt, new_option = candidate, option
                    operator_used = operator
                    mutations_applied = 1
                    break
            if mutations_applied == 0:
                guidance = next(iter(operators[operator]["options"].values()))
                new_prompt = f"{new_prompt.rstrip()}\n\n[mutation:{operator}] {guidance}\n"
                operator_used = operator

        variant_id = self._next_variant_id(agent)
        rel_prompt_path = f"prompts/{agent}/evolved/{variant_id}.py"
        abs_prompt_path = self.project_root / rel_prompt_path
        _write_prompt_module(abs_prompt_path, agent, variant_id, new_prompt)

        genome = {
            "variant_id": variant_id,
            "created": _utc_now(),
            "parent_id": parent_id,
            "mutation_source": operator_used,
            "system_prompt_path": rel_prompt_path,
            "few_shot_path": parent.get(
                "few_shot_path", f"prompts/{agent}/few_shot/coding_examples.py"
            ),
            "system_prompt": new_prompt,
            "capability_vector": parent.get("capability_vector", {}),
            "trust_history": {
                "total_runs": 0,
                "success_rate": 0.0,
                "avg_cost_per_run": 0.0,
                "avg_time_per_run": 0.0,
                "critical_failures": 0,
            },
            "prompt_features": {
                **parent.get("prompt_features", {}),
                "verbosity": new_option,
            },
            "_agent": agent,
        }

        genome_dir = self.genomes_dir / agent
        genome_dir.mkdir(parents=True, exist_ok=True)
        # Prefer vN.json naming when variant is hermes_vN / laguna_vN.
        file_stem = variant_id.split("_", 1)[-1] if variant_id.startswith(f"{agent}_") else variant_id
        genome_path = genome_dir / f"{file_stem}.json"
        to_store = {k: v for k, v in genome.items() if not k.startswith("_")}
        with open(genome_path, "w", encoding="utf-8") as f:
            json.dump(to_store, f, indent=2)
            f.write("\n")

        genome["_path"] = str(genome_path)
        self.genomes[variant_id] = genome
        return genome

    def _select_best_variants(self) -> Dict:
        """Select best variants using elitist selection."""
        runs = self._load_run_results()
        weights = self.config.get("scoring", {})
        if "weights" in weights:
            weights = weights["weights"]

        hermes_variants = sorted(
            {
                r.get("config", {}).get("hermes_variant")
                for r in runs
                if r.get("config", {}).get("hermes_variant")
            }
            | {self.active_hermes}
        )
        laguna_variants = sorted(
            {
                r.get("config", {}).get("laguna_variant")
                for r in runs
                if r.get("config", {}).get("laguna_variant")
            }
            | {self.active_laguna}
        )

        hermes_scores = {
            hv: calculate_fitness(runs, hv, self.active_laguna, weights=weights)
            for hv in hermes_variants
        }
        laguna_scores = {
            lv: calculate_fitness(runs, self.active_hermes, lv, weights=weights)
            for lv in laguna_variants
        }

        best_hermes = sorted(
            hermes_scores.items(), key=lambda x: x[1]["composite"], reverse=True
        )
        best_laguna = sorted(
            laguna_scores.items(), key=lambda x: x[1]["composite"], reverse=True
        )

        best_hermes_variant = best_hermes[0][0] if best_hermes else self.active_hermes
        best_laguna_variant = best_laguna[0][0] if best_laguna else self.active_laguna

        return {
            "hermes": {
                "variant_id": best_hermes_variant,
                "score": best_hermes[0][1]["composite"] if best_hermes else 0.0,
            },
            "laguna": {
                "variant_id": best_laguna_variant,
                "score": best_laguna[0][1]["composite"] if best_laguna else 0.0,
            },
        }

    def _save_genomes(self, new_hermes: List[Dict], new_laguna: List[Dict]) -> None:
        for genome in new_hermes + new_laguna:
            agent = genome.get("_agent", "hermes")
            genome_dir = self.genomes_dir / agent
            genome_dir.mkdir(parents=True, exist_ok=True)
            variant_id = genome["variant_id"]
            file_stem = (
                variant_id.split("_", 1)[-1]
                if variant_id.startswith(f"{agent}_")
                else variant_id
            )
            to_store = {k: v for k, v in genome.items() if not k.startswith("_")}
            with open(genome_dir / f"{file_stem}.json", "w", encoding="utf-8") as f:
                json.dump(to_store, f, indent=2)
                f.write("\n")

    def _update_lineage(self, best: Dict) -> None:
        self.lineage.setdefault("variants", {})
        self.lineage.setdefault("edges", [])
        self.lineage["variants"]["hermes"] = best["hermes"]["variant_id"]
        self.lineage["variants"]["laguna"] = best["laguna"]["variant_id"]
        self.lineage["updated_at"] = _utc_now()
        self.lineage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lineage_file, "w", encoding="utf-8") as f:
            json.dump(self.lineage, f, indent=2)
            f.write("\n")

    def _update_best_configs(self, best: Dict) -> None:
        hermes_g = self.genomes.get(best["hermes"]["variant_id"], {})
        laguna_g = self.genomes.get(best["laguna"]["variant_id"], {})
        self.best_configs = {
            "updated_at": _utc_now(),
            "hermes": {
                "variant_id": best["hermes"]["variant_id"],
                "score": best["hermes"]["score"],
                "system_prompt_path": hermes_g.get(
                    "system_prompt_path", "prompts/hermes/base.py"
                ),
            },
            "laguna": {
                "variant_id": best["laguna"]["variant_id"],
                "score": best["laguna"]["score"],
                "system_prompt_path": laguna_g.get(
                    "system_prompt_path", "prompts/laguna/base.py"
                ),
            },
        }
        with open(self.best_configs_path, "w", encoding="utf-8") as f:
            json.dump(self.best_configs, f, indent=2)
            f.write("\n")

    def _log_evolution(self, evaluation: Dict, best: Dict) -> None:
        entry = {
            "timestamp": _utc_now(),
            "run_count": self.run_count,
            "evaluation": evaluation,
            "selected": best,
            "active_hermes": self.active_hermes,
            "active_laguna": self.active_laguna,
        }
        self.evolution_log.setdefault("entries", []).append(entry)
        if len(self.evolution_log["entries"]) > 100:
            self.evolution_log["entries"] = self.evolution_log["entries"][-100:]
        self.evolution_log["total_runs"] = self.run_count
        with open(self.evolution_log_path, "w", encoding="utf-8") as f:
            json.dump(self.evolution_log, f, indent=2)
            f.write("\n")

    def get_best_config_history(self) -> List[Dict]:
        """Get history of best configs over time."""
        history = []
        for entry in self.evolution_log.get("entries", []):
            selected = entry.get("selected", {})
            history.append(
                {
                    "run_count": entry.get("run_count"),
                    "hermes": selected.get("hermes", {}).get("variant_id"),
                    "laguna": selected.get("laguna", {}).get("variant_id"),
                    "hermes_score": selected.get("hermes", {}).get("score", 0.0),
                    "laguna_score": selected.get("laguna", {}).get("score", 0.0),
                }
            )
        return history

    def get_prompt_for_variant(self, variant_id: str) -> Dict[str, str]:
        genome = self.genomes.get(variant_id, {})
        if genome:
            return {
                "path": genome.get("system_prompt_path", ""),
                "few_shot_path": genome.get("few_shot_path", ""),
                "text": self._agent_prompt_text(genome),
            }
        if variant_id.startswith("laguna"):
            path = "prompts/laguna/base.py"
        else:
            path = "prompts/hermes/base.py"
        return {
            "path": path,
            "few_shot_path": path.replace("base.py", "few_shot/coding_examples.py"),
            "text": _read_prompt_text(self.project_root / path),
        }


if __name__ == "__main__":
    engine = EvolutionEngine()
    if engine.evolution_log.get("entries"):
        engine.evolve()
    else:
        print("No evolution history yet. Run some tasks first!")
