import json
import time
from typing import Dict, Any, Optional, Tuple
from ..config import config
from ..schemas.task_spec import TaskSpec
from ..utils.metrics import MetricsLogger
from .provider import call_with_retry, response_cost, validate_provider_credentials
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
        model_name: str = config.planner_model,
        system_prompt: Optional[str] = None,
    ):
        self.model_name = model_name
        self.system_prompt = system_prompt or PLANNER_SYSTEM_PROMPT

    def plan(self, user_prompt: str, metrics_logger: MetricsLogger = None) -> Tuple[TaskSpec, Dict[str, Any]]:
        start_time = time.time()
        
        if completion is None:
            # Fallback mock for testing environment when litellm is not installed
            raw_json = json.dumps({
                "goal": f"Plan for: {user_prompt}",
                "target_files": ["main.py"],
                "acceptance_criteria": ["Implementation meets requirements"],
                "step_by_step_plan": ["Execute task"],
                "notes": "Generated in fallback mode (litellm package missing)",
            })
            elapsed = time.time() - start_time
            prompt_tokens, completion_tokens = 50, 50
            provider_cost = None
        else:
            validate_provider_credentials(self.model_name, config.openrouter_api_key)
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
                    "api_key": config.openrouter_api_key or None,
                    "temperature": 0.1,
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
                node="PlannerAgent",
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_seconds=elapsed,
                cost_estimate_usd=provider_cost,
            )
            
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
