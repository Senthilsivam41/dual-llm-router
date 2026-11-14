import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals.evolution_engine import EvolutionEngine
from src.agents import executor, planner
from src.agents.provider import completion_options
from src.config import config
from src.reconciliation import fixtures
from src.reconciliation.report import PRICE_SNAPSHOT, paired_effect, summarize
from src.reconciliation.study import EXAMPLE, TrialRunner, make_record, run_study, select_guidance
from src.reconciliation.verifier import CandidateError, DockerRunner, SandboxError, compare_output, verify
from src.schemas.task_spec import TaskSpec
from src.showcase.settings import PINNED_EXECUTOR, PINNED_PLANNER

PROGRAM = """import csv
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal

def load(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def cents(value):
    return int(Decimal(value) * 100)

invoices = {row["invoice_id"]: row for row in load(sys.argv[1])}
payments = load(sys.argv[2])
counts = Counter(row["payment_id"] for row in payments)
paid = defaultdict(int)
exceptions = []
for index, row in enumerate(payments, 1):
    invoice = invoices.get(row["invoice_id"])
    reason = None
    if counts[row["payment_id"]] > 1:
        reason = "duplicate_payment_id"
    elif invoice is None:
        reason = "unknown_invoice"
    elif invoice["currency"] != row["currency"]:
        reason = "currency_mismatch"
    if reason:
        exceptions.append(dict(row=index, payment_id=row["payment_id"], reason=reason))
    else:
        paid[row["invoice_id"]] += cents(row["amount"])

summaries = []
for key, invoice in sorted(invoices.items()):
    invoiced = cents(invoice["amount"])
    total = paid[key]
    status = ("unpaid" if total == 0 else "partial" if total < invoiced
              else "paid" if total == invoiced else "overpaid")
    summaries.append(dict(invoice_id=key, currency=invoice["currency"],
                          invoiced_cents=invoiced, paid_cents=total, status=status))
print(json.dumps(dict(invoices=summaries, exceptions=exceptions)))
"""
WRONG = PROGRAM.replace('paid[row["invoice_id"]] += cents(row["amount"])',
                        'paid[row["invoice_id"]] = cents(row["amount"])')
PLAN = {
    "goal": "Produce a verified reconciliation CLI",
    "target_files": ["reconcile.py"],
    "acceptance_criteria": ["Summaries and exceptions follow the policy"],
    "step_by_step_plan": ["Validate payment rows", "Aggregate accepted payments in cents", "Emit sorted JSON"],
}
MODELS = {"planner": "scripted/planner", "executor": "scripted/executor"}


def _trusted_runner(tmp_path):
    def run(program, probe):
        # Only the fixed test programs execute in this local test subprocess.
        assert program in (PROGRAM.encode(), WRONG.encode())
        directory = tmp_path / "trusted"
        directory.mkdir(exist_ok=True)
        (directory / "reconcile.py").write_bytes(program)
        (directory / "invoices.csv").write_text(probe.invoices)
        (directory / "payments.csv").write_text(probe.payments)
        return subprocess.check_output(
            [sys.executable, "-I", "-B", "reconcile.py", "invoices.csv", "payments.csv"],
            cwd=directory,
            timeout=5,
        )
    return run


def _response(payload):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10),
    )


def scripted_demo(tmp_path, monkeypatch, *, candidate=None):
    prompts = []
    monkeypatch.setattr(config, "openrouter_api_key", "")
    monkeypatch.setattr(planner, "completion", lambda **kwargs: _response(PLAN))

    def complete(messages, **kwargs):
        prompts.append(messages)
        correct = "Verifier diagnostics" in messages[-1]["content"] or messages[0]["content"] == candidate
        return _response({
            "actions": [{"type": "apply_patch", "file_path": "reconcile.py", "content": PROGRAM if correct else WRONG}],
        })

    monkeypatch.setattr(executor, "completion", complete)
    policy = (EXAMPLE / "policy.md").read_text()
    case = fixtures.scenarios("holdout")[0]
    study = make_record(MODELS, policy, demo=True, mode="scripted")
    runner = TrialRunner(MODELS, _trusted_runner(tmp_path), policy)
    trial = runner.run(tmp_path / "runs", case, 1, candidate=candidate)
    study.update(status="complete", trials=[trial])
    return study, prompts, case


