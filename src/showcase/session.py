"""Live and recorded issue-to-fix showcase."""

from __future__ import annotations

import json
import os
import shutil
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agents.provider import resolve_api_key, validate_provider_credentials
from src.config import config
from src.orchestrator import DualLLMRouterOrchestrator
from src.showcase.report import (
    build_run_record,
    publish_success_rate,
    render_compare_html,
    render_html,
    render_markdown,
    render_terminal,
    write_run_folder,
)
from src.showcase.settings import USER_PROMPT, showcase_models

try:
    from litellm import completion
except ImportError:
    completion = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = PROJECT_ROOT / "examples" / "issue_to_fix"
RECORDED_DIR = FIXTURE_DIR / "recorded"
REPORTS_DIR = PROJECT_ROOT / "reports" / "showcase"
RATE_PATH = PROJECT_ROOT / "benchmark" / "published" / "showcase_success_rate.json"

_MISSING_KEY = (
    "FIREWORKS_API_KEY is not set, so this cannot be a live run.\n"
    "Create a key in your Fireworks account and export FIREWORKS_API_KEY.\n"
    "See https://app.fireworks.ai/account/api-keys"
)


def prepare_workspace(destination: Path) -> str:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    shutil.copy(FIXTURE_DIR / "billing.py", destination / "billing.py")
    shutil.copy(FIXTURE_DIR / "issue.md", destination / "issue.md")
    return (FIXTURE_DIR / "issue.md").read_text(encoding="utf-8")


def preflight_model(model: str) -> str | None:
    if completion is None:
        return "litellm is required for a live showcase."
    api_key = resolve_api_key(model)
    try:
        validate_provider_credentials(model, api_key)
    except RuntimeError as exc:
        return str(exc)
    try:
        completion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            api_key=api_key or None,
            max_tokens=1,
            temperature=0,
            timeout=30,
        )
    except Exception as exc:
        return (
            f"Model {model} is unavailable: {exc}. "
            "Override it with PLANNER_MODEL or EXECUTOR_MODEL "
            "(or SHOWCASE_PLANNER_MODEL / SHOWCASE_EXECUTOR_MODEL). "
            "There is no fallback."
        )
    return None


def run_pipeline(
    workspace: Path,
    planner_model: str,
    executor_model: str,
    issue_text: str,
) -> dict[str, Any]:
    previous_tokens = config.max_tokens
    if previous_tokens < 8192:
        config.max_tokens = 8192
    try:
        router = DualLLMRouterOrchestrator(
            planner_model=planner_model,
            executor_model=executor_model,
            workspace_root=str(workspace),
        )
        return router.run(
            USER_PROMPT,
            execute_tools=True,
            max_iterations=3,
            issue_text=issue_text,
        )
    finally:
        config.max_tokens = previous_tokens


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _open_report(path: Path, *, open_browser: bool) -> None:
    print(f"Report: {path}")
    if not open_browser or os.environ.get("CI"):
        return
    webbrowser.open(path.resolve().as_uri())


def _print_record(record: dict[str, Any]) -> None:
    print(render_terminal(record))
    warning = (record.get("sandbox") or {}).get("warning")
    if warning:
        print(warning, file=sys.stderr)
    append_step_summary(render_markdown(record))


def replay(*, compare: bool, open_browser: bool) -> int:
    print(_MISSING_KEY)
    json_name = "compare.json" if compare else "run.json"
    html_name = "compare_report.html" if compare else "report.html"
    json_path = RECORDED_DIR / json_name
    html_path = RECORDED_DIR / html_name
    if not json_path.exists() and not html_path.exists():
        print("No recorded run is committed yet at examples/issue_to_fix/recorded/.")
        print("A Fireworks key is required until five live runs have been captured.")
        return 1
    if json_path.exists():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if compare and "dual" in payload and "single" in payload:
            for side in (payload["dual"], payload["single"]):
                side["kind"] = "recorded"
                side["recorded_label"] = (
                    f"Recorded run from {side.get('finished_at', 'an earlier date')}, not live"
                )
            print(render_terminal(payload["dual"]))
            print()
            print(render_terminal(payload["single"]))
        else:
            payload["kind"] = "recorded"
            payload["recorded_label"] = (
                f"Recorded run from {payload.get('finished_at', 'an earlier date')}, not live"
            )
            _print_record(payload)
    if html_path.exists():
        _open_report(html_path, open_browser=open_browser)
        return 0
    folder = REPORTS_DIR / f"replay-{_timestamp()}"
    if json_path.exists():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if compare and "dual" in payload:
            html_text = render_compare_html(payload["dual"], payload["single"])
        else:
            payload["kind"] = "recorded"
            payload["recorded_label"] = (
                f"Recorded run from {payload.get('finished_at', 'an earlier date')}, not live"
            )
            html_text = render_html(payload)
        write_run_folder(folder, payload if not compare else payload, html_text)
        _open_report(folder / "report.html", open_browser=open_browser)
    return 0


def run_showcase(*, compare: bool, open_browser: bool, publish_rate: bool) -> int:
    if not config.fireworks_api_key:
        return replay(compare=compare, open_browser=open_browser)

    planner_model, executor_model = showcase_models()
    models = {planner_model}
    if compare:
        models.add(executor_model)
    else:
        models.add(executor_model)
    for model in models:
        error = preflight_model(model)
        if error:
            print(error, file=sys.stderr)
            return 1

    folder = REPORTS_DIR / _timestamp()
    if compare:
        dual_workspace = folder / "dual" / "workspace"
        single_workspace = folder / "single" / "workspace"
        dual_issue = prepare_workspace(dual_workspace)
        single_issue = prepare_workspace(single_workspace)
        dual_pipeline = run_pipeline(dual_workspace, planner_model, executor_model, dual_issue)
        single_pipeline = run_pipeline(
            single_workspace, executor_model, executor_model, single_issue
        )
        dual = build_run_record(
            dual_pipeline,
            models={"planner": planner_model, "executor": executor_model},
        )
        single = build_run_record(
            single_pipeline,
            models={"planner": executor_model, "executor": executor_model},
        )
        _print_record(dual)
        print()
        _print_record(single)
        html_text = render_compare_html(dual, single)
        record = {"kind": "compare", "dual": dual, "single": single}
        write_run_folder(folder, record, html_text)
    else:
        workspace = folder / "workspace"
        issue_text = prepare_workspace(workspace)
        pipeline = run_pipeline(workspace, planner_model, executor_model, issue_text)
        record = build_run_record(
            pipeline,
            models={"planner": planner_model, "executor": executor_model},
        )
        _print_record(record)
        write_run_folder(folder, record, render_html(record))
        if publish_rate:
            publish_success_rate(record, RATE_PATH)
    _open_report(folder / "report.html", open_browser=open_browser)
    return 0


def append_step_summary(markdown: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    with open(summary, "a", encoding="utf-8") as handle:
        handle.write(markdown)
        if not markdown.endswith("\n"):
            handle.write("\n")
