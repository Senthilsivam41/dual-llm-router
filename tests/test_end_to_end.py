import os
import json
import unittest
from unittest.mock import patch, MagicMock
from src.schemas.task_spec import TaskSpec
from src.tools import apply_patch, run_shell
from src.utils.metrics import MetricsLogger
from src.orchestrator import DualLLMRouterOrchestrator

class TestDualLLMRouter(unittest.TestCase):
    def test_task_spec_validation(self):
        spec_data = {
            "goal": "Build toy calculator",
            "target_files": ["calc.py"],
            "acceptance_criteria": ["calc.py exists", "tests pass"],
            "step_by_step_plan": ["Create calc.py with add function"],
            "notes": "Keep simple",
        }
        spec = TaskSpec(**spec_data)
        self.assertEqual(spec.goal, "Build toy calculator")
        self.assertIn("calc.py", spec.target_files)

    def test_patch_tool_safety(self):
        workspace = "/tmp/test_router_workspace"
        os.makedirs(workspace, exist_ok=True)
        res = apply_patch("src/demo.py", "print('hello')", workspace_root=workspace)
        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(os.path.join(workspace, "src/demo.py")))

        # Test path traversal prevention
        res_unsafe = apply_patch("../../outside.py", "bad", workspace_root=workspace)
        self.assertFalse(res_unsafe["success"])
        self.assertIn("outside workspace", res_unsafe["error"])

    def test_shell_tool(self):
        workspace = "/tmp/test_router_workspace"
        os.makedirs(workspace, exist_ok=True)
        res = run_shell("echo 'hello world'", workspace_root=workspace)
        self.assertTrue(res["success"])
        self.assertIn("hello world", res["stdout"])

    def test_metrics_logger(self):
        logger = MetricsLogger()
        logger.log_call("PlannerNode", "hermes-4", 100, 50, 0.5)
        logger.log_call("ExecutorNode", "laguna-2.1", 200, 150, 1.2)
        summary = logger.summary()
        self.assertEqual(summary["total_calls"], 2)
        self.assertEqual(summary["total_prompt_tokens"], 300)
        self.assertEqual(summary["total_completion_tokens"], 200)
        self.assertEqual(summary["total_latency_seconds"], 1.7)

    @patch("src.agents.planner.completion")
    @patch("src.agents.executor.completion")
    def test_orchestrator_mocked_run(self, mock_executor_completion, mock_planner_completion):
        workspace = "/tmp/test_router_workspace"
        os.makedirs(workspace, exist_ok=True)

        mock_planner_resp = MagicMock()
        mock_planner_resp.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "goal": "Mock Goal",
                "target_files": ["test.py"],
                "acceptance_criteria": ["test.py exists"],
                "step_by_step_plan": ["Write test.py"]
            })))
        ]
        mock_planner_resp.usage = MagicMock(prompt_tokens=50, completion_tokens=30)
        mock_planner_completion.return_value = mock_planner_resp

        mock_executor_resp = MagicMock()
        mock_executor_resp.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "summary": "Created test.py",
                "actions": [
                    {"type": "apply_patch", "file_path": "test.py", "content": "print('ok')"}
                ],
                "verification_results": ["File created"]
            })))
        ]
        mock_executor_resp.usage = MagicMock(prompt_tokens=80, completion_tokens=40)
        mock_executor_completion.return_value = mock_executor_resp

        orchestrator = DualLLMRouterOrchestrator(workspace_root=workspace)
        result = orchestrator.run("Create a test file", execute_tools=True)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["task_spec"]["goal"], "Mock Goal")
        self.assertTrue(result["executor_result"]["success"])
        self.assertTrue(result["executor_result"]["verification_report"]["criteria_passed"])
        self.assertEqual(result["metrics"]["total_calls"], 2)

    @patch("src.agents.planner.completion")
    def test_orchestrator_planning_failure(self, mock_planner_completion):
        mock_planner_completion.side_effect = Exception("OpenRouter API 500 error")

        orchestrator = DualLLMRouterOrchestrator(workspace_root="/tmp/test_router_workspace")
        result = orchestrator.run("Create test file")

        self.assertEqual(result["status"], "planning_failed")
        self.assertIn("OpenRouter API 500 error", result["error"])
        self.assertIsNone(result["task_spec"])

    @patch("src.agents.planner.completion")
    @patch("src.agents.executor.completion")
    def test_orchestrator_execution_failure(self, mock_executor_completion, mock_planner_completion):
        mock_planner_resp = MagicMock()
        mock_planner_resp.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "goal": "Mock Goal",
                "target_files": ["missing.py"],
                "acceptance_criteria": ["missing.py exists"],
                "step_by_step_plan": ["Do nothing"]
            })))
        ]
        mock_planner_completion.return_value = mock_planner_resp
        mock_executor_completion.side_effect = Exception("Execution network error")

        orchestrator = DualLLMRouterOrchestrator(workspace_root="/tmp/test_router_workspace")
        result = orchestrator.run("Create test file")

        self.assertEqual(result["status"], "execution_failed")
        self.assertIn("Execution network error", result["error"])
        self.assertEqual(result["task_spec"]["goal"], "Mock Goal")

if __name__ == "__main__":
    unittest.main()
