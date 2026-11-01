"""Issue-to-fix showcase: checks, verifier, seed files, and replay."""

import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from evals.benchmark_runner import BenchmarkTask, materialize_task_seed
from src.agents.executor import ExecutorAgent
from src.config import config
from src.orchestrator import DualLLMRouterOrchestrator
from src.schemas.task_spec import Check, TaskSpec
from src.showcase import session
from src.showcase.report import build_run_record, publish_success_rate, render_html, render_terminal
from src.showcase.settings import PINNED_EXECUTOR, PINNED_PLANNER, showcase_models
from src.verification.assertions import assertion_hits
from src.verification.checks import verify_checks
from src.verification.cross_check import planner_accuracy, validate_report_checks
from src.verification.runner import select_sandbox
from src.workspace_seed import filename_from_seed_comment, write_legacy_seed, write_seed_files

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "issue_to_fix"

FIXED_BILLING = '''from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")


def invoice_total(line_items, coupon="0", tax_rate="0.08"):
    subtotal = sum((Decimal(item) for item in line_items), Decimal("0"))
    discount = min(Decimal(coupon), subtotal)
    taxable = subtotal - discount
    total = taxable * (Decimal("1") + Decimal(tax_rate))
    return format(total.quantize(_CENT, rounding=ROUND_HALF_UP), "f")
'''

PASSING_TESTS = '''from billing import invoice_total


def test_coupon_before_tax():
    assert invoice_total(["100.00"], "10", "0.08") == "97.20"


def test_sum_then_round():
    assert invoice_total(["1.235", "1.235"], "0", "0") == "2.47"


def test_empty_invoice():
    assert invoice_total([], "0", "0") == "0.00"
'''

HONEST_FAILING_TESTS = '''from billing import invoice_total


def test_coupon_before_tax():
    assert invoice_total(["100.00"], "10", "0.08") == "97.20"
'''

DISHONEST_COMMENT = '''def test_mentions_the_number():
    # 97.20
    assert True, "97.20"
'''


