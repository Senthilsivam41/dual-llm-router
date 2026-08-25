import json
import os
import re
import time
from typing import Dict, Any, List, Optional
from ..config import config
from ..schemas.task_spec import TaskSpec
from ..tools import apply_patch, run_shell
from ..tools.action_schemas import validate_actions, ActionModel
from ..utils.metrics import MetricsLogger
from .provider import call_with_retry, response_cost, validate_provider_credentials
from prompts.laguna.base import LAGUNA_SYSTEM_PROMPT

try:
    from litellm import completion
except ImportError:
    completion = None

# Back-compat alias; canonical prompt lives in prompts/laguna/base.py
EXECUTOR_SYSTEM_PROMPT = LAGUNA_SYSTEM_PROMPT


_EXISTENCE_WORDS = {"exist", "exists", "created", "present"}


def _is_file_existence_criterion(criterion: str, file_path: str) -> bool:
    """Return whether a criterion is an objective file-existence assertion."""
    normalized = re.sub(r"[^a-z0-9_./-]+", " ", criterion.lower())
    words = set(normalized.split())
    return file_path.lower() in normalized and bool(words & _EXISTENCE_WORDS)


def _is_safe_action_criterion(criterion: str) -> bool:
    """Recognize criteria directly proven by validated tool execution."""
    words = set(re.sub(r"[^a-z0-9]+", " ", criterion.lower()).split())
    return {"action", "executed", "safely"}.issubset(words)

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
            raise RuntimeError(
                "litellm is required for executor execution; install project dependencies"
            )
        else:
            validate_provider_credentials(self.model_name, config.openrouter_api_key)
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt_payload},
            ]
            response = call_with_retry(
                completion,
                max_retries=config.provider_max_retries,
                sleep=time.sleep,
                kwargs={
                    "model": self.model_name,
                    "messages": messages,
                    "api_key": config.openrouter_api_key or None,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "max_tokens": config.max_tokens,
                    "timeout": config.provider_timeout_seconds,
                },
            )
            elapsed = time.time() - start_time
            raw_json = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            provider_cost = response_cost(response)
        
        if metrics_logger:
            metrics_logger.log_call(
                node="ExecutorAgent",
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_seconds=elapsed,
                cost_estimate_usd=provider_cost,
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
                if action_type in ("apply_patch", "patch"):
                    res = apply_patch(
                        file_path=action_dict["file_path"],
                        new_content=action_dict.get("patch") or action_dict.get("content"),
                        workspace_root=self.workspace_root,
                    )
                    tool_results.append({"action": action_dict, "result": res})
                    if not res.get("success", False):
                        all_tools_succeeded = False
                elif action_type in ("shell", "run_shell"):
                    res = run_shell(
                        command=action_dict["command"],
                        workspace_root=self.workspace_root,
                        timeout_seconds=action_dict.get("timeout") or 120,
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

        # Verify only facts this process can observe. LLM-authored
        # verification_results are claims, not trusted evidence.
        criteria_verification = []
        target_file_status = {}
        for target_file in task_spec.target_files:
            file_abs_path = os.path.join(self.workspace_root, target_file)
            exists = os.path.exists(file_abs_path)
            target_file_status[target_file] = exists
            criteria_verification.append({
                "criterion": f"Target file '{target_file}' exists",
                "passed": exists,
                "details": "File exists on disk" if exists else "File missing from workspace",
                "verification_method": "filesystem",
                "kind": "target_file",
            })

        acceptance_results = []
        for criterion in task_spec.acceptance_criteria:
            matched_file = next(
                (
                    target_file
                    for target_file in task_spec.target_files
                    if _is_file_existence_criterion(criterion, target_file)
                ),
                None,
            )
            if matched_file is not None:
                passed = target_file_status[matched_file]
                details = (
                    f"Verified '{matched_file}' exists on disk"
                    if passed
                    else f"Verified '{matched_file}' is missing"
                )
                method = "filesystem"
            elif _is_safe_action_criterion(criterion):
                passed = bool(tool_results) and all_tools_succeeded
                details = (
                    "Validated tool actions completed successfully"
                    if passed
                    else "No validated tool action completed successfully"
                )
                method = "tool_results"
            else:
                passed = False
                details = "No trusted behavioral verifier produced evidence"
                method = "unverified"

            result = {
                "criterion": criterion,
                "passed": passed,
                "details": details,
                "verification_method": method,
                "kind": "acceptance_criterion",
            }
            acceptance_results.append(result)
            criteria_verification.append(result)

        target_files_passed = all(target_file_status.values())
        criteria_passed = bool(acceptance_results) and all(
            result["passed"] for result in acceptance_results
        )
        verified_criteria = sum(
            1
            for result in acceptance_results
            if result["verification_method"] != "unverified"
        )
        passed_criteria = sum(1 for result in acceptance_results if result["passed"])
        criteria_pass_rate = (
            passed_criteria / len(acceptance_results) if acceptance_results else 0.0
        )

        overall_success = (
            all_tools_succeeded
            and target_files_passed
            and criteria_passed
            and ("error" not in execution_plan)
        )

        return {
            "success": overall_success,
            "execution_plan": execution_plan,
            "tool_results": tool_results,
            "verification_report": {
                "tools_succeeded": all_tools_succeeded,
                "criteria_passed": criteria_passed,
                "target_files_passed": target_files_passed,
                "criteria_pass_rate": criteria_pass_rate,
                "verified_criteria": verified_criteria,
                "total_criteria": len(acceptance_results),
                "reported_verification_results": execution_plan.get(
                    "verification_results", []
                ),
                "details": criteria_verification
            },
            "latency": elapsed,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens},
            "cost_usd": provider_cost,
        }
