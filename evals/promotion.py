"""Gate durable genome snapshots. Runtime genomes stay under .autoclaw/."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from evals.evolution_engine import EvolutionEngine
from evals.scoring import calculate_fitness

_SECRET_KEYS = {
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "access_token",
    "authorization",
}
_SECRET_TEXT = re.compile(
    r"""sk-[A-Za-z0-9_-]{10,}|(?:api[_-]?key|secret|password)\s*["']?\s*[:=]\s*["']?\S{6,}""",
    re.IGNORECASE,
)
_FITNESS_SAMPLE_FLOOR = 5


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def promotion_dir_for(engine: EvolutionEngine) -> Path:
    return engine.project_root / "evolution" / "promoted"


def _settings(engine: EvolutionEngine) -> Dict[str, float]:
    defaults = {
        "min_delta": 0.05,
        "min_samples": _FITNESS_SAMPLE_FLOOR,
        "regression_tolerance": 0.0,
    }
    raw = engine.config.get("promotion")
    if not isinstance(raw, dict):
        raw = {}
    alerting = engine.config.get("alerting")
    if "min_delta" not in raw and isinstance(alerting, dict) and alerting.get("min_delta") is not None:
        defaults["min_delta"] = float(alerting["min_delta"])
    merged = {**defaults, **raw}
    return {
        "min_delta": float(merged["min_delta"]),
        "min_samples": float(merged["min_samples"]),
        "regression_tolerance": float(merged["regression_tolerance"]),
    }


def _public_genome(genome: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in genome.items() if not str(key).startswith("_")}


def _prompt_sha256(engine: EvolutionEngine, genome: Dict[str, Any]) -> str:
    text = genome.get("system_prompt")
    if not isinstance(text, str) or not text:
        text = engine._agent_prompt_text(genome)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _secret_hits(value: Any, path: str = "") -> List[str]:
    hits: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            here = f"{path}.{key}" if path else str(key)
            normalized = str(key).lower().replace("-", "_")
            if normalized in _SECRET_KEYS and item not in (None, "", [], {}):
                hits.append(here)
            hits.extend(_secret_hits(item, here))
        return hits
    if isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(_secret_hits(item, f"{path}[{index}]"))
        return hits
    if isinstance(value, str) and _SECRET_TEXT.search(value):
        hits.append(path or "text")
    return hits


def _load_latest(output_dir: Path) -> Optional[Dict[str, Any]]:
    path = output_dir / "LATEST.json"
    if not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("LATEST.json is not an object")
    return loaded


def _pair_fitness(engine: EvolutionEngine) -> Dict[str, float]:
    weights = engine.config.get("scoring") or {}
    if isinstance(weights, dict) and isinstance(weights.get("weights"), dict):
        weights = weights["weights"]
    if not isinstance(weights, dict):
        weights = None
    return calculate_fitness(
        engine._load_run_results(),
        engine.active_hermes,
        engine.active_laguna,
        weights=weights,
    )


def _challenger_block(engine: EvolutionEngine) -> Optional[str]:
    active = {engine.active_hermes, engine.active_laguna}
    for test in engine.ab_manager.ab_tests:
        if test.get("status") != "running":
            continue
        for variant in test.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            variant_id = str(variant.get("variant_id", ""))
            role = str(variant.get("role", "challenger"))
            if role != "control" and variant_id in active:
                return variant_id
    return None


def _agent_row(
    engine: EvolutionEngine,
    variant_id: str,
    fitness: Dict[str, float],
) -> Dict[str, Any]:
    genome = engine.genomes.get(variant_id) or {}
    return {
        "variant_id": variant_id,
        "prompt_sha256": _prompt_sha256(engine, genome) if genome else "",
        "composite": float(fitness.get("composite") or 0.0),
        "success_rate": float(fitness.get("success_rate") or 0.0),
        "sample_size": int(fitness.get("sample_size") or 0),
    }


