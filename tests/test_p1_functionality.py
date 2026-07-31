import json
import tomllib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from src.agents.executor import ExecutorAgent
from src.agents.planner import PlannerAgent
from src.config import config
from src.orchestrator import DualLLMRouterOrchestrator
from src.schemas.task_spec import TaskSpec
from src.utils.metrics import MetricsLogger


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def completion_response(
    payload: dict,
    *,
    prompt_tokens: int = 10,
    completion_tokens: int = 10,
    response_cost: float | None = None,
) -> SimpleNamespace:
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(payload)),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
        model="test-model",
        id="test-completion",
    )
    response._hidden_params = (
        {"response_cost": response_cost} if response_cost is not None else {}
    )
    return response


def task_spec(*, target_files: list[str] | None = None) -> TaskSpec:
    return TaskSpec(
        goal="Implement a verifiable change",
        target_files=target_files or [],
        acceptance_criteria=["The requested behavior is verified"],
        step_by_step_plan=["Implement", "Verify"],
    )


def planner_response() -> SimpleNamespace:
    return completion_response(
        {
            "goal": "Implement a verifiable change",
            "target_files": ["result.py"],
            "acceptance_criteria": ["Tests pass"],
            "step_by_step_plan": ["Implement", "Run tests"],
        }
    )


def test_orchestrator_retries_failed_execution_up_to_max_iterations(tmp_path):
    orchestrator = DualLLMRouterOrchestrator(workspace_root=str(tmp_path))
    spec = task_spec()
    failed = {"success": False, "verification_report": {"criteria_passed": False}}
    completed = {"success": True, "verification_report": {"criteria_passed": True}}

    with (
        patch.object(orchestrator.planner, "plan", return_value=(spec, {})),
        patch.object(orchestrator.executor, "execute", side_effect=[failed, completed])
        as execute,
    ):
        result = orchestrator.run("Implement the change", max_iterations=2)

    assert result["status"] == "completed"
    assert execute.call_count == 2


def test_orchestrator_stops_after_max_iterations(tmp_path):
    orchestrator = DualLLMRouterOrchestrator(workspace_root=str(tmp_path))
    spec = task_spec()
    failed = {"success": False, "verification_report": {"criteria_passed": False}}

    with (
        patch.object(orchestrator.planner, "plan", return_value=(spec, {})),
        patch.object(orchestrator.executor, "execute", return_value=failed) as execute,
    ):
        result = orchestrator.run("Implement the change", max_iterations=3)

    assert result["status"] == "failed"
    assert execute.call_count == 3


def test_existing_target_file_does_not_satisfy_behavioral_acceptance_criteria(
    tmp_path,
):
    (tmp_path / "result.py").write_text("def answer(): return 0\n", encoding="utf-8")
    response = completion_response(
        {
            "actions": [],
            "verification_results": ["No behavioral verification was performed"],
        }
    )
    spec = TaskSpec(
        goal="Return the expected answer",
        target_files=["result.py"],
        acceptance_criteria=["answer() returns 42"],
        step_by_step_plan=["Implement answer", "Run a behavioral check"],
    )

    with patch("src.agents.executor.completion", Mock(return_value=response)):
        result = ExecutorAgent(workspace_root=str(tmp_path)).execute(spec)

    assert result["success"] is False
    assert result["verification_report"]["criteria_passed"] is False


def test_openrouter_planner_fails_fast_without_api_key(monkeypatch):
    provider = Mock(return_value=planner_response())
    monkeypatch.setattr(config, "openrouter_api_key", "")

    with (
        patch("src.agents.planner.completion", provider),
        pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"),
    ):
        PlannerAgent(model_name="openrouter/test-model").plan("Plan this change")

    provider.assert_not_called()


def test_planner_passes_configured_max_tokens_to_provider(monkeypatch):
    provider = Mock(return_value=planner_response())
    monkeypatch.setattr(config, "openrouter_api_key", "test-key")
    monkeypatch.setattr(config, "max_tokens", 1234)

    with patch("src.agents.planner.completion", provider):
        PlannerAgent(model_name="openrouter/test-model").plan("Plan this change")

    assert provider.call_args.kwargs["max_tokens"] == 1234


def test_planner_sets_a_finite_provider_timeout(monkeypatch):
    provider = Mock(return_value=planner_response())
    monkeypatch.setattr(config, "openrouter_api_key", "test-key")

    with patch("src.agents.planner.completion", provider):
        PlannerAgent(model_name="openrouter/test-model").plan("Plan this change")

    timeout = provider.call_args.kwargs["timeout"]
    assert 0 < timeout <= 120


def test_planner_retries_transient_provider_timeout(monkeypatch):
    provider = Mock(side_effect=[TimeoutError("temporary"), planner_response()])
    monkeypatch.setattr(config, "openrouter_api_key", "test-key")

    with (
        patch("src.agents.planner.completion", provider),
        patch("src.agents.planner.time.sleep"),
    ):
        spec, _ = PlannerAgent(model_name="openrouter/test-model").plan(
            "Plan this change"
        )

    assert spec.goal == "Implement a verifiable change"
    assert provider.call_count == 2


def test_metrics_are_scoped_to_each_orchestrator_run(tmp_path):
    orchestrator = DualLLMRouterOrchestrator(workspace_root=str(tmp_path))
    spec = task_spec()

    def plan(*, metrics_logger, **_):
        metrics_logger.log_call("planner", "test", 10, 10, 0.1)
        return spec, {}

    def execute(*, metrics_logger, **_):
        metrics_logger.log_call("executor", "test", 10, 10, 0.1)
        return {"success": True}

    with (
        patch.object(orchestrator.planner, "plan", side_effect=plan),
        patch.object(orchestrator.executor, "execute", side_effect=execute),
    ):
        first = orchestrator.run("First run")
        second = orchestrator.run("Second run")

    assert first["metrics"]["total_calls"] == 2
    assert second["metrics"]["total_calls"] == 2


def test_provider_reported_cost_is_used_in_metrics(monkeypatch):
    provider = Mock(
        return_value=completion_response(
            {
                "goal": "Costed plan",
                "target_files": [],
                "acceptance_criteria": ["Plan exists"],
                "step_by_step_plan": ["Plan"],
            },
            response_cost=0.123456,
        )
    )
    logger = MetricsLogger()
    monkeypatch.setattr(config, "openrouter_api_key", "test-key")

    with patch("src.agents.planner.completion", provider):
        PlannerAgent(model_name="openrouter/test-model").plan(
            "Plan this change", metrics_logger=logger
        )

    assert logger.summary()["total_cost_usd"] == pytest.approx(0.123456)


def test_pytest_configuration_excludes_generated_workspace():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    pytest_options = pyproject["tool"]["pytest"]["ini_options"]

    assert "workspace" in pytest_options.get("norecursedirs", [])
