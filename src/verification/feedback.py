"""Feedback handed to the executor on the next attempt. The plan stays fixed."""

from __future__ import annotations

from pathlib import Path

_PYTEST_LIMIT = 2000
_FILE_LIMIT = 8000
_SNAPSHOT_LIMIT = 12000


def workspace_snapshot(workspace: str, limit: int = _SNAPSHOT_LIMIT) -> str:
    root = Path(workspace)
    if not root.exists():
        return "(workspace is empty)"
    chunks: list[str] = []
    used = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix not in {".py", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > _FILE_LIMIT:
            text = text[:_FILE_LIMIT] + "\n...[truncated]"
        block = f"----- {path.relative_to(root)} -----\n{text}"
        if used + len(block) > limit:
            chunks.append("...[further files omitted]")
            break
        chunks.append(block)
        used += len(block)
    return "\n".join(chunks) if chunks else "(workspace is empty)"


def target_file_context(workspace: str, target_files: list[str], limit: int = _FILE_LIMIT) -> str:
    root = Path(workspace)
    chunks: list[str] = []
    used = 0
    for name in target_files:
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > limit:
            text = text[:limit] + "\n...[truncated]"
        block = f"----- {name} -----\n{text}"
        if used + len(block) > limit * 3:
            break
        chunks.append(block)
        used += len(block)
    return "\n".join(chunks)


def build_executor_feedback(workspace: str, verification: dict) -> str:
    pytest_output = str((verification.get("pytest") or {}).get("output") or "")[:_PYTEST_LIMIT]
    unmatched = verification.get("unmatched") or []
    unmatched_text = "\n".join(f"- {item}" for item in unmatched) or "- (none)"
    return (
        "Pytest output:\n"
        f"{pytest_output or '(no pytest output)'}\n\n"
        "Checks whose expected value was not found in a passing assertion:\n"
        f"{unmatched_text}\n\n"
        "Current workspace files:\n"
        f"{workspace_snapshot(workspace)}"
    )
