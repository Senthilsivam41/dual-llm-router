#!/usr/bin/env python3
"""Prompt evolution loop for Dual-LLM Router planner prompts.

After each pipeline run, records quality/cost/pass-rate/latency metrics,
keeps a history of (prompt_variant, result) pairs, and periodically mutates
the planner system prompt, A/B tests candidates, and promotes the winner.

All state is persisted to evals/evolution_log.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import statistics
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.agents.planner import PLANNER_SYSTEM_PROMPT
from src.orchestrator import DualLLMRouterOrchestrator

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_PATH = PROJECT_ROOT / "evals" / "evolution_log.json"
DEFAULT_EVOLUTION_INTERVAL = 5
DEFAULT_NUM_MUTANTS = 3
DEFAULT_AB_TRIALS = 1

# Heuristic feature detectors for planner prompt text.
PROMPT_FEATURE_PATTERNS: Dict[str, re.Pattern[str]] = {
    "requires_raw_json": re.compile(r"raw\s+json|respond with.*json", re.I),
    "forbids_markdown": re.compile(r"do not include markdown|no markdown", re.I),
    "asks_measurable_criteria": re.compile(r"measurable|verifiable|testable", re.I),
    "asks_target_files": re.compile(r"target_files|target files", re.I),
    "asks_step_plan": re.compile(r"step_by_step|step-by-step|ordered list", re.I),
    "mentions_acceptance": re.compile(r"acceptance.?criteria", re.I),
    "asks_concise": re.compile(r"concise|brief|minimal", re.I),
    "asks_explicit_paths": re.compile(r"absolute|relative path|file path", re.I),
    "asks_shell_verify": re.compile(r"shell|pytest|unit test|verify", re.I),
    "role_hermes": re.compile(r"hermes", re.I),
}

MUTATION_SNIPPETS = [
    "Prefer measurable, binary acceptance criteria that can be checked with shell commands or file inspection.",
    "Always include concrete target_files with relative paths under the workspace root.",
    "Keep step_by_step_plan short (3-7 steps) and action-oriented for the executor.",
    "Do not invent files outside the user request; only list files that must be created or modified.",
    "When criteria involve behavior, phrase them so they can be verified with pytest or a one-line python check.",
    "Put constraints and edge cases in notes rather than burying them inside the goal.",
    "Ensure the goal is a single sentence summarizing the user request without restating acceptance criteria.",
    "Output must be a single JSON object with keys exactly matching the TaskSpec schema.",
]


@dataclass
class RunResult:
    run_id: str
    timestamp: str
    variant_id: str
    user_prompt: str
    status: str
    task_spec_quality_score: float
    executor_cost_usd: float
    acceptance_criteria_pass_rate: float
    time_to_complete_seconds: float
    fitness: float
    task_spec: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class PromptVariant:
    variant_id: str
    prompt: str
    features: Dict[str, bool] = field(default_factory=dict)
    parent_id: Optional[str] = None
    mutation: Optional[str] = None
    created_at: str = field(default_factory=lambda: _utc_now())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _variant_id(prompt: str, prefix: str = "v") -> str:
    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def extract_prompt_features(prompt: str) -> Dict[str, bool]:
    return {name: bool(pattern.search(prompt)) for name, pattern in PROMPT_FEATURE_PATTERNS.items()}


def score_task_spec_quality(task_spec: Optional[Dict[str, Any]]) -> float:
    """Heuristic quality score in [0, 1] for a planner TaskSpec."""
    if not task_spec:
        return 0.0

    score = 0.0
    goal = (task_spec.get("goal") or "").strip()
    if goal:
        score += 0.2
        if 20 <= len(goal) <= 200:
            score += 0.05

    target_files = task_spec.get("target_files") or []
    if isinstance(target_files, list) and target_files:
        score += 0.15
        if all(isinstance(f, str) and f.strip() and not f.startswith("/") for f in target_files):
            score += 0.05

    criteria = task_spec.get("acceptance_criteria") or []
    if isinstance(criteria, list) and criteria:
        score += 0.2
        measurable_hits = sum(
            1
            for c in criteria
            if isinstance(c, str)
            and re.search(r"exist|pass|return|equal|contain|match|pytest|error|output", c, re.I)
        )
        score += min(0.15, 0.05 * measurable_hits)

    plan = task_spec.get("step_by_step_plan") or []
    if isinstance(plan, list) and plan:
        score += 0.1
        if 2 <= len(plan) <= 8:
            score += 0.05

    notes = task_spec.get("notes")
    if isinstance(notes, str) and notes.strip():
        score += 0.05

    return round(min(1.0, score), 4)


def executor_cost_from_metrics(metrics: Optional[Dict[str, Any]]) -> float:
    if not metrics:
        return 0.0
    total = 0.0
    for entry in metrics.get("breakdown") or []:
        node = str(entry.get("node", "")).lower()
        if "executor" in node:
            total += float(entry.get("cost_estimate_usd") or 0.0)
    if total == 0.0:
        # Fall back to total pipeline cost if node labels differ.
        total = float(metrics.get("total_cost_usd") or 0.0)
    return round(total, 6)


def acceptance_pass_rate(result: Dict[str, Any]) -> float:
    executor_result = result.get("executor_result") or {}
    report = executor_result.get("verification_report") or {}
    details = report.get("details") or []
    if details:
        passed = sum(1 for d in details if d.get("passed"))
        return round(passed / len(details), 4)

    criteria = (result.get("task_spec") or {}).get("acceptance_criteria") or []
    if not criteria:
        return 0.0 if result.get("status") != "completed" else 1.0
    # No per-criterion details available: binary success signal.
    if report.get("criteria_passed") is True or executor_result.get("success") is True:
        return 1.0
    return 0.0


def compute_fitness(
    quality: float,
    pass_rate: float,
    executor_cost: float,
    time_to_complete: float,
) -> float:
    """Higher is better. Soft-penalize cost and latency."""
    cost_penalty = min(0.4, executor_cost * 20.0)  # $0.02 ~ full soft penalty
    time_penalty = min(0.3, max(0.0, time_to_complete - 1.0) / 60.0)
    return round((0.45 * quality) + (0.45 * pass_rate) - cost_penalty - time_penalty, 4)


def mutate_prompt(base_prompt: str, rng: random.Random, n: int = 3) -> List[Tuple[str, str]]:
    """Return up to n (mutation_description, mutated_prompt) pairs."""
    unused = [s for s in MUTATION_SNIPPETS if s not in base_prompt]
    rng.shuffle(unused)
    mutants: List[Tuple[str, str]] = []

    strategies = [
        ("append_guidance", lambda snippet: base_prompt.rstrip() + "\n\nAdditional guidance:\n- " + snippet),
        (
            "strengthen_json",
            lambda snippet: base_prompt.replace(
                "Respond with raw JSON object or JSON inside standard markdown json block.",
                "Respond with a single raw JSON object only. Never wrap it in markdown fences.",
            )
            + f"\n\n{snippet}",
        ),
        (
            "prepend_priority",
            lambda snippet: f"Priority: {snippet}\n\n{base_prompt}",
        ),
    ]

    for i in range(min(n, max(1, len(unused) or 1))):
        snippet = unused[i] if unused else "Be explicit and verifiable in every TaskSpec field."
        name, builder = strategies[i % len(strategies)]
        mutated = builder(snippet)
        if mutated.strip() == base_prompt.strip():
            mutated = base_prompt.rstrip() + f"\n\n- {snippet}"
        mutants.append((f"{name}: {snippet}", mutated))
    return mutants


def identify_best_prompt_features(
    history: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Simple feature analysis: average fitness when a feature is present vs absent."""
    feature_stats: Dict[str, Dict[str, List[float]]] = {}
    for item in history:
        features = item.get("features") or {}
        results = item.get("results") or []
        if not results:
            continue
        avg_fitness = statistics.mean(float(r.get("fitness", 0.0)) for r in results)
        for feature, present in features.items():
            bucket = feature_stats.setdefault(feature, {"present": [], "absent": []})
            bucket["present" if present else "absent"].append(avg_fitness)

    rankings: List[Dict[str, Any]] = []
    for feature, buckets in feature_stats.items():
        present = buckets["present"]
        absent = buckets["absent"]
        if not present:
            continue
        present_mean = statistics.mean(present)
        absent_mean = statistics.mean(absent) if absent else 0.0
        rankings.append(
            {
                "feature": feature,
                "present_mean_fitness": round(present_mean, 4),
                "absent_mean_fitness": round(absent_mean, 4),
                "lift": round(present_mean - absent_mean, 4),
                "present_n": len(present),
                "absent_n": len(absent),
            }
        )

    rankings.sort(key=lambda x: x["lift"], reverse=True)
    return {
        "best_features": [r for r in rankings if r["lift"] > 0][:5],
        "all_features": rankings,
    }


