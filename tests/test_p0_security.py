import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from src.agents.executor import ExecutorAgent
from src.schemas.task_spec import TaskSpec
from src.tools.action_schemas import validate_action
from src.tools.patch_tool import apply_patch
from src.tools.shell_tool import run_shell


def completion_response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(payload)),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10),
        model="test-model",
        id="test-completion",
    )


def task_spec(*, target_files: list[str] | None = None) -> TaskSpec:
    return TaskSpec(
        goal="Exercise one validated tool action",
        target_files=target_files or [],
        acceptance_criteria=["The requested action is executed safely"],
        step_by_step_plan=["Execute the action"],
    )


def test_apply_patch_rejects_parent_directory_traversal(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = apply_patch("../escaped.txt", "unsafe", str(workspace))

    assert result["success"] is False
    assert not (tmp_path / "escaped.txt").exists()


def test_apply_patch_rejects_absolute_paths(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "escaped.txt"

    result = apply_patch(str(outside), "unsafe", str(workspace))

    assert result["success"] is False
    assert not outside.exists()


def test_apply_patch_rejects_symlink_escape(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / "link").symlink_to(outside, target_is_directory=True)

    result = apply_patch("link/escaped.txt", "unsafe", str(workspace))

    assert result["success"] is False
    assert not (outside / "escaped.txt").exists()


def test_run_shell_cannot_write_above_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = run_shell("touch ../escaped.txt", str(workspace))

    assert result["success"] is False
    assert not (tmp_path / "escaped.txt").exists()


def test_run_shell_cannot_read_above_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("outside-workspace-secret", encoding="utf-8")

    result = run_shell("cat ../secret.txt", str(workspace))

    assert result["success"] is False
    assert "outside-workspace-secret" not in result.get("stdout", "")


@pytest.mark.parametrize(
    "action",
    [
        {},
        {"type": "unknown", "command": "echo unsafe"},
        {"type": "apply_patch", "file_path": "/tmp/escaped", "content": "unsafe"},
        {"type": "apply_patch", "file_path": "missing-content.txt"},
    ],
)
def test_action_validation_rejects_malformed_or_unsafe_actions(action):
    with pytest.raises(ValueError):
        validate_action(action)


def test_action_batch_is_validated_before_any_action_executes(tmp_path):
    actions = [
        {"type": "apply_patch", "file_path": "first.txt", "content": "created"},
        {"type": "unknown", "command": "echo unsafe"},
    ]
    response = completion_response({"actions": actions})

    with patch("src.agents.executor.completion", Mock(return_value=response)):
        result = ExecutorAgent(workspace_root=str(tmp_path)).execute(task_spec())

    assert result["success"] is False
    assert not (tmp_path / "first.txt").exists()


def test_executor_dispatches_a_valid_shell_action(tmp_path):
    response = completion_response(
        {"actions": [{"type": "shell", "command": "touch marker.txt"}]}
    )

    with patch("src.agents.executor.completion", Mock(return_value=response)):
        result = ExecutorAgent(workspace_root=str(tmp_path)).execute(task_spec())

    assert result["success"] is True
    assert (tmp_path / "marker.txt").exists()
    assert result["tool_results"][0]["result"]["success"] is True


def test_executor_fails_closed_for_valid_but_unimplemented_action(tmp_path):
    response = completion_response(
        {"actions": [{"type": "read", "file_path": "source.txt"}]}
    )
    (tmp_path / "source.txt").write_text("content", encoding="utf-8")

    with patch("src.agents.executor.completion", Mock(return_value=response)):
        result = ExecutorAgent(workspace_root=str(tmp_path)).execute(task_spec())

    assert result["success"] is False
    assert result["tool_results"]
    assert "unsupported" in result["tool_results"][0]["result"]["error"].lower()