def test_fixture_protocol_and_reference(tmp_path):
    run = _trusted_runner(tmp_path)
    development = fixtures.scenarios("development")
    holdout = fixtures.scenarios("holdout")
    assert len(development) == 12 and len(holdout) == 32
    assert {case.id for case in development}.isdisjoint(case.id for case in holdout)
    assert {family: sum(case.family == family for case in holdout) for family in fixtures.FAMILIES} == {
        family: 8 for family in fixtures.FAMILIES
    }
    for case in development + holdout:
        for probe in (case.diagnostic, *case.private):
            assert compare_output(run(PROGRAM.encode(), probe), probe.expected)["criteria_passed"]


def test_verifier_rejects_incorrect_totals_duplicate_rows_and_malformed_json():
    expected = fixtures.scenarios("holdout")[0].diagnostic.expected
    changed = json.loads(json.dumps(expected))
    changed["invoices"][0]["paid_cents"] += 1
    report = compare_output(json.dumps(changed).encode(), expected)
    assert report["failure_codes"] == ["paid_cents"]
    assert report["diagnostics"][0]["row"] == expected["invoices"][0]["invoice_id"]
    changed["invoices"].insert(0, changed["invoices"][0])
    assert "duplicate_output_row" in compare_output(json.dumps(changed).encode(), expected)["failure_codes"]
    assert compare_output(b"bad JSON", expected)["failure_codes"] == ["malformed_output"]
    assert compare_output(b'{"invoices":[],"invoices":[],"exceptions":[]}', expected)["failure_codes"] == [
        "malformed_output"
    ]


