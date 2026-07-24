import json
import os
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
            
        cleaned_json = raw_json.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            execution_plan = json.loads(cleaned_json)
        except Exception as e:
            execution_plan = {"error": f"Failed to parse execution plan JSON: {e}", "raw_response": raw_json}

        tool_results = []
        all_tools_succeeded = True
        
        if execute_tools and "actions" in execution_plan and isinstance(execution_plan["actions"], list):
            for action in execution_plan["actions"]:
                action_type = action.get("type")
                if action_type == "apply_patch":
                    res = apply_patch(
                        file_path=action["file_path"],
                        new_content=action["content"],
                        workspace_root=self.workspace_root,
                    )
                    tool_results.append({"action": action, "result": res})
                    if not res.get("success", False):
                        all_tools_succeeded = False
                elif action_type == "run_shell":
                    res = run_shell(
                        command=action["command"],
                        workspace_root=self.workspace_root,
                    )
                    tool_results.append({"action": action, "result": res})
                    if not res.get("success", False):
                        all_tools_succeeded = False

        # Verify acceptance criteria & target files
        criteria_verification = []
        criteria_passed = True
        
        # Check target files existence
        for target_file in task_spec.target_files:
            file_abs_path = os.path.join(self.workspace_root, target_file)
            exists = os.path.exists(file_abs_path)
            criteria_verification.append({
                "criterion": f"Target file '{target_file}' exists",
                "passed": exists,
                "details": "File exists on disk" if exists else "File missing from workspace"
            })
            if not exists:
                criteria_passed = False

        overall_success = all_tools_succeeded and criteria_passed and ("error" not in execution_plan)

        return {
            "success": overall_success,
            "execution_plan": execution_plan,
            "tool_results": tool_results,
            "verification_report": {
                "tools_succeeded": all_tools_succeeded,
                "criteria_passed": criteria_passed,
                "details": criteria_verification
            },
            "latency": elapsed,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens},
        }
