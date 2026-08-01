"""Dual-LLM router with optional co-evolution integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from evals.evolution_engine import EvolutionEngine
from src.orchestrator import DualLLMRouterOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class Prompt:
    path: str
    few_shot_path: str = ""
    text: str = ""


class DualLLMRouter(DualLLMRouterOrchestrator):
    """Public router entrypoint used by scripts and evolution."""

    def __init__(
        self,
        planner_model: Optional[str] = None,
        executor_model: Optional[str] = None,
        workspace_root: str = ".",
        planner_system_prompt: Optional[str] = None,
        executor_system_prompt: Optional[str] = None,
    ):
        super().__init__(
            planner_model=planner_model,
            executor_model=executor_model,
            workspace_root=workspace_root,
            planner_system_prompt=planner_system_prompt,
        )
        if executor_system_prompt:
            self.executor.system_prompt = executor_system_prompt


class EvolvingRouter(DualLLMRouter):
    """Router with built-in Hermes/Laguna co-evolution."""

    def __init__(
        self,
        evolution_engine: Optional[EvolutionEngine] = None,
        workspace_root: str = ".",
        **kwargs: Any,
    ):
        self.evolution_engine = evolution_engine or EvolutionEngine()
        hermes = self.evolution_engine.get_prompt_for_variant(
            self.evolution_engine.active_hermes
        )
        laguna = self.evolution_engine.get_prompt_for_variant(
            self.evolution_engine.active_laguna
        )
        super().__init__(
            workspace_root=workspace_root,
            planner_system_prompt=hermes.get("text") or None,
            executor_system_prompt=laguna.get("text") or None,
            **kwargs,
        )

    def route_task(
        self,
        user_prompt: str,
        *,
        execute_tools: bool = True,
        task: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Route a task with evolution awareness and run logging."""
        if self.evolution_engine.should_evolve():
            result = self.evolution_engine.evolve()
            logger.info("Evolution complete: %s", result)

        hermes_variant = self.evolution_engine.active_hermes
        laguna_variant = self.evolution_engine.active_laguna
        hermes_prompt = self._get_prompt(hermes_variant)
        laguna_prompt = self._get_prompt(laguna_variant)

        # Refresh agent prompts for this run.
        self.planner.system_prompt = hermes_prompt.text or self.planner.system_prompt
        self.executor.system_prompt = laguna_prompt.text or self.executor.system_prompt

        pipeline = super().run(user_prompt, execute_tools=execute_tools)

        metrics = pipeline.get("metrics") or {}
        executor_result = pipeline.get("executor_result") or {}
        verification = executor_result.get("verification_report") or {}
        details = verification.get("details") or []
        pass_rate = (
            sum(1 for d in details if d.get("passed")) / len(details) if details else float(
                bool(verification.get("criteria_passed") or executor_result.get("success"))
            )
        )

        status = pipeline.get("status", "failure")
        if status == "completed":
            status = "success"

        self.evolution_engine.record_run_result(
            {
                "config": {
                    "hermes_variant": hermes_variant,
                    "laguna_variant": laguna_variant,
                    "hermes_prompt_path": hermes_prompt.path,
                    "laguna_prompt_path": laguna_prompt.path,
                },
                "task": (task or {}).get("spec", {"spec_id": "ad_hoc", "expected_cost": 0.15}),
                "result": {
                    "status": status,
                    "cost": float(metrics.get("total_cost_usd") or 0.0),
                    "time_seconds": float(metrics.get("total_latency_seconds") or 0.0),
                    "iterations": 1,
                    "executor_calls": sum(
                        1
                        for m in metrics.get("breakdown") or []
                        if "executor" in str(m.get("node", "")).lower()
                    ),
                },
                "quality_metrics": {
                    "task_spec_clarity": 1.0 if pipeline.get("task_spec") else 0.0,
                    "code_quality_score": pass_rate,
                    "test_coverage": pass_rate,
                    "acceptance_criteria_pass": bool(
                        verification.get("criteria_passed") or executor_result.get("success")
                    ),
                    "quality_score": pass_rate,
                    "cost_efficiency": 0.0,
                },
            }
        )
        return pipeline

    def _get_prompt(self, variant_id: str) -> Prompt:
        """Load prompt for a specific variant."""
        info = self.evolution_engine.get_prompt_for_variant(variant_id)
        return Prompt(
            path=info.get("path", ""),
            few_shot_path=info.get("few_shot_path", ""),
            text=info.get("text", ""),
        )

    def run(
        self,
        user_prompt: str,
        execute_tools: bool = True,
        max_iterations: int = 1,
    ) -> Dict[str, Any]:
        return self.route_task(user_prompt, execute_tools=execute_tools)
