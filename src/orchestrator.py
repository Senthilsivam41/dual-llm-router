from typing import Dict, Any, Optional
from .agents import PlannerAgent, ExecutorAgent
from .schemas.task_spec import TaskSpec
from .utils.metrics import MetricsLogger

class DualLLMRouterOrchestrator:
    def __init__(
        self,
        planner_model: Optional[str] = None,
        executor_model: Optional[str] = None,
        workspace_root: str = ".",
        planner_system_prompt: Optional[str] = None,
    ):
        planner_kwargs: Dict[str, Any] = {}
        if planner_model:
            planner_kwargs["model_name"] = planner_model
        if planner_system_prompt:
            planner_kwargs["system_prompt"] = planner_system_prompt
        self.planner = PlannerAgent(**planner_kwargs)
        self.executor = ExecutorAgent(workspace_root=workspace_root, **({"model_name": executor_model} if executor_model else {}))
        self.metrics_logger = MetricsLogger()

    def run(
        self,
        user_prompt: str,
        execute_tools: bool = True,
        max_iterations: int = 1
    ) -> Dict[str, Any]:
        """Runs Planner node -> Executor node pipeline sequentially."""
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        metrics_logger = MetricsLogger()
        self.metrics_logger = metrics_logger

        # Step 1: Planning Node (Hermes 4)
        try:
            task_spec, planner_meta = self.planner.plan(
                user_prompt=user_prompt,
                metrics_logger=metrics_logger
            )
        except Exception as e:
            return {
                "status": "planning_failed",
                "error": str(e),
                "task_spec": None,
                "executor_result": None,
                "metrics": metrics_logger.summary(),
            }

        # Step 2: Execution Node (Laguna S 2.1)
        executor_result: Dict[str, Any] = {}
        iterations = 0
        for iterations in range(1, max_iterations + 1):
            try:
                executor_result = self.executor.execute(
                    task_spec=task_spec,
                    metrics_logger=metrics_logger,
                    execute_tools=execute_tools
                )
            except Exception as e:
                return {
                    "status": "execution_failed",
                    "error": str(e),
                    "task_spec": task_spec.model_dump(),
                    "executor_result": None,
                    "iterations": iterations,
                    "metrics": metrics_logger.summary(),
                }
            if executor_result.get("success", False):
                break

        status = "completed" if executor_result.get("success", False) else "failed"

        return {
            "status": status,
            "task_spec": task_spec.model_dump(),
            "executor_result": executor_result,
            "iterations": iterations,
            "metrics": metrics_logger.summary(),
        }
