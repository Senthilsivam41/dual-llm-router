"""Example execution entrypoint for the Dual-LLM Router framework."""

import argparse
import os
import sys

from src.orchestrator import DualLLMRouterOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Run Dual-LLM Router Agent (Hermes 4 Planner + Laguna S 2.1 Executor)"
    )
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        default="Create a python module `math_utils.py` containing a function `add(a, b)` and a corresponding unit test `test_math_utils.py`.",
        help="User request prompt for the agent pipeline"
    )
    parser.add_argument(
        "-w", "--workspace",
        type=str,
        default="./workspace",
        help="Target workspace root directory for tool execution"
    )
    args = parser.parse_args()

    # Ensure isolated workspace scratch directory exists
    workspace_dir = os.path.abspath(args.workspace)
    os.makedirs(workspace_dir, exist_ok=True)

    print("=== Running Dual-LLM Router Pipeline ===")
    print(f"Workspace: {workspace_dir}")
    print(f"User Request: {args.prompt}\n")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("NOTE: OPENROUTER_API_KEY environment variable is not set.")
        print("The pipeline will run using fallback/mock LLM completion modes.\n")

    try:
        orchestrator = DualLLMRouterOrchestrator(workspace_root=workspace_dir)
        result = orchestrator.run(args.prompt, execute_tools=True)
    except Exception as e:
        print(f"\n[ERROR] Pipeline execution crashed with unhandled exception: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n=== Pipeline Execution Summary ===")
    print(f"Status: {result.get('status', 'unknown')}")

    task_spec = result.get("task_spec")
    if task_spec:
        print(f"TaskSpec Goal: {task_spec.get('goal', 'N/A')}")
        print(f"Acceptance Criteria: {task_spec.get('acceptance_criteria', [])}")
    else:
        print("TaskSpec: None (Planning failed)")

    if result.get("error"):
        print(f"Error Details: {result.get('error')}")

    executor_result = result.get("executor_result")
    if executor_result:
        print(f"Verification Report: {executor_result.get('verification_report')}")
        print(f"Tool Results Count: {len(executor_result.get('tool_results', []))}")

    print(f"\nMetrics: {result.get('metrics', {})}")


if __name__ == "__main__":
    main()
