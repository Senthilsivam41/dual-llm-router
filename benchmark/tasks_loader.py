"""Load benchmark task definitions from benchmark/{easy,medium,hard,extreme}/."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional

CATEGORIES = ("easy", "medium", "hard", "extreme")
BENCHMARK_ROOT = Path(__file__).resolve().parent


def load_task_modules(categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Import TASK dicts from category packages."""
    selected = categories or list(CATEGORIES)
    tasks: List[Dict[str, Any]] = []

    for category in selected:
        if category not in CATEGORIES:
            continue
        package_name = f"benchmark.{category}"
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            continue
        package_path = Path(package.__file__).parent
        for module_info in pkgutil.iter_modules([str(package_path)]):
            if module_info.name.startswith("_"):
                continue
            module = importlib.import_module(f"{package_name}.{module_info.name}")
            task = getattr(module, "TASK", None)
            if isinstance(task, dict):
                task = dict(task)
                task.setdefault("category", category)
                task.setdefault("id", f"{category}_{module_info.name}")
                tasks.append(task)
    return tasks


def task_to_jsonable(task: Dict[str, Any]) -> Dict[str, Any]:
    return dict(task)
