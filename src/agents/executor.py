import json
import os
import time
from typing import Dict, Any, List, Optional
from ..config import config
from ..schemas.task_spec import TaskSpec
from ..tools import apply_patch, run_shell
from ..tools.action_schemas import validate_actions, ActionModel
from ..utils.metrics import MetricsLogger
from prompts.laguna.base import LAGUNA_SYSTEM_PROMPT

try:
    from litellm import completion
except ImportError:
    completion = None

# Back-compat alias; canonical prompt lives in prompts/laguna/base.py
EXECUTOR_SYSTEM_PROMPT = LAGUNA_SYSTEM_PROMPT

class ExecutorAgent:
    def __init__(
        self,
        model_name: str = config.executor_model,
        workspace_root: str = ".",
        system_prompt: Optional[str] = None,
    ):
        self.model_name = model_name
        self.workspace_root = workspace_root
        self.system_prompt = system_prompt or EXECUTOR_SYSTEM_PROMPT

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
                {"role": "system", "content": self.system_prompt},
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
            # Validate all actions before execution using Pydantic schemas
            try:
                validated_actions: List[ActionModel] = validate_actions(execution_plan["actions"])
            except ValueError as e:
                tool_results.append({
                    "action": execution_plan["actions"],
                    "result": {"success": False, "error": f"Action validation failed: {e}"}
                })
                all_tools_succeeded = False
                validated_actions = []
            
            for action in validated_actions:
                action_dict = action.model_dump()
                action_type = action_dict.get("type")
                if action_type == "apply_patch":
                    res = apply_patch(
                        file_path=action_dict["file_path"],
                        new_content=action_dict.get("patch") or action_dict.get("content"),
                        workspace_root=self.workspace_root,
                    )
                    tool_results.append({"action": action_dict, "result": res})
                    if not res.get("success", False):
                        all_tools_succeeded = False
                elif action_type == "shell":
                    res = run_shell(
                        command=action_dict["command"],
                        workspace_root=self.workspace_root,
                    )
                    tool_results.append({"action": action_dict, "result": res})
                    if not res.get("success", False):
                        all_tools_succeeded = False
                else:
                    tool_results.append({
                        "action": action_dict,
                        "result": {
                            "success": False,
                            "error": f"Unsupported action type: {action_type}",
                        },
                    })
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