class EvolutionEngine:
    def __init__(
        self,
        log_path: Path = DEFAULT_LOG_PATH,
        evolution_interval: int = DEFAULT_EVOLUTION_INTERVAL,
        num_mutants: int = DEFAULT_NUM_MUTANTS,
        ab_trials: int = DEFAULT_AB_TRIALS,
        workspace_root: Optional[str] = None,
        seed: Optional[int] = None,
    ):
        self.log_path = Path(log_path)
        self.evolution_interval = max(1, evolution_interval)
        self.num_mutants = max(2, min(3, num_mutants))
        self.ab_trials = max(1, ab_trials)
        self.workspace_root = workspace_root or str(PROJECT_ROOT / "workspace" / "evolution")
        self.rng = random.Random(seed)
        self.state = self._load_or_init()

    def _load_or_init(self) -> Dict[str, Any]:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if self.log_path.exists():
            with open(self.log_path, encoding="utf-8") as f:
                return json.load(f)

        baseline = PromptVariant(
            variant_id=_variant_id(PLANNER_SYSTEM_PROMPT, prefix="baseline"),
            prompt=PLANNER_SYSTEM_PROMPT,
            features=extract_prompt_features(PLANNER_SYSTEM_PROMPT),
            mutation="initial_baseline",
        )
        state = {
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "evolution_interval": self.evolution_interval,
            "runs_since_evolution": 0,
            "current_default_variant_id": baseline.variant_id,
            "current_default_prompt": baseline.prompt,
            "runs": [],
            "history": [
                {
                    "variant_id": baseline.variant_id,
                    "prompt": baseline.prompt,
                    "features": baseline.features,
                    "parent_id": None,
                    "mutation": baseline.mutation,
                    "created_at": baseline.created_at,
                    "results": [],
                    "aggregate_fitness": None,
                }
            ],
            "ab_tests": [],
            "events": [
                {
                    "type": "init",
                    "timestamp": _utc_now(),
                    "variant_id": baseline.variant_id,
                    "message": "Initialized evolution log with baseline planner prompt",
                }
            ],
        }
        self._save(state)
        return state

    def _save(self, state: Optional[Dict[str, Any]] = None) -> None:
        payload = state if state is not None else self.state
        payload["updated_at"] = _utc_now()
        payload["evolution_interval"] = self.evolution_interval
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_name = tempfile.mkstemp(
            prefix="evolution_log_",
            suffix=".json",
            dir=str(self.log_path.parent),
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_name, self.log_path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        self.state = payload

    def _history_entry(self, variant_id: str) -> Optional[Dict[str, Any]]:
        for entry in self.state["history"]:
            if entry["variant_id"] == variant_id:
                return entry
        return None

    def _ensure_variant(self, variant: PromptVariant) -> Dict[str, Any]:
        existing = self._history_entry(variant.variant_id)
        if existing:
            return existing
        entry = {
            "variant_id": variant.variant_id,
            "prompt": variant.prompt,
            "features": variant.features,
            "parent_id": variant.parent_id,
            "mutation": variant.mutation,
            "created_at": variant.created_at,
            "results": [],
            "aggregate_fitness": None,
        }
        self.state["history"].append(entry)
        return entry

    def current_prompt(self) -> str:
        return self.state["current_default_prompt"]

    def current_variant_id(self) -> str:
        return self.state["current_default_variant_id"]

    def run_once(
        self,
        user_prompt: str,
        *,
        prompt_variant: Optional[str] = None,
        variant_id: Optional[str] = None,
        execute_tools: bool = True,
        workspace_root: Optional[str] = None,
        record: bool = True,
        count_toward_evolution: bool = True,
        trigger_evolution: bool = True,
    ) -> RunResult:
        prompt_text = prompt_variant or self.current_prompt()
        if variant_id:
            vid = variant_id
        elif prompt_variant is None or prompt_text == self.current_prompt():
            # Keep continuity with the promoted default variant id.
            vid = self.current_variant_id()
        else:
            vid = _variant_id(prompt_text)
        variant = PromptVariant(
            variant_id=vid,
            prompt=prompt_text,
            features=extract_prompt_features(prompt_text),
        )
        self._ensure_variant(variant)

        run_workspace = workspace_root or os.path.join(
            self.workspace_root, vid, uuid.uuid4().hex[:8]
        )
        os.makedirs(run_workspace, exist_ok=True)

        started = time.time()
        orchestrator = DualLLMRouterOrchestrator(
            workspace_root=run_workspace,
            planner_system_prompt=prompt_text,
        )
        try:
            pipeline = orchestrator.run(user_prompt, execute_tools=execute_tools)
        except Exception as exc:  # noqa: BLE001 - evolution must keep logging failures
            pipeline = {
                "status": "crashed",
                "error": str(exc),
                "task_spec": None,
                "executor_result": None,
                "metrics": {},
            }
        elapsed = time.time() - started

        quality = score_task_spec_quality(pipeline.get("task_spec"))
        cost = executor_cost_from_metrics(pipeline.get("metrics"))
        pass_rate = acceptance_pass_rate(pipeline)
        fitness = compute_fitness(quality, pass_rate, cost, elapsed)

        result = RunResult(
            run_id=uuid.uuid4().hex[:12],
            timestamp=_utc_now(),
            variant_id=vid,
            user_prompt=user_prompt,
            status=str(pipeline.get("status", "unknown")),
            task_spec_quality_score=quality,
            executor_cost_usd=cost,
            acceptance_criteria_pass_rate=pass_rate,
            time_to_complete_seconds=round(elapsed, 3),
            fitness=fitness,
            task_spec=pipeline.get("task_spec"),
            error=pipeline.get("error"),
            metrics=pipeline.get("metrics"),
        )

        if record:
            self._record_run(result, count_toward_evolution=count_toward_evolution)
            if (
                trigger_evolution
                and self.state["runs_since_evolution"] >= self.evolution_interval
            ):
                self.evolve(user_prompt=user_prompt, execute_tools=execute_tools)

        return result

    def _record_run(self, result: RunResult, *, count_toward_evolution: bool = True) -> None:
        payload = asdict(result)
        self.state["runs"].append(payload)
        entry = self._history_entry(result.variant_id)
        if entry is not None:
            entry["results"].append(
                {
                    "run_id": result.run_id,
                    "timestamp": result.timestamp,
                    "task_spec_quality_score": result.task_spec_quality_score,
                    "executor_cost_usd": result.executor_cost_usd,
                    "acceptance_criteria_pass_rate": result.acceptance_criteria_pass_rate,
                    "time_to_complete_seconds": result.time_to_complete_seconds,
                    "fitness": result.fitness,
                    "status": result.status,
                }
            )
            fitnesses = [float(r["fitness"]) for r in entry["results"]]
            entry["aggregate_fitness"] = round(statistics.mean(fitnesses), 4)

        # Count toward evolution only for the current default variant.
        if count_toward_evolution and result.variant_id == self.current_variant_id():
            self.state["runs_since_evolution"] = int(self.state.get("runs_since_evolution", 0)) + 1

        self.state["events"].append(
            {
                "type": "run_recorded",
                "timestamp": result.timestamp,
                "run_id": result.run_id,
                "variant_id": result.variant_id,
                "task_spec_quality_score": result.task_spec_quality_score,
                "executor_cost_usd": result.executor_cost_usd,
                "acceptance_criteria_pass_rate": result.acceptance_criteria_pass_rate,
                "time_to_complete_seconds": result.time_to_complete_seconds,
                "fitness": result.fitness,
            }
        )
        self._save()

    def evolve(self, user_prompt: str, execute_tools: bool = True) -> Dict[str, Any]:
        """Identify best features, mutate, A/B test, promote winner."""
        analysis = identify_best_prompt_features(self.state["history"])
        current_id = self.current_variant_id()
        current_prompt = self.current_prompt()

        mutants = mutate_prompt(current_prompt, self.rng, n=self.num_mutants)
        # Bias mutants toward currently best features when possible.
        for feature_info in analysis.get("best_features") or []:
            feature = feature_info["feature"]
            if feature == "asks_measurable_criteria" and "measurable" not in current_prompt.lower():
                mutants[0] = (
                    mutants[0][0] + " +inject_measurable",
                    mutants[0][1].rstrip()
                    + "\n\nEmphasize measurable, verifiable acceptance criteria.",
                )
                break

        candidates: List[PromptVariant] = [
            PromptVariant(
                variant_id=current_id,
                prompt=current_prompt,
                features=extract_prompt_features(current_prompt),
                mutation="control",
            )
        ]
        for mutation, prompt_text in mutants:
            variant = PromptVariant(
                variant_id=_variant_id(prompt_text, prefix="mut"),
                prompt=prompt_text,
                features=extract_prompt_features(prompt_text),
                parent_id=current_id,
                mutation=mutation,
            )
            self._ensure_variant(variant)
            candidates.append(variant)

        scores: Dict[str, List[float]] = {c.variant_id: [] for c in candidates}
        trial_results: List[Dict[str, Any]] = []

        for candidate in candidates:
            for _ in range(self.ab_trials):
                # Fresh scratch workspace per trial.
                trial_workspace = os.path.join(
                    self.workspace_root, "ab", candidate.variant_id, uuid.uuid4().hex[:8]
                )
                result = self.run_once(
                    user_prompt,
                    prompt_variant=candidate.prompt,
                    variant_id=candidate.variant_id,
                    execute_tools=execute_tools,
                    workspace_root=trial_workspace,
                    record=True,
                    count_toward_evolution=False,
                    trigger_evolution=False,
                )
                scores[candidate.variant_id].append(result.fitness)
                trial_results.append(asdict(result))

        mean_scores = {
            vid: round(statistics.mean(vals), 4) if vals else float("-inf")
            for vid, vals in scores.items()
        }
        winner_id = max(mean_scores, key=mean_scores.get)
        winner = next(c for c in candidates if c.variant_id == winner_id)
        previous_default = current_id
        promoted = winner_id != current_id

        if promoted:
            self.state["current_default_variant_id"] = winner.variant_id
            self.state["current_default_prompt"] = winner.prompt

        ab_record = {
            "timestamp": _utc_now(),
            "user_prompt": user_prompt,
            "feature_analysis": analysis,
            "candidates": [
                {
                    "variant_id": c.variant_id,
                    "mutation": c.mutation,
                    "parent_id": c.parent_id,
                    "mean_fitness": mean_scores[c.variant_id],
                    "features": c.features,
                }
                for c in candidates
            ],
            "winner_variant_id": winner_id,
            "previous_default_variant_id": previous_default,
            "promoted": promoted,
            "trial_run_ids": [r["run_id"] for r in trial_results],
        }
        self.state["ab_tests"].append(ab_record)
        self.state["runs_since_evolution"] = 0
        self.state["events"].append(
            {
                "type": "evolution_cycle",
                "timestamp": ab_record["timestamp"],
                "winner_variant_id": winner_id,
                "promoted": promoted,
                "best_features": analysis.get("best_features"),
                "message": (
                    f"Promoted {winner_id} as new default"
                    if promoted
                    else f"Kept current default {current_id}"
                ),
            }
        )
        self._save()
        return ab_record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Dual-LLM Router with planner-prompt evolution logging"
    )
    parser.add_argument(
        "-p",
        "--prompt",
        type=str,
        default=(
            "Create a python module `math_utils.py` containing a function "
            "`add(a, b)` and a corresponding unit test `test_math_utils.py`."
        ),
        help="User task prompt for the pipeline",
    )
    parser.add_argument(
        "-n",
        "--runs",
        type=int,
        default=1,
        help="Number of consecutive runs to execute",
    )
    parser.add_argument(
        "--evolution-interval",
        type=int,
        default=DEFAULT_EVOLUTION_INTERVAL,
        help="Trigger prompt evolution after this many default-variant runs",
    )
    parser.add_argument(
        "--num-mutants",
        type=int,
        default=DEFAULT_NUM_MUTANTS,
        help="Number of mutated prompt variants to A/B test (2-3)",
    )
    parser.add_argument(
        "--ab-trials",
        type=int,
        default=DEFAULT_AB_TRIALS,
        help="Trials per candidate during an A/B evolution cycle",
    )
    parser.add_argument(
        "--evolve-now",
        action="store_true",
        help="Force an evolution/A/B cycle after the recorded runs",
    )
    parser.add_argument(
        "--log-path",
        type=str,
        default=str(DEFAULT_LOG_PATH),
        help="Path to evolution log JSON",
    )
    parser.add_argument(
        "-w",
        "--workspace",
        type=str,
        default=str(PROJECT_ROOT / "workspace" / "evolution"),
        help="Base workspace directory for evolution runs",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Skip tool execution (planner+executor JSON only)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for reproducible mutations",
    )
    parser.add_argument(
        "--show-status",
        action="store_true",
        help="Print current evolution status and exit",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    engine = EvolutionEngine(
        log_path=Path(args.log_path),
        evolution_interval=args.evolution_interval,
        num_mutants=args.num_mutants,
        ab_trials=args.ab_trials,
        workspace_root=args.workspace,
        seed=args.seed,
    )

    if args.show_status:
        print(json.dumps(
            {
                "log_path": str(engine.log_path),
                "current_default_variant_id": engine.current_variant_id(),
                "runs": len(engine.state["runs"]),
                "runs_since_evolution": engine.state.get("runs_since_evolution"),
                "evolution_interval": engine.evolution_interval,
                "history_variants": len(engine.state["history"]),
                "ab_tests": len(engine.state["ab_tests"]),
            },
            indent=2,
        ))
        return

    print("=== Dual-LLM Router Prompt Evolution ===")
    print(f"Log: {engine.log_path}")
    print(f"Default variant: {engine.current_variant_id()}")
    print(f"Evolution interval: every {engine.evolution_interval} runs\n")

    for i in range(max(1, args.runs)):
        print(f"--- Run {i + 1}/{args.runs} ---")
        result = engine.run_once(
            args.prompt,
            execute_tools=not args.no_tools,
        )
        print(
            f"status={result.status} quality={result.task_spec_quality_score} "
            f"pass_rate={result.acceptance_criteria_pass_rate} "
            f"executor_cost=${result.executor_cost_usd} "
            f"time={result.time_to_complete_seconds}s fitness={result.fitness}"
        )

    if args.evolve_now:
        print("\n=== Forcing evolution / A/B cycle ===")
        ab = engine.evolve(user_prompt=args.prompt, execute_tools=not args.no_tools)
        print(
            f"Winner: {ab['winner_variant_id']} "
            f"(promoted={ab['promoted']})"
        )
        best = (ab.get("feature_analysis") or {}).get("best_features") or []
        if best:
            print("Best features:")
            for item in best[:3]:
                print(f"  - {item['feature']} (lift={item['lift']})")

    print(f"\nEvolution log written to {engine.log_path}")


if __name__ == "__main__":
    main()
