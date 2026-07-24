from typing import Dict, Any, Optional
from .agents import PlannerAgent, ExecutorAgent
from .schemas.task_spec import TaskSpec
from .utils.metrics import MetricsLogger

class DualLLMRouterOrchestrator:
    def __init__(
        self,
        planner_model: Optional[str] = None,
        executor_model: Optional[str] = None,
        workspace_root: str = "."
    ):
        self.planner = PlannerAgent(**({"model_name": planner_model} if planner_model else {}))
        self.executor = ExecutorAgent(workspace_root=workspace_root, **({"model_name": executor_model} if executor_model else {}))
        self.metrics_logger = MetricsLogger()

    def run(
        self,
        user_prompt: str,
        execute_tools: bool = True,
        max_iterations: int = 1
    ) -> Dict[str, Any]:
        """Runs Planner node -> Executor node pipeline sequentially."""
        # Step 1: Planning Node (Hermes 4)
        try:
            task_spec, planner_meta = self.planner.plan(
                user_prompt=user_prompt,
                metrics_logger=self.metrics_logger
            )
        except Exception as e:
            return {
                "status": "planning_failed",
                "error": str(e),
                "task_spec": None,
                "executor_result": None,
                "metrics": self.metrics_logger.summary(),
            }

        # Step 2: Execution Node (Laguna S 2.1)
        try:
            executor_result = self.executor.execute(
                task_spec=task_spec,
                metrics_logger=self.metrics_logger,
                execute_tools=execute_tools
            )
        except Exception as e:
            return {
                "status": "execution_failed",
                "error": str(e),
                "task_spec": task_spec.model_dump(),
                "executor_result": None,
                "metrics": self.metrics_logger.summary(),
            }

        status = "completed" if executor_result.get("success", False) else "failed"

        return {
            "status": status,
            "task_spec": task_spec.model_dump(),
            "executor_result": executor_result,
            "metrics": self.metrics_logger.summary(),
        }
