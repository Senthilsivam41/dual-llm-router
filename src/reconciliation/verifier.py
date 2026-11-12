"""Execute reconciliation code in Docker and compare its output on the host."""

from __future__ import annotations

import json
import os
import re
import selectors
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import uuid4

from .fixtures import Probe

IMAGE = "python:3.11-slim"
MAX_OUTPUT = 65_536
MAX_PROGRAM_BYTES = 65_536
TIMEOUT_SECONDS = 12
MAX_DIAGNOSTICS = 8
REASONS = {"duplicate_payment_id", "unknown_invoice", "currency_mismatch"}
STATUSES = {"unpaid", "partial", "paid", "overpaid"}
INVOICE_FIELDS = {"invoice_id": str, "currency": str, "invoiced_cents": int, "paid_cents": int, "status": str}
EXCEPTION_FIELDS = {"row": int, "payment_id": str, "reason": str}


class SandboxError(RuntimeError):
    """The verifier infrastructure could not run the candidate."""


class CandidateError(RuntimeError):
    """The candidate failed to produce a usable result."""


class DockerRunner:
    def __init__(self, image: str = IMAGE):
        self.image = image

    def preflight(self) -> str:
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.image, "--format", "{{.Id}}"],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SandboxError(f"Docker image check failed ({type(exc).__name__})") from exc
        image_id = result.stdout.strip()
        if result.returncode or not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
            raise SandboxError(f"Docker image {self.image} is unavailable. Check the daemon and pull the image.")
        self.image = image_id
        probe = Probe("invoice_id,currency,amount\n", "payment_id,invoice_id,currency,amount\n", {})
        try:
            if self(b'print("ready")\n', probe).strip() != b"ready":
                raise SandboxError("Docker reconciliation probe returned unexpected output")
        except CandidateError as exc:
            raise SandboxError(f"Docker reconciliation probe failed ({exc})") from exc
        return image_id

    def __call__(self, program: bytes, probe: Probe) -> bytes:
        with tempfile.TemporaryDirectory(prefix="reconcile-") as directory:
            mount = Path(directory) / "input"
            mount.mkdir(mode=0o755)
            for name, content in (
                ("reconcile.py", program),
                ("invoices.csv", probe.invoices.encode("utf-8")),
                ("payments.csv", probe.payments.encode("utf-8")),
            ):
                (mount / name).write_bytes(content)
                (mount / name).chmod(0o644)
            name = f"reconciliation-{uuid4().hex}"
            command = [
                "docker", "run", "--rm", "--pull=never", "--name", name,
                "--network=none", "--read-only", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--user=65534:65534",
                "--pids-limit=32", "--memory=128m", "--cpus=1", "--log-driver=none",
                "--mount", f"type=bind,src={mount},dst=/input,readonly",
                "--workdir=/input", self.image,
                "python", "-I", "-B", "reconcile.py", "invoices.csv", "payments.csv",
            ]
            return self._collect(command, name)

    @staticmethod
    def _collect(command: list[str], name: str) -> bytes:
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise SandboxError(f"Docker command unavailable ({type(exc).__name__})") from exc
        assert process.stdout is not None
        deadline = time.monotonic() + TIMEOUT_SECONDS
        output = bytearray()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.select(max(0, deadline - time.monotonic())):
                    chunk = os.read(process.stdout.fileno(), 8192)
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > MAX_OUTPUT:
                        raise CandidateError("output_limit")
                else:
                    raise CandidateError("timeout")
            try:
                status = process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as exc:
                raise CandidateError("timeout") from exc
            if status in {125, 126, 127}:
                raise SandboxError(f"Docker could not start the verifier (exit {status})")
            if status:
                raise CandidateError("program_exit")
            return bytes(output)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
                try:
                    subprocess.run(
                        ["docker", "rm", "-f", name], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=5, check=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pass
            process.stdout.close()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("duplicate JSON key")
    return value


def _safe(value: Any) -> Any:
    if type(value) is int:
        return value if abs(value) <= 10**12 else "(out of range)"
    if isinstance(value, str) and (
        value in STATUSES | REASONS | {"USD", "EUR"}
        or re.fullmatch(r"(?:INV|PMT)-[0-9]{4}-[A-Z]", value)
    ):
        return value
    return "(invalid value)"


def compare_output(raw: bytes, expected: dict[str, Any]) -> dict[str, Any]:
    try:
        observed = json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        return _failure("malformed_output")
    if not isinstance(observed, dict) or observed.keys() != expected.keys():
        return _failure("output_schema")

    diagnostics: list[dict[str, Any]] = []

    def add(code: str, **details: Any) -> None:
        diagnostics.append({"code": code, **details})

    for group, key, fields in (
        ("invoices", "invoice_id", INVOICE_FIELDS),
        ("exceptions", "row", EXCEPTION_FIELDS),
    ):
        rows = observed[group]
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) or row.keys() != fields.keys()
            or any(type(row[field]) is not expected_type for field, expected_type in fields.items())
            for row in rows
        ):
            add("output_schema", group=group)
            continue
        ids = [row[key] for row in rows]
        if ids != sorted(ids):
            add("ordering", group=group)
        for identity, count in Counter(ids).items():
            if count > 1:
                add("duplicate_output_row", group=group, row=_safe(identity), expected=1, observed=count)
        actual_by_id = {row[key]: row for row in rows}
        expected_by_id = {row[key]: row for row in expected[group]}
        for identity in actual_by_id.keys() - expected_by_id.keys():
            add("unexpected_row", group=group, row=_safe(identity))
        for identity, target in expected_by_id.items():
            actual = actual_by_id.get(identity)
            if actual is None:
                code = target["reason"] if group == "exceptions" else "missing_invoice"
                add(code, group=group, row=identity, expected=target, observed="missing")
                continue
            for field in fields.keys() - {key}:
                if target[field] == actual[field]:
                    continue
                code = target["reason"] if group == "exceptions" else field
                add(code, group=group, row=identity, field=field,
                    expected=target[field], observed=_safe(actual[field]))
    diagnostics.sort(key=lambda row: (row["code"], str(row.get("row", "")), row.get("field", "")))
    return {
        "criteria_passed": not diagnostics,
        "failure_codes": sorted({row["code"] for row in diagnostics}),
        "diagnostics": diagnostics[:MAX_DIAGNOSTICS],
        "output": observed if not diagnostics else None,
    }


def _failure(code: str) -> dict[str, Any]:
    return {"criteria_passed": False, "failure_codes": [code], "diagnostics": [{"code": code}], "output": None}


def verify(workspace: Path, probe: Probe, runner: DockerRunner) -> dict[str, Any]:
    path = workspace / "reconcile.py"
    if path.is_symlink() or not path.is_file():
        return _failure("missing_program")
    with path.open("rb") as handle:
        program = handle.read(MAX_PROGRAM_BYTES + 1)
    if len(program) > MAX_PROGRAM_BYTES:
        return _failure("program_size")
    try:
        result = runner(program, probe)
    except CandidateError as exc:
        return _failure(str(exc))
    return compare_output(result, probe.expected)
