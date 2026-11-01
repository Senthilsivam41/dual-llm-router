"""Run executor-written pytest in a restricted subprocess, or Docker when it can."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

_PYTEST_TIMEOUT_SECONDS = 60
_SUBPROCESS_WARNING = (
    "Sandbox: restricted subprocess. Generated tests can still reach the network "
    "and read files this user can read."
)


@dataclass(frozen=True)
class PytestOutcome:
    returncode: int | None
    output: str
    junit_xml: str
    sandbox: str
    warning: str | None
    error: str | None = None


def passed_test_names(junit_xml: str) -> set[str]:
    if not junit_xml.strip():
        return set()
    try:
        root = ET.fromstring(junit_xml)
    except ET.ParseError:
        return set()
    names: set[str] = set()
    for case in root.iter("testcase"):
        failed = any(child.tag in {"failure", "error", "skipped"} for child in list(case))
        if failed:
            continue
        name = case.get("name") or ""
        names.add(name.split("[", 1)[0])
    return names


def select_sandbox() -> tuple[str, str | None]:
    """Pick docker only when it is requested or the image can import pytest."""
    forced = os.environ.get("SHOWCASE_SANDBOX", "auto").strip().lower()
    if forced == "subprocess":
        return "subprocess", _SUBPROCESS_WARNING
    if forced == "docker":
        return "docker", None
    if _docker_can_import_pytest():
        return "docker", None
    return "subprocess", _SUBPROCESS_WARNING


def run_pytest(workspace: str) -> PytestOutcome:
    sandbox, warning = select_sandbox()
    if sandbox == "docker":
        return _run_docker(workspace)
    return _run_subprocess(workspace, warning)


def _restricted_env(home: Path) -> dict[str, str]:
    python_dir = os.path.dirname(sys.executable)
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep) if path else []
    if python_dir and python_dir not in parts:
        path = python_dir + (os.pathsep + path if path else "")
    return {
        "PATH": path,
        "HOME": str(home),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }


def _copy_workspace(workspace: str, destination: Path) -> None:
    source = Path(workspace)
    if not source.exists():
        destination.mkdir(parents=True, exist_ok=True)
        return
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )


def _run_subprocess(workspace: str, warning: str | None) -> PytestOutcome:
    with tempfile.TemporaryDirectory(prefix="issue-to-fix-") as temp:
        temp_path = Path(temp)
        work = temp_path / "work"
        home = temp_path / "home"
        home.mkdir()
        _copy_workspace(workspace, work)
        junit_path = temp_path / "junit.xml"
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(work),
                    "--rootdir",
                    str(work),
                    "--noconftest",
                    "--junitxml",
                    str(junit_path),
                    "-p",
                    "no:cacheprovider",
                    "-q",
                ],
                cwd=str(work),
                env=_restricted_env(home),
                capture_output=True,
                text=True,
                timeout=_PYTEST_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            output = f"{stdout}\n{stderr}\nCommand timed out after {_PYTEST_TIMEOUT_SECONDS}s"
            return PytestOutcome(
                returncode=None,
                output=output.strip(),
                junit_xml="",
                sandbox="subprocess",
                warning=warning,
                error=f"pytest timed out after {_PYTEST_TIMEOUT_SECONDS}s",
            )
        junit_xml = junit_path.read_text(encoding="utf-8") if junit_path.exists() else ""
        output = f"{completed.stdout}{completed.stderr}".strip()
        return PytestOutcome(
            returncode=completed.returncode,
            output=output,
            junit_xml=junit_xml,
            sandbox="subprocess",
            warning=warning,
            error=None if completed.returncode == 0 else f"pytest exited {completed.returncode}",
        )


def _docker_image() -> str:
    return os.environ.get("SHOWCASE_DOCKER_IMAGE", "python:3.11-slim")


def _docker_can_import_pytest() -> bool:
    cached = getattr(_docker_can_import_pytest, "cached", None)
    if cached is not None:
        return bool(cached)
    ready = False
    if shutil.which("docker"):
        try:
            probe = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    _docker_image(),
                    "python",
                    "-c",
                    "import pytest",
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            ready = probe.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ready = False
    setattr(_docker_can_import_pytest, "cached", ready)
    return ready


def _run_docker(workspace: str) -> PytestOutcome:
    with tempfile.TemporaryDirectory(prefix="issue-to-fix-docker-") as temp:
        temp_path = Path(temp)
        work = temp_path / "work"
        junit_dir = temp_path / "junit"
        junit_dir.mkdir()
        _copy_workspace(workspace, work)
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{work}:/work:ro",
            "-v",
            f"{junit_dir}:/junit",
            "-w",
            "/work",
            "-e",
            "HOME=/tmp",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            _docker_image(),
            "python",
            "-m",
            "pytest",
            "--rootdir",
            "/work",
            "--noconftest",
            "--junitxml",
            "/junit/results.xml",
            "-p",
            "no:cacheprovider",
            "-q",
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=_PYTEST_TIMEOUT_SECONDS + 15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return PytestOutcome(
                returncode=None,
                output=str(exc),
                junit_xml="",
                sandbox="docker",
                warning=None,
                error=str(exc),
            )
        junit_path = junit_dir / "results.xml"
        junit_xml = junit_path.read_text(encoding="utf-8") if junit_path.exists() else ""
        output = f"{completed.stdout}{completed.stderr}".strip()
        return PytestOutcome(
            returncode=completed.returncode,
            output=output,
            junit_xml=junit_xml,
            sandbox="docker",
            warning=None,
            error=None if completed.returncode == 0 else f"pytest exited {completed.returncode}",
        )