def evaluate_promotion(
    engine: EvolutionEngine,
    *,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Decide whether the active pair may be copied out of .autoclaw/."""
    output_dir = Path(output_dir) if output_dir else promotion_dir_for(engine)
    settings = _settings(engine)
    required_samples = max(_FITNESS_SAMPLE_FLOOR, int(settings["min_samples"]))
    reasons: List[str] = []

    try:
        previous = _load_latest(output_dir)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "rejected",
            "reasons": [f"unreadable latest snapshot: {exc}"],
            "applied_path": None,
        }

    missing = [
        variant_id
        for variant_id in (engine.active_hermes, engine.active_laguna)
        if variant_id not in engine.genomes
    ]
    if missing:
        return {
            "status": "rejected",
            "reasons": [f"missing genome {variant_id}" for variant_id in missing],
            "applied_path": None,
        }

    fitness = _pair_fitness(engine)
    hermes = _agent_row(engine, engine.active_hermes, fitness)
    laguna = _agent_row(engine, engine.active_laguna, fitness)
    decision: Dict[str, Any] = {
        "status": "rejected",
        "reasons": reasons,
        "hermes": hermes,
        "laguna": laguna,
        "pair": {
            "composite": float(fitness.get("composite") or 0.0),
            "success_rate": float(fitness.get("success_rate") or 0.0),
            "sample_size": int(fitness.get("sample_size") or 0),
            "quality_score": float(fitness.get("quality_score") or 0.0),
            "cost_efficiency": float(fitness.get("cost_efficiency") or 0.0),
            "time_efficiency": float(fitness.get("time_efficiency") or 0.0),
        },
        "previous_snapshot": None if previous is None else previous.get("snapshot_id"),
        "min_delta": settings["min_delta"],
        "min_samples": required_samples,
        "applied_path": None,
    }

    for variant_id in (engine.active_hermes, engine.active_laguna):
        hits = _secret_hits(_public_genome(engine.genomes[variant_id]))
        for hit in hits:
            reasons.append(f"secret material in {variant_id}.{hit}")
    if reasons:
        decision["status"] = "rejected"
        return decision

    if previous is not None:
        prev_hermes = previous.get("hermes") or {}
        prev_laguna = previous.get("laguna") or {}
        same_ids = (
            prev_hermes.get("variant_id") == hermes["variant_id"]
            and prev_laguna.get("variant_id") == laguna["variant_id"]
        )
        same_hash = (
            prev_hermes.get("prompt_sha256") == hermes["prompt_sha256"]
            and prev_laguna.get("prompt_sha256") == laguna["prompt_sha256"]
        )
        if same_ids and same_hash:
            decision["status"] = "unchanged"
            reasons.append(f"same genomes as snapshot {previous.get('snapshot_id')}")
            return decision

    sample_size = int(fitness.get("sample_size") or 0)
    if sample_size < required_samples:
        reasons.append(f"sample_size {sample_size} is below {required_samples}")

    challenger = _challenger_block(engine)
    if challenger:
        reasons.append(f"ab_inconclusive: {challenger} is a challenger in a running A/B test")

    if reasons:
        decision["status"] = "rejected"
        return decision

    if previous is None:
        decision["status"] = "baseline"
        reasons.append("first durable snapshot of the active pair")
        return decision

    previous_pair = previous.get("pair") or {}
    previous_success = float(previous_pair.get("success_rate") or 0.0)
    previous_composite = float(previous_pair.get("composite") or 0.0)
    success = float(fitness.get("success_rate") or 0.0)
    composite = float(fitness.get("composite") or 0.0)
    if success + settings["regression_tolerance"] < previous_success:
        reasons.append(
            f"success_rate {success:.4f} dropped below previous {previous_success:.4f}"
        )
        decision["status"] = "rejected"
        return decision
    if composite + 1e-9 < previous_composite + settings["min_delta"]:
        reasons.append(
            f"pair composite {composite:.4f} is below "
            f"{previous_composite:.4f} + min_delta {settings['min_delta']:.4f}"
        )
        decision["status"] = "rejected"
        return decision

    decision["status"] = "promote"
    reasons.append("active pair cleared the fitness gates")
    return decision


def _write_index(output_dir: Path) -> None:
    rows: List[Dict[str, Any]] = []
    snapshot_root = output_dir / "snapshots"
    if snapshot_root.exists():
        for manifest_path in snapshot_root.glob("*/manifest.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(manifest, dict):
                rows.append(manifest)
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    lines = [
        "# Promoted genomes",
        "",
        "Durable copies of pairs that cleared the promotion gates.",
        "Nightly evolution does not write this directory.",
        "",
        "| Created (UTC) | Snapshot | Status | Hermes | Laguna | Composite | Success |",
        "| --- | --- | --- | --- | --- | ---: | ---: |",
    ]
    for row in rows:
        pair = row.get("pair") or {}
        hermes = row.get("hermes") or {}
        laguna = row.get("laguna") or {}
        snapshot_id = row.get("snapshot_id", "")
        lines.append(
            f"| `{row.get('created_at', '')}` | `{snapshot_id}` | `{row.get('status', '')}` | "
            f"`{hermes.get('variant_id', '')}` | `{laguna.get('variant_id', '')}` | "
            f"{float(pair.get('composite') or 0):.4f} | {float(pair.get('success_rate') or 0):.4f} |"
        )
    if not rows:
        lines.append("| — | — | — | — | — | — | — |")
    lines.append("")
    (output_dir / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def apply_promotion(
    engine: EvolutionEngine,
    decision: Dict[str, Any],
    *,
    output_dir: Optional[Path] = None,
    snapshot_id: Optional[str] = None,
) -> Path:
    """Copy the active pair into evolution/promoted when the decision allows it."""
    if decision.get("status") not in {"baseline", "promote"}:
        raise ValueError(f"cannot apply promotion status {decision.get('status')}")
    output_dir = Path(output_dir) if output_dir else promotion_dir_for(engine)
    current = evaluate_promotion(engine, output_dir=output_dir)
    if current.get("status") != decision.get("status"):
        raise ValueError("promotion decision is stale")
    for agent in ("hermes", "laguna"):
        if (current.get(agent) or {}).get("prompt_sha256") != (decision.get(agent) or {}).get(
            "prompt_sha256"
        ):
            raise ValueError(f"{agent} genome changed since the decision")

    snapshot_id = snapshot_id or _stamp()
    snapshot_dir = output_dir / "snapshots" / snapshot_id
    if snapshot_dir.exists():
        raise FileExistsError(f"snapshot already exists: {snapshot_id}")
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    for agent, variant_id in (
        ("hermes", engine.active_hermes),
        ("laguna", engine.active_laguna),
    ):
        payload = _public_genome(engine.genomes[variant_id])
        (snapshot_dir / f"{agent}.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    created_at = _utc_now()
    manifest = {
        "snapshot_id": snapshot_id,
        "status": decision["status"],
        "created_at": created_at,
        "run_count": engine.run_count,
        "hermes": current["hermes"],
        "laguna": current["laguna"],
        "pair": current["pair"],
        "reasons": list(current.get("reasons") or []),
        "files": ["hermes.json", "laguna.json"],
    }
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    latest = {
        "snapshot_id": snapshot_id,
        "status": decision["status"],
        "created_at": created_at,
        "hermes": current["hermes"],
        "laguna": current["laguna"],
        "pair": current["pair"],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "LATEST.json").write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")
    _write_index(output_dir)
    return snapshot_dir