def test_timeout_is_a_candidate_failure_and_daemon_error_is_infrastructure(tmp_path, monkeypatch):
    monkeypatch.setattr("src.reconciliation.verifier.TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr("src.reconciliation.verifier.subprocess.run", lambda *args, **kwargs: None)
    with pytest.raises(CandidateError, match="timeout"):
        DockerRunner._collect([sys.executable, "-c", "import time; time.sleep(2)"], "unused")

    (tmp_path / "reconcile.py").write_text(PROGRAM)
    probe = fixtures.scenarios("development")[0].diagnostic

    def timeout(*_):
        raise CandidateError("timeout")

    def daemon(*_):
        raise SandboxError("daemon unavailable")

    assert verify(tmp_path, probe, timeout)["failure_codes"] == ["timeout"]
    with pytest.raises(SandboxError):
        verify(tmp_path, probe, daemon)


def test_paired_retry_uses_same_snapshot_and_keeps_private_probes_out(tmp_path, monkeypatch):
    study, prompts, case = scripted_demo(tmp_path, monkeypatch, candidate="Development-guided executor")
    trial = study["trials"][0]
    first, generic, diagnostics, candidate = (trial["executions"][arm] for arm in (
        "first", "generic", "diagnostics", "candidate"
    ))
    assert first["final_program_sha256"] == generic["initial_program_sha256"] == diagnostics["initial_program_sha256"]
    assert candidate["initial_program_sha256"] is None
    assert first["private_pass"] is False
    assert generic["private_pass"] is False
    assert diagnostics["private_pass"] is True
    assert candidate["private_pass"] is True
    assert len(generic["attempts"]) == 2 and len(diagnostics["attempts"]) == 1
    assert "paid_cents" in diagnostics["attempts"][0]["feedback"]
    assert "paid_cents" not in generic["attempts"][0]["feedback"]
    for probe in case.private:
        private_id = probe.expected["invoices"][0]["invoice_id"]
        assert all(private_id not in str(messages) for messages in prompts)
    summary = summarize(study)
    assert summary["attempted_study_calls"] == 6
    assert summary["effects"]["retry_feedback"]["delta_pp"] == 100
    assert summary["effects"]["prompt_feedback"]["pairs"] == 1


def test_independent_verdict_uses_verified_output_when_optional_tool_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(executor, "completion", lambda **_: _response({
        "actions": [
            {"type": "apply_patch", "file_path": "reconcile.py", "content": PROGRAM},
            {"type": "run_shell", "command": "python reconcile.py"},
        ],
    }))
    case = fixtures.scenarios("holdout")[0]
    router = TrialRunner(MODELS, _trusted_runner(tmp_path), "Policy")
    agent = router._router(tmp_path, case).executor
    result = agent.execute(TaskSpec(**PLAN))
    assert result["verification_report"]["tools_succeeded"] is False
    assert result["verification_report"]["failure_codes"] == []
    assert result["success"] is True


def test_guidance_is_selected_from_development_and_frozen_before_holdout(tmp_path, monkeypatch):
    base = fixtures.scenarios
    monkeypatch.setattr("src.reconciliation.study.scenarios", lambda split: base(split)[:2])
    record = make_record(MODELS, "Policy", demo=False, mode="scripted")
    prompts = []

    class Runner:
        def run(self, workspace, case, repetition, *, candidate=None, development=False):
            if development:
                assert candidate is None
                codes = ["paid_cents", "paid_cents", "ordering", "unknown_code"]
            else:
                assert (tmp_path / "evolution/.autoclaw/agents/genomes/laguna/v2.json").is_file()
                assert candidate and "Sum exact integer cents" in candidate
                assert "Sort summaries" in candidate
                prompts.append(candidate)
                codes = ["duplicate_payment_id"]
            return {
                "scenario": case.id, "family": case.family, "repetition": repetition,
                "arms": {"first": {"passed": False, "cost_usd": 0.0, "wall_seconds": 1.0}},
                "executions": {"first": {"diagnostic": {"failure_codes": codes}}},
            }

    run_study(tmp_path, record, Runner(), jobs=2, checkpoint=lambda _: None)
    assert select_guidance(record["development"]) == ({"ordering": 2, "paid_cents": 2}, ["ordering", "paid_cents"])
    assert len(prompts) == 4 and len(set(prompts)) == 1
    assert record["candidate"]["counts"] == {"ordering": 2, "paid_cents": 2}
    engine = EvolutionEngine(root=tmp_path / "evolution")
    assert engine.active_laguna == "laguna_v1"
    assert engine.lineage["edges"][0]["child"] == record["candidate"]["variant_id"]


def test_paired_effect_resamples_scenarios_and_omits_incomplete_pairs():
    rows = [
        {"scenario": name, "family": "mixed", "arms": {"a": {"passed": left}, "b": {"passed": right}}}
        for name, left, right in [
            ("one", False, True), ("one", False, True),
            ("two", False, True), ("two", False, True),
            ("three", True, None),
        ]
    ]
    effect = paired_effect(rows, "a", "b", resamples=100)
    assert effect["pairs"] == 4 and effect["scenarios"] == 2
    assert effect["ci95_pp"] == [100, 100]
    assert effect["verdict"] == "improved"
    assert effect["by_family"]["mixed"] == {"pairs": 4, "gains": 4, "regressions": 0}


def test_fireworks_reasoning_parameter_survives_litellm_adapter():
    from litellm import get_llm_provider
    from litellm.utils import get_optional_params

    for model in (PINNED_PLANNER, PINNED_EXECUTOR):
        name, provider, _, _ = get_llm_provider(model)
        assert get_optional_params(
            model=name, custom_llm_provider=provider, **completion_options(model),
        )["reasoning_effort"] == "low"


def test_report_estimates_zero_cost_calls_from_token_usage(tmp_path, monkeypatch):
    record, _, _ = scripted_demo(tmp_path, monkeypatch)
    trial = record["trials"][0]
    record["pricing"] = {"usd_per_million_tokens": PRICE_SNAPSHOT}
    for segment in [trial["planning"], *trial["executions"].values()]:
        for call in segment["model_calls"]:
            call["model"] = PINNED_PLANNER if call["node"] == "PlannerAgent" else PINNED_EXECUTOR
            call["cost_estimate_usd"] = 0.0
    diagnostics = summarize(record)["arms"]["diagnostics"]
    assert diagnostics["estimated_cost_calls"] == 3
    assert diagnostics["cost_per_verified_task_usd"] == pytest.approx(
        (10 * (0.30 + 1.20) + 20 * (0.15 + 0.50)) / 1_000_000
    )
