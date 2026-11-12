"""Run the development phase and paired reconciliation trials."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from evals.evolution_engine import EvolutionEngine
from prompts.hermes.base import HERMES_SYSTEM_PROMPT
from prompts.laguna.base import LAGUNA_SYSTEM_PROMPT
from src.agents.provider import completion_options
from src.config import config
from src.orchestrator import DualLLMRouterOrchestrator
from src.schemas.task_spec import TaskSpec
from src.utils.metrics import MetricsLogger

from .fixtures import Scenario, fixture_hash, scenarios, sha256
from .verifier import DockerRunner, SandboxError, verify

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "reconciliation"
REPETITIONS = 2
GENERIC_FEEDBACK = "The independent reconciliation verifier failed. Review the current program and policy."
GUIDANCE = {
    "currency": "Preserve the invoice currency exactly in each summary.",
    "currency_mismatch": "Check each remaining payment's currency against its invoice before aggregation.",
    "duplicate_output_row": "Produce one summary per invoice and at most one exception per payment data row.",
    "duplicate_payment_id": "Pre-count payment IDs across the entire file and reject all occurrences of duplicates before any other validation.",
    "invoiced_cents": "Convert invoice amounts using exact decimal arithmetic and report the original invoiced cents.",
    "malformed_output": "Use json.dumps to print a single JSON object with no surrounding text.",
    "missing_invoice": "Build summaries from the invoice table so invoices with zero valid payments are represented.",
    "missing_program": "Return an apply_patch action containing the complete reconcile.py program.",
    "ordering": "Sort summaries by invoice ID and exceptions by their numeric input row.",
    "output_limit": "Emit only the requested JSON object and avoid debug output.",
    "output_schema": "Compare every output key and scalar type against the contract before returning the patch.",
    "paid_cents": "Sum exact integer cents only from accepted payments; preserve every valid payment, including partial payments.",
    "program_exit": "Check imports, CLI arguments, CSV headers, and JSON serialization for a standalone standard-library invocation.",
    "program_size": "Use a compact standard-library implementation that computes the result from input CSVs.",
    "status": "Derive invoice status by explicitly comparing total paid cents with invoiced cents, including zero and overpayment.",
    "timeout": "Read inputs once and use ID-indexed lookups and counters to avoid repeated scans.",
    "unexpected_row": "Emit summaries only for input invoices and exceptions only for rejected payment rows.",
    "unknown_invoice": "Look up the invoice ID before checking currency and report unmatched IDs with the original payment row.",
    "invalid_actions": "Return a JSON action object with an apply_patch action for reconcile.py.",
}


@contextmanager
def provider_settings():
    previous = config.provider_max_retries, config.max_tokens
    config.provider_max_retries = 0
    config.max_tokens = 8192
    try:
        yield
    finally:
        config.provider_max_retries, config.max_tokens = previous


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_plan(task: TaskSpec) -> str | None:
    if task.target_files != ["reconcile.py"] or task.checks:
        return "Target only reconcile.py and omit the checks array. An independent runner verifies the policy."
    return None


def _generic_feedback(_workspace: str, _report: dict[str, Any]) -> str:
    return GENERIC_FEEDBACK


def _diagnostic_feedback(_workspace: str, report: dict[str, Any]) -> str:
    diagnostics = json.dumps(report.get("diagnostics", []), separators=(",", ":"))
    return f"{GENERIC_FEEDBACK}\nVerifier diagnostics for the diagnostic fixture: {diagnostics}"


def _snapshot(workspace: Path) -> str | None:
    program = workspace / "reconcile.py"
    if program.is_file() and not program.is_symlink() and program.stat().st_size <= 65_536:
        return sha256(program.read_text(encoding="utf-8", errors="replace"))
    return None


def _cost_metrics(metrics: MetricsLogger, wall_seconds: float) -> dict[str, Any]:
    summary = metrics.summary()
    return {
        "wall_seconds": wall_seconds,
        "calls": metrics.attempted_calls,
        "cost_usd": summary["total_cost_usd"] if summary["total_calls"] == metrics.attempted_calls else None,
        "estimated_calls": sum(row.cost_source == "estimate" for row in metrics.metrics),
        "model_calls": summary["breakdown"],
    }


def _arm(
    segments: list[dict[str, Any]], passed: bool | None, infrastructure_error: str | None = None,
) -> dict[str, Any]:
    costs = [part["cost_usd"] for part in segments]
    return {
        "passed": passed,
        "infrastructure_error": infrastructure_error,
        "wall_seconds": sum(part["wall_seconds"] for part in segments),
        "calls": sum(part["calls"] for part in segments),
        "cost_usd": sum(costs) if all(cost is not None for cost in costs) else None,
        "estimated_calls": sum(part["estimated_calls"] for part in segments),
    }


class TrialRunner:
    def __init__(self, models: dict[str, str], runner: DockerRunner, policy: str):
        self.models = models
        self.runner = runner
        self.policy = policy

    def _router(
        self, workspace: Path, scenario: Scenario, prompt: str = LAGUNA_SYSTEM_PROMPT,
    ) -> DualLLMRouterOrchestrator:
        public = scenario.diagnostic
        context = f"{self.policy}\nDiagnostic fixture\ninvoices.csv\n{public.invoices}\npayments.csv\n{public.payments}"
        return DualLLMRouterOrchestrator(
            planner_model=self.models["planner"],
            executor_model=self.models["executor"],
            workspace_root=str(workspace),
            executor_system_prompt=prompt,
            task_context=context,
            attempt_verifier=lambda root: verify(root, public, self.runner),
        )

    def _execute(
        self,
        router: DualLLMRouterOrchestrator,
        plan: TaskSpec,
        scenario: Scenario,
        *,
        retries: int = 0,
        initial_feedback: str | None = None,
        formatter: Callable[[str, dict[str, Any]], str] = _generic_feedback,
        score_private: bool = True,
    ) -> dict[str, Any]:
        metrics = MetricsLogger()
        workspace = Path(router.executor.workspace_root)
        start = perf_counter()
        initial_hash = _snapshot(workspace)
        result = router.execute_plan(
            plan, max_iterations=1 + retries, metrics_logger=metrics,
            initial_feedback=initial_feedback, feedback_builder=formatter,
        )
        wall = perf_counter() - start
        executor = result.get("executor_result") or {}
        error = result.get("error_type")
        private_pass: bool | None = None
        if error is None and score_private:
            try:
                verdicts = [
                    verify(workspace, probe, self.runner)["criteria_passed"] for probe in scenario.private
                ]
                private_pass = all(verdicts)
            except SandboxError:
                error = "PrivateSandboxError"
        return {
            **_cost_metrics(metrics, wall),
            "attempts": executor.get("attempts") or result.get("attempts") or [],
            "diagnostic": executor.get("verification_report"),
            "public_pass": executor.get("success"),
            "private_pass": private_pass,
            "infrastructure_error": error,
            "initial_program_sha256": initial_hash,
            "final_program_sha256": _snapshot(workspace),
        }

    def run(
        self, workspace: Path, scenario: Scenario, repetition: int, *,
        candidate: str | None = None, development: bool = False,
    ) -> dict[str, Any]:
        first_path = workspace / "first" / "workspace"
        first_path.mkdir(parents=True)
        first_router = self._router(first_path, scenario)
        plan_metrics = MetricsLogger()
        start = perf_counter()
        planned = first_router.plan_task(
            self.policy, metrics_logger=plan_metrics, validate_plan=_validate_plan,
        )
        plan_time = perf_counter() - start
        plan = planned.get("task_spec_model")
        planning_error = planned.get("error_type")
        planning = {
            **_cost_metrics(plan_metrics, plan_time),
            "task_spec": plan.model_dump() if plan is not None else None,
            "attempts": planned["planner_attempts"],
            "status": "accepted" if plan is not None else "failed",
            "infrastructure_error": planning_error,
        }
        trial: dict[str, Any] = {
            "scenario": scenario.id, "family": scenario.family, "repetition": repetition,
            "planning": planning, "executions": {}, "arms": {}, "order": [],
        }
        arms = trial["arms"]
        executions = trial["executions"]
        arm_names = ["first"] if development else ["first", "generic", "diagnostics"]
        if candidate is not None:
            arm_names.append("candidate")
        if plan is None:
            for name in arm_names:
                arms[name] = _arm([planning], None if planning_error else False, planning_error)
            return trial

        def run_candidate() -> None:
            candidate_path = workspace / "candidate" / "workspace"
            candidate_path.mkdir(parents=True)
            trial["order"].append("candidate")
            execution = self._execute(self._router(candidate_path, scenario, candidate), plan, scenario)
            executions["candidate"] = execution
            arms["candidate"] = _arm(
                [planning, execution], execution["private_pass"], execution["infrastructure_error"],
            )

        if candidate is not None and repetition % 2 == 0:
            run_candidate()
        trial["order"].append("first")
        first = self._execute(first_router, plan, scenario, score_private=not development)
        executions["first"] = first
        first_verdict = first["public_pass"] if development else first["private_pass"]
        arms["first"] = _arm([planning, first], first_verdict, first["infrastructure_error"])
        if development:
            return trial
        if candidate is not None and repetition % 2 == 1:
            run_candidate()

        formatters = {"generic": _generic_feedback, "diagnostics": _diagnostic_feedback}
        order = ("generic", "diagnostics") if repetition % 2 == 1 else ("diagnostics", "generic")
        for name in order:
            if first["public_pass"] is not False:
                arms[name] = dict(arms["first"])
                continue
            trial["order"].append(name)
            retry_path = workspace / name / "workspace"
            shutil.copytree(first_path, retry_path)
            report = first["diagnostic"]
            formatter = formatters[name]
            execution = self._execute(
                self._router(retry_path, scenario), plan, scenario,
                retries=1, formatter=formatter, initial_feedback=formatter(str(retry_path), report),
            )
            executions[name] = execution
            arms[name] = _arm(
                [planning, first, execution], execution["private_pass"], execution["infrastructure_error"],
            )
        return trial


def select_guidance(development: list[dict[str, Any]]) -> tuple[dict[str, int], list[str]]:
    counts: Counter[str] = Counter()
    for trial in development:
        first = trial["executions"].get("first") or {}
        if first.get("infrastructure_error"):
            continue
        report = first.get("diagnostic") or {}
        counts.update(set(report.get("failure_codes", [])) & GUIDANCE.keys())
    selected = sorted(counts, key=lambda code: (-counts[code], code))[:2]
    return dict(sorted(counts.items())), selected


def _record_development(
    engine: EvolutionEngine, trial: dict[str, Any], planner: str, executor: str, scripted: bool,
) -> None:
    first = trial["arms"]["first"]
    diagnostic = (trial["executions"].get("first") or {}).get("diagnostic") or {}
    engine.record_run_result({
        "run_id": trial["scenario"],
        "config": {"hermes_variant": planner, "laguna_variant": executor},
        "task": {"spec_id": trial["scenario"], "domain": "reconciliation"},
        "result": {
            "status": "infrastructure_error" if first["passed"] is None else
                      "success" if first["passed"] else "failure",
            "cost": first["cost_usd"], "time_seconds": first["wall_seconds"],
            "failure_codes": diagnostic.get("failure_codes", []),
        },
        "simulated": scripted,
    })


def make_record(models: dict[str, str], policy: str, *, demo: bool, mode: str) -> dict[str, Any]:
    development = () if demo else scenarios("development")
    holdout = scenarios("holdout")[:1] if demo else scenarios("holdout")
    return {
        "schema_version": 1, "mode": mode, "scope": "demo" if demo else "study",
        "status": "running", "started_at": utc_now(), "models": models,
        "protocol": {
            "development_cases": len(development), "holdout_cases": len(holdout),
            "trials_per_case": 1 if demo else REPETITIONS,
            "max_provider_calls": 548 if not demo else 8,
            "max_tokens": config.max_tokens,
            "provider_retries": config.provider_max_retries,
            "provider_timeout_seconds": config.provider_timeout_seconds,
            "planner_temperature": 0.1, "executor_temperature": 0.2,
            "provider_options": {role: completion_options(model) for role, model in models.items()},
            "fixture_sha256": {
                "development": fixture_hash(development), "holdout": fixture_hash(holdout),
            },
            "policy_sha256": sha256(policy),
            "prompt_sha256": {
                "planner": sha256(HERMES_SYSTEM_PROMPT), "executor": sha256(LAGUNA_SYSTEM_PROMPT),
            },
        },
        "preflight": {}, "development": [], "candidate": None, "trials": [],
    }


def run_study(
    output: Path,
    record: dict[str, Any],
    runner: TrialRunner,
    *,
    jobs: int,
    checkpoint: Callable[[dict[str, Any]], None],
) -> None:
    demo = record["scope"] == "demo"
    candidate_prompt = None
    if not demo:
        engine = EvolutionEngine(root=output / "evolution")
        planner = engine.register_prompt_variant("hermes", HERMES_SYSTEM_PROMPT, source="baseline")
        executor = engine.register_prompt_variant("laguna", LAGUNA_SYSTEM_PROMPT, source="baseline")
        cases = scenarios("development")
        if fixture_hash(cases) != record["protocol"]["fixture_sha256"]["development"]:
            raise ValueError("Development scenarios differ from the frozen protocol")
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = [
                pool.submit(runner.run, output / "runs" / case.id / "1", case, 1, development=True)
                for case in cases
            ]
            for future in futures:
                trial = future.result()
                record["development"].append(trial)
                _record_development(
                    engine, trial, planner["variant_id"], executor["variant_id"], record["mode"] != "live",
                )
                checkpoint(record)
        counts, codes = select_guidance(record["development"])
        if codes:
            candidate_prompt = LAGUNA_SYSTEM_PROMPT.rstrip() + "\n\nReconciliation guidance:\n" + "\n".join(
                f"- {GUIDANCE[code]}" for code in codes
            ) + "\n"
            evidence = {"counts": counts, "selected_codes": codes, "prompt_sha256": sha256(candidate_prompt)}
            candidate = engine.register_prompt_variant(
                "laguna", candidate_prompt, source="reconciliation_development_feedback",
                parent_id=executor["variant_id"], evidence=evidence,
            )
            record["candidate"] = {
                "variant_id": candidate["variant_id"], "parent_id": candidate["parent_id"], **evidence,
            }
        else:
            observed = sum(trial["arms"]["first"]["passed"] is not None for trial in record["development"])
            record["candidate"] = {
                "status": "no_actionable_development_failures" if observed else "no_scored_development_trials",
                "counts": counts,
            }
        checkpoint(record)

    cases = scenarios("holdout")[:1] if demo else scenarios("holdout")
    expected = record["protocol"]
    if fixture_hash(cases) != expected["fixture_sha256"]["holdout"]:
        raise ValueError("Holdout differs from the frozen protocol")
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [
            pool.submit(
                runner.run, output / "runs" / case.id / str(repetition), case, repetition,
                candidate=candidate_prompt,
            )
            for case in cases
            for repetition in range(1, expected["trials_per_case"] + 1)
        ]
        for future in futures:
            record["trials"].append(future.result())
            checkpoint(record)

    entries = record["trials"] + record["development"]
    record["status"] = (
        "incomplete" if any(arm["passed"] is None for trial in entries for arm in trial["arms"].values())
        else "complete"
    )
    record["finished_at"] = utc_now()
    checkpoint(record)
