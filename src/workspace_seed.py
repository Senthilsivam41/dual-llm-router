"""Write benchmark and showcase seed files under their real paths."""

from __future__ import annotations

import re
from pathlib import Path

_SEED_NAME = re.compile(r"^#\s*([A-Za-z0-9_.-]+\.py)\s*$")


def filename_from_seed_comment(seed_code: str) -> str:
    """Use a leading `# module.py` comment as the filename.

    Older tasks stored that name as a comment and were always written to seed.py.
    """
    first = seed_code.splitlines()[0].strip() if seed_code else ""
    match = _SEED_NAME.match(first)
    if match is None:
        return "seed.py"
    name = match.group(1)
    if name.startswith(".") or "/" in name or "\\" in name:
        return "seed.py"
    return name


def write_seed_files(workspace: Path, seed_files: dict[str, str]) -> None:
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in seed_files.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe seed path: {relative}")
        destination = (root / path).resolve()
        if destination != root and root not in destination.parents:
            raise ValueError(f"Unsafe seed path: {relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def write_legacy_seed(workspace: Path, seed_code: str) -> str:
    name = filename_from_seed_comment(seed_code)
    destination = workspace / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(seed_code, encoding="utf-8")
    return name
