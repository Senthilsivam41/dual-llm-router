#!/usr/bin/env python3
"""Run or replay the paired invoice reconciliation showcase."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reconciliation.report import checkpoint, write_report
from src.reconciliation.study import EXAMPLE, TrialRunner, make_record, provider_settings, run_study, utc_now
from src.reconciliation.verifier import DockerRunner, SandboxError
from src.showcase.session import preflight_model
from src.showcase.settings import showcase_models


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="Run the provider and Docker benchmark")
    mode.add_argument("--replay", action="store_true", help="Render a saved recording")
    parser.add_argument("--demo", action="store_true", help="Run one paired trial for the showcase")
    parser.add_argument("--recording", type=Path, help="Path to run.json for replay")
    parser.add_argument("--output", type=Path, help="New output directory")
    parser.add_argument("--jobs", type=int, default=4, choices=range(1, 9), metavar="1..8")
    args = parser.parse_args()
    if args.recording and args.live:
        parser.error("--recording requires --replay")
    return args


def _live(args: argparse.Namespace, output: Path) -> int:
    policy = (EXAMPLE / "policy.md").read_text(encoding="utf-8")
    planner, executor = showcase_models()
    models = {"planner": planner, "executor": executor}
    runner = DockerRunner()
    with provider_settings():
        record = make_record(models, policy, demo=args.demo, mode="live")
        record["protocol"]["jobs"] = args.jobs
        checkpoint(output, record)
        try:
            record["preflight"]["docker_image_id"] = runner.preflight()
            for model in dict.fromkeys(models.values()):
                print(f"Checking provider model {model}", flush=True)
                error = preflight_model(model)
                if error:
                    raise RuntimeError(error)
                record["preflight"].setdefault("models", []).append(model)
        except (SandboxError, RuntimeError) as exc:
            record.update(status="blocked", blocker=str(exc), finished_at=utc_now())
            write_report(output, record)
            print(record["blocker"], file=sys.stderr)
            return 2

        def save(current: dict) -> None:
            checkpoint(output, current)
            print(f"Recorded {len(current['development'])} development and "
                  f"{len(current['trials'])} evaluation trials", flush=True)

        try:
            run_study(output, record, TrialRunner(models, runner, policy), jobs=args.jobs, checkpoint=save)
        except KeyboardInterrupt:
            record.update(status="incomplete", blocker="Interrupted", finished_at=utc_now())
            write_report(output, record)
            return 130
        write_report(output, record)
        return 0 if record["status"] == "complete" else 1


def main() -> int:
    args = _arguments()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.output or ROOT / "reports" / "reconciliation" / stamp).resolve()
    try:
        if args.replay:
            source = args.recording or EXAMPLE / "recorded" / "run.json"
            record = json.loads(source.read_text(encoding="utf-8"))
            if record.get("schema_version") != 1:
                raise ValueError("Unsupported reconciliation recording version")
            output.mkdir(parents=True)
            record["replayed"] = True
            write_report(output, record)
            status = 0
        else:
            output.mkdir(parents=True)
            status = _live(args, output)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Reconciliation benchmark: {exc}", file=sys.stderr)
        return 2
    print(f"Report: {output / 'report.html'}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
