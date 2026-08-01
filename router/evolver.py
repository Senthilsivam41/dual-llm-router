"""Co-evolution integration point for DualLLMRouter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from evals.evolution_engine import EvolutionEngine
from evals.paths import EVOLUTION_CONFIG_PATH
from router.router import EvolvingRouter


class CoEvolver:
    """Bridge between router runs and the evolution engine."""

    def __init__(
        self,
        *,
        config_path: Optional[Path] = None,
        root: Optional[Path] = None,
        workspace_root: str = ".",
    ):
        self.engine = EvolutionEngine(
            root=root,
            config_path=Path(config_path) if config_path else EVOLUTION_CONFIG_PATH,
        )
        self.router = EvolvingRouter(
            evolution_engine=self.engine,
            workspace_root=workspace_root,
        )

    def run(self, user_prompt: str, *, execute_tools: bool = True) -> Dict[str, Any]:
        return self.router.route_task(user_prompt, execute_tools=execute_tools)

    def evolve_now(self) -> Dict[str, Any]:
        return self.engine.evolve()

    def status(self) -> Dict[str, Any]:
        return {
            "active_hermes": self.engine.active_hermes,
            "active_laguna": self.engine.active_laguna,
            "run_count": self.engine.run_count,
            "should_evolve": self.engine.should_evolve(),
            "check_interval_runs": self.engine.config.get("check_interval_runs"),
            "log_path": str(self.engine.evolution_log_path),
        }
