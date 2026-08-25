"""
Calculate fitness scores for agent variants based on run history.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows
    fcntl = None
    import msvcrt
else:
    msvcrt = None

from .paths import RUN_RESULTS_PATH

RUNS_FILE = RUN_RESULTS_PATH
_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: Dict[Path, threading.Lock] = {}
_RUN_ID_PATTERN = re.compile(r"^run_(\d+)$")


def _path_lock(path: Path) -> threading.Lock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(resolved, threading.Lock())


@contextmanager
def _exclusive_file_lock(path: Path) -> Iterator[None]:
    """Serialize threads and POSIX processes updating one state file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f"{path.name}.lock")
    with _path_lock(path):
        with open(lock_path, "a+b") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            elif msvcrt is not None:  # pragma: no cover - Windows only
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:  # pragma: no cover - Windows only
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


def _atomic_write_json(path: Path, data: Dict) -> None:
    """Write complete JSON beside its destination, then atomically replace it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _load_run_document(path: Path) -> Dict:
    if not path.exists():
        return {"total_runs": 0, "runs": []}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"total_runs": len(data), "runs": data}
    return data


def load_run_results(runs_file: Optional[Path] = None) -> List[Dict]:
    """Load all run results (append-only log)."""
    path = Path(runs_file or RUNS_FILE)
    data = _load_run_document(path)
    return data.get("runs", data.get("results", []))


def append_run_result(
    run_data: Dict,
    runs_file: Optional[Path] = None,
) -> Tuple[Dict, int]:
    """Atomically append a run and return its stored payload and sequence."""
    path = Path(runs_file or RUNS_FILE)
    with _exclusive_file_lock(path):
        document = _load_run_document(path)
        runs = list(document.get("runs", document.get("results", [])))
        existing_ids = {
            str(run.get("run_id")) for run in runs if run.get("run_id") is not None
        }
        numbered_ids = [
            int(match.group(1))
            for run_id in existing_ids
            if (match := _RUN_ID_PATTERN.match(run_id))
        ]
        sequence = max(
            len(runs),
            int(document.get("total_runs", 0) or 0),
            max(numbered_ids, default=0),
        ) + 1

        payload = dict(run_data)
        payload.setdefault("run_id", f"run_{sequence:06d}")
        if payload["run_id"] in existing_ids:
            raise ValueError(f"Duplicate run_id: {payload['run_id']}")
        runs.append(payload)
        _atomic_write_json(
            path,
            {
                "updated_at": payload.get("timestamp"),
                "total_runs": len(runs),
                "last_evolution_check": len(runs),
                "runs": runs,
            },
        )
        return payload, len(runs)


def save_run_result(run_data: Dict, runs_file: Optional[Path] = None) -> None:
    """Backward-compatible atomic append API."""
    append_run_result(run_data, runs_file)


def calculate_fitness(
    runs: List[Dict],
    hermes_variant: str,
    laguna_variant: str,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Calculate composite fitness score for a (hermes, laguna) pair.

    Returns weighted fitness components.
    """
    matching = [
        r
        for r in runs
        if r.get("config", {}).get("hermes_variant") == hermes_variant
        and r.get("config", {}).get("laguna_variant") == laguna_variant
    ]

    if len(matching) < 5:
        return {
            "success_rate": 0.0,
            "cost_efficiency": 0.0,
            "quality_score": 0.0,
            "time_efficiency": 0.0,
            "sample_size": len(matching),
            "composite": 0.0,
        }

    successful = [
        r
        for r in matching
        if r.get("result", {}).get("status") in ("success", "completed")
    ]
    success_rate = len(successful) / len(matching)

    costs = [float(r.get("result", {}).get("cost", 0) or 0) for r in matching]
    expected_costs = [
        float(r.get("task", {}).get("expected_cost", 0) or 0) for r in matching
    ]
    ratios = [
        (exp / cost) if cost > 0 else 0.0
        for cost, exp in zip(costs, expected_costs)
        if exp > 0
    ]
    # Prefer expected/actual (higher when cheaper than expected); clamp to [0, 1.5].
    if ratios:
        cost_efficiency = min(1.5, sum(min(1.5, r) for r in ratios) / len(ratios)) / 1.5
    else:
        avg_cost = sum(costs) / len(costs) if costs else 0.0
        cost_efficiency = max(0.0, 1.0 - avg_cost)

    quality_scores = []
    for r in matching:
        qm = r.get("quality_metrics", {}) or {}
        score = qm.get("quality_score")
        if score is not None:
            quality_scores.append(float(score))
    quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    times = [float(r.get("result", {}).get("time_seconds", 0) or 0) for r in matching]
    avg_time = sum(times) / len(times) if times else 0.0
    time_efficiency = max(0.0, 1.0 - (avg_time / 60.0))

    weights = weights or {
        "success_rate": 0.35,
        "cost_efficiency": 0.30,
        "quality_score": 0.25,
        "time_efficiency": 0.10,
    }
    composite = (
        success_rate * weights["success_rate"]
        + cost_efficiency * weights["cost_efficiency"]
        + quality_score * weights["quality_score"]
        + time_efficiency * weights["time_efficiency"]
    )

    return {
        "success_rate": round(success_rate, 4),
        "cost_efficiency": round(cost_efficiency, 4),
        "quality_score": round(quality_score, 4),
        "time_efficiency": round(time_efficiency, 4),
        "sample_size": len(matching),
        "composite": round(composite, 4),
        "avg_cost": round(sum(costs) / len(costs), 4) if costs else 0.0,
        "avg_time": round(avg_time, 1),
    }


def score_variant(
    runs: List[Dict],
    hermes_variant: str,
    laguna_variant: str,
) -> Dict[str, float]:
    """Score a specific (hermes, laguna) variant combination."""
    return calculate_fitness(runs, hermes_variant, laguna_variant)


def get_top_variants(
    runs: List[Dict],
    top_n: int = 5,
) -> List[Tuple[Tuple[str, str], Dict[str, float]]]:
    """Get top N variant combinations by composite score."""
    hermes_variants = sorted(
        {
            r.get("config", {}).get("hermes_variant")
            for r in runs
            if r.get("config", {}).get("hermes_variant")
        }
    )
    laguna_variants = sorted(
        {
            r.get("config", {}).get("laguna_variant")
            for r in runs
            if r.get("config", {}).get("laguna_variant")
        }
    )

    all_scores = {}
    for hv in hermes_variants:
        for lv in laguna_variants:
            all_scores[(hv, lv)] = calculate_fitness(runs, hv, lv)

    sorted_scores = sorted(
        all_scores.items(), key=lambda x: x[1]["composite"], reverse=True
    )
    return sorted_scores[:top_n]
