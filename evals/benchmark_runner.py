"""
Benchmark runner for dual-llm-router variant evaluation.
Loads tasks from benchmark/{easy,medium,hard,extreme}/ and executes via EvolvingRouter.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from benchmark.tasks_loader import load_task_modules
from evals.evolution_engine import EvolutionEngine
from evals.paths import AUTOCLAW_ROOT, PROJECT_ROOT

logger = logging.getLogger("evals.benchmark_runner")

BENCHMARK_STATE_DIR = AUTOCLAW_ROOT / "evals" / "benchmark"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class BenchmarkTask:
    """Defines a single benchmark task."""

    id: str
    category: str
    spec: str
    acceptance_criteria: List[str]
    complexity_score: float
    expected_cost: float
    expected_time: float
    seed_code: Optional[str] = None
    expected_code: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    difficulty: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkTask":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        payload = {k: v for k, v in data.items() if k in known}
        payload.setdefault("tags", [])
        return cls(**payload)


@dataclass
class BenchmarkResult:
    """Result of running a benchmark task."""

    task_id: str
    category: str
    variant_hermes: str
    variant_laguna: str
    status: str
    cost: float
    time_seconds: float
    iterations: int
    executor_calls: int
    quality_score: float
    acceptance_criteria_passed: bool
    acceptance_criteria_details: Dict[str, bool]
    failure_reason: Optional[str] = None
    code_diff: Optional[str] = None
    timestamp: Optional[str] = None
    expected_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkResult":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


class BenchmarkRunner:
    """Runs benchmark tasks with specified variant combinations."""

    def __init__(
        self,
        engine: Optional[EvolutionEngine] = None,
        *,
        benchmark_dir: Optional[Path] = None,
        simulate: bool = False,
        workspace_root: Optional[str] = None,
    ):
        self.engine = engine or EvolutionEngine()
        self.benchmark_dir = Path(benchmark_dir or BENCHMARK_STATE_DIR)
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        (self.benchmark_dir / "tasks").mkdir(parents=True, exist_ok=True)
        self.simulate = simulate
        self.workspace_root = workspace_root or str(PROJECT_ROOT / "workspace" / "benchmark")
        self.results: List[BenchmarkResult] = []
        self.benchmark_suite = self._load_benchmark_suite()
        self._export_task_snapshots()

    def _load_benchmark_suite(self) -> List[BenchmarkTask]:
        tasks = [BenchmarkTask.from_dict(t) for t in load_task_modules()]
        # Also load any JSON tasks dropped into .autoclaw/evals/benchmark/tasks/
        for task_file in sorted((self.benchmark_dir / "tasks").glob("*.json")):
            with open(task_file, encoding="utf-8") as f:
                tasks.append(BenchmarkTask.from_dict(json.load(f)))
        # De-dupe by id (package tasks win over JSON duplicates)
        by_id: Dict[str, BenchmarkTask] = {}
        for task in tasks:
            by_id.setdefault(task.id, task)
        loaded = list(by_id.values())
        logger.info("Loaded %s benchmark tasks", len(loaded))
        return loaded

    def _export_task_snapshots(self) -> None:
        snapshot = [t.to_dict() for t in self.benchmark_suite]
        with open(self.benchmark_dir / "tasks.json", "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
            f.write("\n")

    def list_tasks(self, suite: Optional[str] = None) -> List[BenchmarkTask]:
        if not suite or suite == "all":
            return list(self.benchmark_suite)
        return [t for t in self.benchmark_suite if t.category == suite]

    def run_single_task(
        self,
        task: BenchmarkTask,
        variant_hermes: Optional[str] = None,
        variant_laguna: Optional[str] = None,
    ) -> BenchmarkResult:
        variant_hermes = variant_hermes or self.engine.active_hermes
        variant_laguna = variant_laguna or self.engine.active_laguna

        start_time = time.time()
        result = self._execute_task(task, variant_hermes, variant_laguna)
        elapsed = time.time() - start_time

        cost = float(result.get("cost", 0.0) or 0.0)
        quality_score = self._calculate_quality_score(task, result)
        details = result.get("acceptance_criteria_details") or {}
        if not details:
            details = {
                c: self._check_single_criterion(task, c, result) for c in task.acceptance_criteria
            }
        acceptance_passed = all(details.values()) if details else False

        status = result.get("status", "failure")
        if status == "completed":
            status = "success"
        if status == "success" and not acceptance_passed:
            status = "partial"

        benchmark_result = BenchmarkResult(
            task_id=task.id,
            category=task.category,
            variant_hermes=variant_hermes,
            variant_laguna=variant_laguna,
            status=status,
            cost=cost,
            time_seconds=round(elapsed, 3),
            iterations=int(result.get("iterations", 1) or 1),
            executor_calls=int(result.get("executor_calls", 0) or 0),
            quality_score=quality_score,
            acceptance_criteria_passed=acceptance_passed,
            acceptance_criteria_details=details,
            failure_reason=result.get("failure_reason"),
            code_diff=result.get("code_diff"),
            timestamp=_utc_now(),
            expected_cost=task.expected_cost,
        )
        self.results.append(benchmark_result)

        # Feed evolution scoring pipeline.
        self.engine.record_run_result(
            {
                "run_id": f"bench_{task.id}_{benchmark_result.timestamp}",
                "timestamp": benchmark_result.timestamp,
                "config": {
                    "hermes_variant": variant_hermes,
                    "laguna_variant": variant_laguna,
                },
                "task": {
                    "spec_id": task.id,
                    "complexity": task.category,
                    "domain": ",".join(task.tags),
                    "expected_cost": task.expected_cost,
                },
                "result": {
                    "status": "success" if status == "success" else "failure",
                    "cost": cost,
                    "time_seconds": benchmark_result.time_seconds,
                    "iterations": benchmark_result.iterations,
                    "executor_calls": benchmark_result.executor_calls,
                },
                "quality_metrics": {
                    "quality_score": quality_score,
                    "code_quality_score": quality_score,
                    "acceptance_criteria_pass": acceptance_passed,
                },
            }
        )
        logger.info(
            "Benchmark task=%s status=%s quality=%.3f cost=%.4f time=%.2fs",
            task.id,
            status,
            quality_score,
            cost,
            elapsed,
        )
        return benchmark_result

    def run_benchmark_suite(
        self,
        task_ids: Optional[List[str]] = None,
        variant_combo: Optional[Tuple[str, str]] = None,
        suite: Optional[str] = None,
    ) -> List[BenchmarkResult]:
        tasks = self.list_tasks(suite)
        if task_ids:
            wanted = set(task_ids)
            tasks = [t for t in tasks if t.id in wanted]

        results: List[BenchmarkResult] = []
        for task in tasks:
            hermes = variant_combo[0] if variant_combo else None
            laguna = variant_combo[1] if variant_combo else None
            results.append(self.run_single_task(task, hermes, laguna))
        return results

    def _execute_task(
        self,
        task: BenchmarkTask,
        variant_hermes: str,
        variant_laguna: str,
    ) -> Dict[str, Any]:
        if self.simulate or not os.getenv("OPENROUTER_API_KEY"):
            return self._simulate_execution(task)

        from router.router import EvolvingRouter

        work = Path(self.workspace_root) / task.id / f"{variant_hermes}_{variant_laguna}"
        work.mkdir(parents=True, exist_ok=True)
        if task.seed_code:
            seed_name = "seed.py"
            (work / seed_name).write_text(task.seed_code, encoding="utf-8")

        # Temporarily pin active variants for prompt selection.
        prev_h, prev_l = self.engine.active_hermes, self.engine.active_laguna
        self.engine.active_hermes = variant_hermes
        self.engine.active_laguna = variant_laguna
        try:
            router = EvolvingRouter(
                evolution_engine=self.engine,
                workspace_root=str(work),
            )
            pipeline = router.route_task(task.spec, execute_tools=True)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "failure",
                "failure_reason": str(exc),
                "iterations": 0,
                "executor_calls": 0,
                "cost": 0.0,
                "acceptance_criteria_details": {c: False for c in task.acceptance_criteria},
            }
        finally:
            self.engine.active_hermes = prev_h
            self.engine.active_laguna = prev_l

        metrics = pipeline.get("metrics") or {}
        executor = pipeline.get("executor_result") or {}
        report = executor.get("verification_report") or {}
        details = {
            d.get("criterion", f"check_{i}"): bool(d.get("passed"))
            for i, d in enumerate(report.get("details") or [])
        }
        # Map planner criteria into details when verification only checked files.
        for criterion in task.acceptance_criteria:
            details.setdefault(criterion, bool(report.get("criteria_passed")))

        status = pipeline.get("status", "failure")
        return {
            "status": status,
            "iterations": 1,
            "executor_calls": sum(
                1
                for m in metrics.get("breakdown") or []
                if "executor" in str(m.get("node", "")).lower()
            ),
            "cost": float(metrics.get("total_cost_usd") or 0.0),
            "failure_reason": pipeline.get("error"),
            "acceptance_criteria_details": details,
            "workspace": str(work),
            "task_spec": pipeline.get("task_spec"),
            "syntax_valid": True,
            "tests_pass": bool(executor.get("success")),
            "imports_valid": True,
            "no_errors": status in ("completed", "success"),
        }

    def _simulate_execution(self, task: BenchmarkTask) -> Dict[str, Any]:
        """Deterministic offline simulation for CI / no-API environments."""
        # Easier tasks succeed more often; seeded by task id for stability.
        seed = sum(ord(c) for c in task.id) % 100
        success = seed < int((1.0 - task.complexity_score) * 90) + 5
        details = {c: success for c in task.acceptance_criteria}
        # Leave one criterion failing on partial-ish hard tasks.
        if not success and task.acceptance_criteria:
            details[task.acceptance_criteria[0]] = False
        return {
            "status": "success" if success else "failure",
            "iterations": 1 + int(task.complexity_score * 3),
            "executor_calls": 1 + int(task.complexity_score * 4),
            "cost": round(task.expected_cost * (0.8 if success else 1.2), 4),
            "failure_reason": None if success else "simulated_failure",
            "acceptance_criteria_details": details,
            "syntax_valid": True,
            "tests_pass": success,
            "imports_valid": True,
            "no_errors": success,
        }

    def _calculate_quality_score(self, task: BenchmarkTask, result: Dict[str, Any]) -> float:
        checks = [
            bool(result.get("syntax_valid", self._check_syntax(task, result))),
            bool(result.get("tests_pass", self._check_tests(task, result))),
            bool(result.get("imports_valid", self._check_imports(task, result))),
            bool(result.get("no_errors", self._check_no_errors(task, result))),
        ]
        base = sum(0.25 for c in checks if c)
        details = result.get("acceptance_criteria_details") or {}
        if details:
            pass_rate = sum(1 for v in details.values() if v) / len(details)
            return round(0.5 * base + 0.5 * pass_rate, 4)
        return round(base, 4)

    def _check_syntax(self, task: BenchmarkTask, result: Dict[str, Any]) -> bool:
        workspace = result.get("workspace")
        if not workspace:
            return result.get("status") in ("success", "completed")
        root = Path(workspace)
        for path in root.rglob("*.py"):
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                return False
        return True

    def _check_tests(self, task: BenchmarkTask, result: Dict[str, Any]) -> bool:
        return bool(result.get("tests_pass") or result.get("status") in ("success", "completed"))

    def _check_imports(self, task: BenchmarkTask, result: Dict[str, Any]) -> bool:
        return True

    def _check_no_errors(self, task: BenchmarkTask, result: Dict[str, Any]) -> bool:
        return result.get("failure_reason") in (None, "")

    def _check_single_criterion(
        self, task: BenchmarkTask, criterion: str, result: Dict[str, Any]
    ) -> bool:
        details = result.get("acceptance_criteria_details") or {}
        if criterion in details:
            return bool(details[criterion])
        return result.get("status") in ("success", "completed")

    def save_results(self, filepath: Optional[str] = None) -> Path:
        path = Path(filepath or self.benchmark_dir / "results.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)
            f.write("\n")
        logger.info("Saved %s results to %s", len(self.results), path)
        return path

    def load_results(self, filepath: Optional[str] = None) -> List[BenchmarkResult]:
        path = Path(filepath or self.benchmark_dir / "results.json")
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("results", [])
        return [BenchmarkResult.from_dict(r) for r in data]