def load_billing(path: Path):
    spec = importlib.util.spec_from_file_location("billing_fixture", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_checks() -> list[Check]:
    return [
        Check(
            id="AC1",
            source="report",
            description="coupon before tax",
            expected_value="97.20",
            planner_value="97.20",
            required=True,
        ),
        Check(
            id="AC2",
            source="report",
            description="sum then round",
            expected_value="2.47",
            planner_value="98.00",
            required=True,
        ),
        Check(
            id="AC3",
            source="edge",
            description="empty invoice",
            expected_value="0.00",
            planner_value="0.00",
            required=True,
            reason="an empty invoice charges nothing",
        ),
    ]


def sample_spec() -> TaskSpec:
    return TaskSpec(
        goal="Fix the invoice bug",
        target_files=["billing.py", "test_billing.py"],
        acceptance_criteria=["Expected amounts are charged"],
        step_by_step_plan=["Fix billing.py", "Add tests"],
        checks=sample_checks(),
    )


def test_fixture_charges_the_reported_wrong_amounts():
    billing = load_billing(FIXTURE / "billing.py")

    assert billing.invoice_total(["100.00"], "10", "0.08") == "98.00"
    assert billing.invoice_total(["1.235", "1.235"], "0", "0") == "2.48"


def test_report_checks_must_be_required_and_decimal():
    with pytest.raises(ValidationError):
        Check(
            id="AC1",
            source="report",
            description="coupon",
            expected_value="97.20",
            planner_value="97.20",
            required=False,
        )
    with pytest.raises(ValidationError):
        Check(
            id="AC1",
            source="report",
            description="coupon",
            expected_value="$97.20",
            planner_value="97.20",
            required=True,
        )


def test_checks_require_one_required_edge_case():
    with pytest.raises(ValidationError, match="edge-case"):
        TaskSpec(
            goal="Fix",
            target_files=["billing.py"],
            acceptance_criteria=["fixed"],
            step_by_step_plan=["fix"],
            checks=[
                Check(
                    id="AC1",
                    source="report",
                    description="coupon",
                    expected_value="97.20",
                    planner_value="97.20",
                    required=True,
                )
            ],
        )


def test_omitted_checks_keep_the_old_task_shape():
    spec = TaskSpec(
        goal="Create a file",
        acceptance_criteria=["file exists"],
        step_by_step_plan=["create it"],
    )

    assert spec.checks is None


def test_report_values_must_be_expected_amounts_from_the_issue():
    issue = (FIXTURE / "issue.md").read_text(encoding="utf-8")
    spec = sample_spec()

    assert validate_report_checks(spec, issue) is None
    spec.checks[0].expected_value = "97.2"
    assert validate_report_checks(spec, issue) is None

    spec.checks[0].expected_value = "98.00"
    error = validate_report_checks(spec, issue)
    assert error is not None
    assert "Charged" in error
    assert planner_accuracy(sample_checks()) == 0.5


def test_assertion_match_ignores_comments_messages_and_failing_tests():
    honest = assertion_hits(PASSING_TESTS, "test_billing.py")
    values = {hit.value for hit in honest if hit.function_name == "test_coupon_before_tax"}
    assert any(value == Decimal("97.20") for value in values)

    dishonest = assertion_hits(DISHONEST_COMMENT, "test_billing.py")
    assert dishonest == []


def test_failing_tests_do_not_verify_the_buggy_fixture(tmp_path):
    (tmp_path / "billing.py").write_text((FIXTURE / "billing.py").read_text(), encoding="utf-8")
    (tmp_path / "test_billing.py").write_text(HONEST_FAILING_TESTS, encoding="utf-8")

    report = verify_checks(str(tmp_path), sample_checks())

    assert report["criteria_passed"] is False
    assert "AC1" in " ".join(report["unmatched"])


def test_passing_assertions_verify_a_correct_fix(tmp_path):
    (tmp_path / "billing.py").write_text(FIXED_BILLING, encoding="utf-8")
    (tmp_path / "test_billing.py").write_text(PASSING_TESTS, encoding="utf-8")

    report = verify_checks(str(tmp_path), sample_checks())

    assert report["criteria_passed"] is True
    assert report["verified_criteria"] == 3
    assert report["pytest"]["sandbox"] == "subprocess"
    assert report["pytest"]["warning"]


def test_executor_is_verified_from_tests_not_its_own_claim(tmp_path):
    (tmp_path / "billing.py").write_text((FIXTURE / "billing.py").read_text(), encoding="utf-8")
    response_payload = {
        "summary": "fix the invoice",
        "actions": [
            {"type": "apply_patch", "file_path": "billing.py", "content": FIXED_BILLING},
            {"type": "apply_patch", "file_path": "test_billing.py", "content": PASSING_TESTS},
        ],
        "verification_results": ["I checked it mentally"],
    }
    response = Mock()
    response.choices = [Mock(message=Mock(content=json.dumps(response_payload)))]
    response.usage = Mock(prompt_tokens=5, completion_tokens=5)
    response._hidden_params = {}

    with patch("src.agents.executor.completion", Mock(return_value=response)) as provider:
        result = ExecutorAgent(model_name="test-model", workspace_root=str(tmp_path)).execute(
            sample_spec()
        )

    prompt = provider.call_args.kwargs["messages"][1]["content"]
    assert "97.20" in prompt
    assert "def invoice_total" in prompt
    assert result["success"] is True
    assert result["verification_report"]["criteria_passed"] is True


def test_planner_retries_once_when_checks_are_invalid(tmp_path):
    orchestrator = DualLLMRouterOrchestrator(workspace_root=str(tmp_path))
    spec = sample_spec()
    prompts = []

    def plan(*, user_prompt, metrics_logger=None):
        prompts.append(user_prompt)
        if len(prompts) == 1:
            raise ValueError("at least one edge-case check must be required")
        return spec, {}

    with (
        patch.object(orchestrator.planner, "plan", side_effect=plan),
        patch.object(
            orchestrator.executor,
            "execute",
            return_value={"success": True, "verification_report": {}},
        ),
    ):
        result = orchestrator.run(
            "Fix the invoice bug",
            issue_text=(FIXTURE / "issue.md").read_text(encoding="utf-8"),
        )

    assert result["status"] == "completed"
    assert result["planner_attempts"] == 2
    assert result["planner_accuracy"] == 0.5
    assert len(result["planner_disagreements"]) == 1
    assert "Expected: 97.20" in prompts[0]
    assert "Workspace files:" in prompts[0]
    assert "at least one edge-case check must be required" in prompts[1]


def test_planner_stops_after_the_second_validation_failure(tmp_path):
    orchestrator = DualLLMRouterOrchestrator(workspace_root=str(tmp_path))
    plan = Mock(side_effect=ValueError("bad checks"))

    with patch.object(orchestrator.planner, "plan", plan):
        result = orchestrator.run("Fix the invoice bug", issue_text="Expected: 97.20")

    assert result["status"] == "planning_failed"
    assert plan.call_count == 2


def test_provider_errors_are_not_retried_as_validation(tmp_path):
    orchestrator = DualLLMRouterOrchestrator(workspace_root=str(tmp_path))
    plan = Mock(side_effect=RuntimeError("provider down"))

    with patch.object(orchestrator.planner, "plan", plan):
        result = orchestrator.run("Fix the invoice bug", issue_text="Expected: 97.20")

    assert result["status"] == "planning_failed"
    assert plan.call_count == 1
    assert "provider down" in result["error"]


def test_executor_retry_receives_pytest_and_unmatched_checks(tmp_path):
    orchestrator = DualLLMRouterOrchestrator(workspace_root=str(tmp_path))
    failed = {
        "success": False,
        "verification_report": {
            "unmatched": ["AC1 (report, required=true) expected 97.20"],
            "pytest": {"output": "AssertionError: assert '98.00' == '97.20'"},
        },
    }
    succeeded = {"success": True, "verification_report": {"unmatched": [], "pytest": {}}}

    with (
        patch.object(orchestrator.planner, "plan", return_value=(sample_spec(), {})),
        patch.object(
            orchestrator.executor,
            "execute",
            side_effect=[failed, succeeded],
        ) as execute,
    ):
        result = orchestrator.run("Fix the invoice bug", max_iterations=3)

    assert result["status"] == "completed"
    assert execute.call_count == 2
    feedback = execute.call_args_list[1].kwargs["feedback"]
    assert "97.20" in feedback
    assert "AssertionError" in feedback
    assert execute.call_args_list[0].kwargs["feedback"] is None


def test_seed_files_keep_their_paths(tmp_path):
    write_seed_files(
        tmp_path,
        {"billing.py": "print('bill')\n", "notes/issue.md": "Expected: 1.00\n"},
    )
    legacy = tmp_path / "legacy"
    write_legacy_seed(legacy, "# legacy_calc.py\ndef total(x, y):\n    return x + y\n")

    assert (tmp_path / "billing.py").read_text(encoding="utf-8").startswith("print")
    assert (tmp_path / "notes" / "issue.md").exists()
    assert not (tmp_path / "seed.py").exists()
    assert filename_from_seed_comment("# legacy_calc.py\n") == "legacy_calc.py"
    assert (legacy / "legacy_calc.py").exists()
    assert not (legacy / "seed.py").exists()
    with pytest.raises(ValueError):
        write_seed_files(tmp_path, {"../escape.py": "nope"})


def test_benchmark_seed_map_replaces_seed_py(tmp_path):
    task = BenchmarkTask.from_dict(
        {
            "id": "medium_billing_coupon",
            "category": "medium",
            "spec": "fix",
            "acceptance_criteria": ["fixed"],
            "complexity_score": 0.4,
            "expected_cost": 0.01,
            "expected_time": 10,
            "seed_files": {"billing.py": "x = 1\n", "issue.md": "Expected: 97.20\n"},
            "max_iterations": 3,
        }
    )

    issue = materialize_task_seed(tmp_path, task)

    assert issue == "Expected: 97.20\n"
    assert (tmp_path / "billing.py").exists()
    assert not (tmp_path / "seed.py").exists()
    assert task.max_iterations == 3


def test_subprocess_sandbox_is_explicit(monkeypatch):
    monkeypatch.setenv("SHOWCASE_SANDBOX", "subprocess")

    sandbox, warning = select_sandbox()

    assert sandbox == "subprocess"
    assert warning is not None
    assert "network" in warning


def test_showcase_without_a_key_explains_and_replays(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(config, "fireworks_api_key", "")
    monkeypatch.setattr(session, "RECORDED_DIR", tmp_path)
    record = build_run_record(
        {
            "status": "completed",
            "executor_result": {"verification_report": {"checks": []}, "attempts": [{}]},
            "metrics": {"total_cost_usd": 0.002, "breakdown": []},
            "planner_accuracy": 1.0,
        },
        models={"planner": PINNED_PLANNER, "executor": PINNED_EXECUTOR},
        kind="live",
        success_rate={
            "verified": 4,
            "total": 5,
            "median_attempts": 2,
            "median_cost_usd": "0.002",
        },
    )
    (tmp_path / "run.json").write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "report.html").write_text(render_html(record), encoding="utf-8")

    code = session.run_showcase(compare=False, open_browser=False, publish_rate=False)
    captured = capsys.readouterr().out

    assert code == 0
    assert "FIREWORKS_API_KEY" in captured
    assert "not live" in captured
    assert "4 of 5" in captured


def test_showcase_without_a_key_or_recording_stops(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(config, "fireworks_api_key", "")
    monkeypatch.setattr(session, "RECORDED_DIR", tmp_path)

    code = session.run_showcase(compare=False, open_browser=False, publish_rate=False)

    assert code == 1
    assert "No recorded run" in capsys.readouterr().out


def test_pinned_models_ignore_the_repo_openrouter_defaults(monkeypatch):
    monkeypatch.delenv("SHOWCASE_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("SHOWCASE_EXECUTOR_MODEL", raising=False)
    monkeypatch.setenv("PLANNER_MODEL", "openrouter/nousresearch/hermes-4-70b")
    monkeypatch.setenv("EXECUTOR_MODEL", "openrouter/poolside/laguna-s-2.1")

    assert showcase_models() == (PINNED_PLANNER, PINNED_EXECUTOR)

    monkeypatch.setenv("SHOWCASE_EXECUTOR_MODEL", "fireworks_ai/custom-executor")
    assert showcase_models()[1] == "fireworks_ai/custom-executor"


def test_empty_executor_content_fails_without_raising(tmp_path):
    response = Mock()
    response.choices = [Mock(message=Mock(content=None), finish_reason="length")]
    response.usage = Mock(prompt_tokens=1, completion_tokens=1)
    response._hidden_params = {}
    spec = TaskSpec(
        goal="Run safe action",
        target_files=[],
        acceptance_criteria=["The requested action is executed safely"],
        step_by_step_plan=["Execute"],
    )

    with patch("src.agents.executor.completion", Mock(return_value=response)) as provider:
        result = ExecutorAgent(
            model_name="fireworks_ai/accounts/fireworks/models/glm-5p3-flash",
            workspace_root=str(tmp_path),
        ).execute(spec)

    assert result["success"] is False
    assert "no content" in result["execution_plan"]["error"]
    assert provider.call_args.kwargs["reasoning_effort"] == "low"


def test_recorded_runs_do_not_change_the_published_rate(tmp_path):
    record = build_run_record(
        {"status": "completed", "metrics": {}, "executor_result": {}},
        models={"planner": "p", "executor": "e"},
        kind="recorded",
    )
    path = tmp_path / "showcase_success_rate.json"

    publish_success_rate(record, path)

    assert not path.exists()
    assert "Recorded run, not live" in render_terminal(record)
