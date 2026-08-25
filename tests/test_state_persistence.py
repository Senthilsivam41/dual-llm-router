from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from evals import scoring
from evals.scoring import append_run_result, load_run_results


def test_concurrent_run_appends_have_unique_ids_and_no_lost_updates(tmp_path: Path):
    runs_path = tmp_path / "run_results.json"

    def append(index: int) -> None:
        append_run_result({"timestamp": f"run-{index}"}, runs_path)

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(append, range(100)))

    document = json.loads(runs_path.read_text(encoding="utf-8"))
    runs = load_run_results(runs_path)
    run_ids = [run["run_id"] for run in runs]

    assert document["total_runs"] == 100
    assert len(runs) == 100
    assert len(set(run_ids)) == 100
    assert set(run_ids) == {f"run_{index:06d}" for index in range(1, 101)}


def test_processes_cannot_lose_concurrent_run_appends(tmp_path: Path):
    runs_path = tmp_path / "process_run_results.json"
    script = (
        "from pathlib import Path; "
        "from evals.scoring import append_run_result; "
        "import sys; "
        "append_run_result({'timestamp': f'process-{sys.argv[2]}'}, Path(sys.argv[1]))"
    )
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(runs_path), str(index)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(16)
    ]
    for process in processes:
        _, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, stderr

    runs = load_run_results(runs_path)
    assert len(runs) == 16
    assert len({run["run_id"] for run in runs}) == 16


def test_failed_atomic_replace_preserves_previous_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    runs_path = tmp_path / "run_results.json"
    append_run_result({"timestamp": "first"}, runs_path)
    original = runs_path.read_bytes()

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(scoring.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        append_run_result({"timestamp": "second"}, runs_path)

    assert runs_path.read_bytes() == original
    assert list(tmp_path.glob(".run_results.json.*.tmp")) == []


def test_duplicate_explicit_run_id_is_rejected(tmp_path: Path):
    runs_path = tmp_path / "run_results.json"
    append_run_result({"run_id": "external-1"}, runs_path)

    with pytest.raises(ValueError, match="Duplicate run_id"):
        append_run_result({"run_id": "external-1"}, runs_path)
