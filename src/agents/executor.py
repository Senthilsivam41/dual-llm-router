import json
import time
from typing import Dict, Any, List
from ..config import config
from ..schemas.task_spec import TaskSpec
from ..tools import apply_patch, run_shell
from ..utils.metrics import MetricsLogger

try:
    from litellm import completion
except ImportError:
    completion = None

EXECUTOR_SYSTEM_PROMPT = """You are Laguna S 2.1, an expert agentic execution model.
Your task is to take a TaskSpec, analyze target files/goals, and produce execution tool calls or code patches to fulfill all acceptance criteria.
Available tool actions:
- apply_patch(file_path, new_content)
- run_shell(command)

Output your execution steps as JSON:
{
  "summary": "<summary of actions>",
  "actions": [
    {"type": "apply_patch", "file_path": "...", "content": "..."},
    {"type": "run_shell", "command": "..."}
  ],
  "verification_results": ["<how criteria were checked>"]
}
"""

class ExecutorAgent:
    def __init__(self, model_name: str = config.executor_model, workspace_root: str = "."):
        self.model_name = model_name
        self.workspace_root = workspace_root

    def execute(
        self,
        task_spec: TaskSpec,
        metrics_logger: MetricsLogger = None,
        execute_tools: bool = True
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        prompt_payload = (
            f"Goal: {task_spec.goal}\n"
            f"Target Files: {task_spec.target_files}\n"
            f"Acceptance Criteria: {task_spec.acceptance_criteria}\n"
            f"Plan: {task_spec.step_by_step_plan}\n"
            f"Notes: {task_spec.notes or ''}"
        )
        
        if completion is None:
            raw_json = json.dumps({
                "summary": "Mock execution completed",
                "actions": [],
                "verification_results": ["Executed in fallback mode"],
            })
            elapsed = time.time() - start_time
            prompt_tokens, completion_tokens = 100, 50
        else:
            messages = [
                {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_payload},
            ]
            response = completion(
                model=self.model_name,
                messages=messages,
                api_key=config.openrouter_api_key if config.openrouter_api_key else None,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            elapsed = time.time() - start_time
            raw_json = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        
        if metrics_logger:
            metrics_logger.log_call(
                node="ExecutorAgent",
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_seconds=elapsed,
            )
            
        cleaned_json = raw_json.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            
        execution_plan = json.loads(cleaned_json.strip())
        tool_results = []
        
        if execute_tools and "actions" in execution_plan:
            for action in execution_plan["actions"]:
                action_type = action.get("type")
                if action_type == "apply_patch":
                    res = apply_patch(
                        file_path=action["file_path"],
                        new_content=action["content"],
                        workspace_root=self.workspace_root,
                    )
                    tool_results.append({"action": action, "result": res})
                elif action_type == "run_shell":
                    res = run_shell(
                        command=action["command"],
                        workspace_root=self.workspace_root,
                    )
                    tool_results.append({"action": action, "result": res})
                    
        return {
            "execution_plan": execution_plan,
            "tool_results": tool_results,
            "latency": elapsed,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens},
        }
