"""Example execution of Dual-LLM Router framework."""

import os
import sys

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.orchestrator import DualLLMRouterOrchestrator

def main():
    prompt = "Create a python module `math_utils.py` containing a function `add(a, b)` and a corresponding unit test `test_math_utils.py`."
    print(f"=== Running Dual-LLM Router Pipeline ===")
    print(f"User Request: {prompt}\n")

    orchestrator = DualLLMRouterOrchestrator(workspace_root=".")
    
    # If no API key configured, notify
    if not os.getenv("OPENROUTER_API_KEY"):
        print("NOTE: OPENROUTER_API_KEY environment variable not set. Running mock/verification tests instead.")
        return

    result = orchestrator.run(prompt, execute_tools=True)
    print("\n=== Pipeline Execution Summary ===")
    print(f"Status: {result['status']}")
    print(f"TaskSpec Goal: {result['task_spec']['goal']}")
    print(f"Acceptance Criteria: {result['task_spec']['acceptance_criteria']}")
    print(f"\nMetrics: {result['metrics']}")

if __name__ == "__main__":
    main()
