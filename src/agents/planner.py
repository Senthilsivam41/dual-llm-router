import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from ..config import config
from ..schemas.task_spec import TaskSpec
from ..utils.metrics import MetricsLogger
from .provider import (
    call_with_retry,
    message_text,
    resolve_api_key,
    response_cost,
    response_format_for,
    reasoning_effort_for,
    validate_provider_credentials,
)
from prompts.hermes.base import HERMES_SYSTEM_PROMPT

try:
    from litellm import completion
except ImportError:
    completion = None

# Back-compat alias; canonical prompt lives in prompts/hermes/base.py
PLANNER_SYSTEM_PROMPT = HERMES_SYSTEM_PROMPT

class PlannerAgent:
    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.model_name = model_name or config.planner_model
        self.system_prompt = system_prompt or PLANNER_SYSTEM_PROMPT

    def plan(self, user_prompt: str, metrics_logger: MetricsLogger = None) -> Tuple[TaskSpec, Dict[str, Any]]:
        start_time = time.time()
        
        if completion is None:
            raise RuntimeError(
                "litellm is required for planner execution; install project dependencies"
            )
        else:
            api_key = resolve_api_key(self.model_name)
            validate_provider_credentials(self.model_name, api_key)
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = call_with_retry(
                completion,
                max_retries=config.provider_max_retries,
                sleep=time.sleep,
                kwargs={
                    "model": self.model_name,
                    "messages": messages,
                    "api_key": api_key or None,
                    "temperature": 0.1,
                    "response_format": response_format_for(self.model_name),
                    "reasoning_effort": reasoning_effort_for(self.model_name),
                    "max_tokens": config.max_tokens,
                    "timeout": config.provider_timeout_seconds,
                },
            )
            elapsed = time.time() - start_time
            raw_json = message_text(response.choices[0].message)
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            provider_cost = response_cost(response)
        
        if metrics_logger:
            metrics_logger.log_call(
                node="PlannerAgent",
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_seconds=elapsed,
                cost_estimate_usd=provider_cost,
            )
            
        if not raw_json.strip():
            finish = getattr(response.choices[0], "finish_reason", None)
            raise ValueError(f"Model returned no content (finish_reason={finish}).")

        cleaned_json = raw_json.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(cleaned_json)
            task_spec = TaskSpec(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse TaskSpec from LLM response: {e}. Raw response: {raw_json}") from e
        
        return task_spec, {
            "raw_response": raw_json,
            "latency": elapsed,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens},
            "cost_usd": provider_cost,
        }


def workspace_listing(workspace: str) -> str:
    root = Path(workspace)
    if not root.exists():
        return "(no files)"
    names = [
        str(path.relative_to(root))
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]
    return "\n".join(f"- {name}" for name in names) or "(no files)"


def build_planner_user_message(
    user_prompt: str,
    workspace: str,
    issue_text: Optional[str] = None,
    rejection: Optional[str] = None,
) -> str:
    """Give the planner the bug report, the file list, and a prior validation error."""
    parts = [
        user_prompt.strip(),
        "Workspace files:\n" + workspace_listing(workspace),
    ]
    if issue_text:
        parts.append("Bug report (issue.md):\n" + issue_text.strip())
    if rejection:
        parts.append(
            "The previous TaskSpec was rejected:\n"
            + rejection
            + "\nReturn a corrected TaskSpec JSON object."
        )
    return "\n\n".join(parts)
