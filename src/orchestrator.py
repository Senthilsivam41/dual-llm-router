from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, Optional

from .agents import PlannerAgent, ExecutorAgent
from .agents.planner import build_planner_user_message
from .schemas.task_spec import TaskSpec
from .utils.metrics import MetricsLogger
from .verification.cross_check import (
    planner_accuracy,
    planner_disagreements,
    validate_report_checks,
)
from .verification.feedback import build_executor_feedback
from .workspace_seed import write_seed_files

_PLANNER_ATTEMPTS = 2


class DualLLMRouterOrchestrator:
    def __init__(
        self,
        planner_model: Optional[str] = None,
        executor_model: Optional[str] = None,
        workspace_root: str = ".",
        planner_system_prompt: Optional[str] = None,
        *,
        executor_system_prompt: Optional[str] = None,
        attempt_verifier: Callable[[Path], Dict[str, Any]] | None = None,
        task_context: str = "",
    ):
        planner_kwargs: Dict[str, Any] = {}
        if planner_model:
            planner_kwargs["model_name"] = planner_model
        if planner_system_prompt:
            planner_kwargs["system_prompt"] = planner_system_prompt
        self.planner = PlannerAgent(**planner_kwargs)
        self.executor = ExecutorAgent(
            workspace_root=workspace_root,
            **({"model_name": executor_model} if executor_model else {}),
            system_prompt=executor_system_prompt,
            attempt_verifier=attempt_verifier,
            task_context=task_context,
        )
        self.metrics_logger = MetricsLogger()

    def run(
        self,
        user_prompt: str,
        execute_tools: bool = True,
        max_iterations: int = 1,
        issue_text: Optional[str] = None,
        seed_files: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Runs Planner node -> Executor node pipeline sequentially."""
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        metrics_logger = MetricsLogger()
        self.metrics_logger = metrics_logger
        workspace = Path(self.executor.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        if seed_files:
            write_seed_files(workspace, seed_files)

        planned = self.plan_task(user_prompt, issue_text=issue_text, metrics_logger=metrics_logger)
        if planned.get("status") == "planning_failed":
            return planned
        result = self.execute_plan(
            planned["task_spec_model"],
            execute_tools=execute_tools,
            max_iterations=max_iterations,
            metrics_logger=metrics_logger,
        )
        return {**result, **{k: v for k, v in planned.items() if k.startswith("planner_")}}

    def execute_plan(
        self,
        task_spec: TaskSpec,
        *,
        execute_tools: bool = True,
        max_iterations: int = 1,
        metrics_logger: MetricsLogger | None = None,
        initial_feedback: str | None = None,
        feedback_builder: Callable[[str, Dict[str, Any]], str] = build_executor_feedback,
    ) -> Dict[str, Any]:
        """Execute an accepted plan, optionally continuing a previous attempt."""
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        metrics_logger = metrics_logger or MetricsLogger()
        workspace = self.executor.workspace_root
        executor_result: Dict[str, Any] = {}
        feedback = initial_feedback
        attempts = []
        iterations = 0
        for iterations in range(1, max_iterations + 1):
            start = perf_counter()
            try:
                executor_result = self.executor.execute(
                    task_spec=task_spec,
                    metrics_logger=metrics_logger,
                    execute_tools=execute_tools,
                    feedback=feedback,
                )
            except Exception as exc:
                failure = {
                    "status": "execution_failed",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "task_spec": task_spec.model_dump(),
                    "executor_result": None,
                    "iterations": iterations,
                    "metrics": metrics_logger.summary(),
                }
                if self.executor.attempt_verifier is not None:
                    failure["attempts"] = attempts + [{
                        "attempt": iterations,
                        "error_type": type(exc).__name__,
                        "wall_seconds": perf_counter() - start,
                    }]
                return failure
            report = executor_result.get("verification_report") or {}
            attempts.append(
                {
                    "attempt": iterations,
                    "success": bool(executor_result.get("success")),
                    "cost_usd": executor_result.get("cost_usd"),
                    "unmatched": report.get("unmatched") or [],
                    "pytest_output": str((report.get("pytest") or {}).get("output") or "")[:2000],
                }
            )
            if self.executor.attempt_verifier is not None:
                attempts[-1].update(
                    wall_seconds=perf_counter() - start,
                    verification=report,
                    feedback=feedback,
                )
            if executor_result.get("success", False):
                break
            if iterations < max_iterations:
                feedback = feedback_builder(str(workspace), report)

        executor_result["attempts"] = attempts
        status = "completed" if executor_result.get("success", False) else "failed"
        return {
            "status": status,
            "task_spec": task_spec.model_dump(),
            "executor_result": executor_result,
            "iterations": iterations,
            "metrics": metrics_logger.summary(),
        }

    def plan_task(
        self,
        user_prompt: str,
        *,
        issue_text: Optional[str] = None,
        metrics_logger: MetricsLogger | None = None,
        validate_plan: Callable[[TaskSpec], str | None] | None = None,
    ) -> Dict[str, Any]:
        metrics_logger = metrics_logger or MetricsLogger()
        last_error: Optional[str] = None
        task_spec: Optional[TaskSpec] = None
        for attempt in range(1, _PLANNER_ATTEMPTS + 1):
            message = build_planner_user_message(
                user_prompt,
                self.executor.workspace_root,
                issue_text=issue_text,
                rejection=last_error,
            )
            try:
                task_spec, _meta = self.planner.plan(
                    user_prompt=message,
                    metrics_logger=metrics_logger,
                )
            except ValueError as exc:
                last_error = str(exc)
                if attempt == _PLANNER_ATTEMPTS:
                    return self._planning_failed(last_error, metrics_logger, attempt)
                continue
            except Exception as exc:
                return {
                    **self._planning_failed(str(exc), metrics_logger, attempt),
                    "error_type": type(exc).__name__,
                }

            check_error = validate_report_checks(task_spec, issue_text) if issue_text is not None else None
            if not check_error and validate_plan is not None:
                check_error = validate_plan(task_spec)
            if check_error:
                last_error = check_error
                if attempt == _PLANNER_ATTEMPTS:
                    return self._planning_failed(check_error, metrics_logger, attempt)
                continue
            accuracy = planner_accuracy(task_spec.checks)
            return {
                "task_spec_model": task_spec,
                "planner_attempts": attempt,
                "planner_accuracy": accuracy,
                "planner_disagreements": planner_disagreements(task_spec.checks),
            }

        return self._planning_failed(
            last_error or "planning failed",
            metrics_logger,
            _PLANNER_ATTEMPTS,
        )

    def _planning_failed(
        self,
        error: str,
        metrics_logger: MetricsLogger,
        attempts: int,
    ) -> Dict[str, Any]:
        return {
            "status": "planning_failed",
            "error": error,
            "task_spec": None,
            "executor_result": None,
            "iterations": 0,
            "planner_attempts": attempts,
            "planner_accuracy": None,
            "planner_disagreements": [],
            "metrics": metrics_logger.summary(),
        }
