# Task-Level Metrics

| Category | Metric | Formula | Why It Matters |
| --- | --- | --- | --- |
| Quality | Code Quality Score | LLM-scored (0-1) or heuristic (cyclomatic, bugs) | Does the output actually work? |
| Quality | Test Coverage | tests_passed / tests_run | Reliability |
| Quality | Acceptance Criteria Pass | Boolean (pass/fail) | Did we meet the spec? |
| Efficiency | Executor Iterations | count of executor calls | Fewer = better specs |
| Efficiency | Time-to-Complete | wall-clock seconds | Speed |
| Cost | Token Cost | total tokens / 1M tokens * $rate | Money |
| Cost | Cost Efficiency | expected_cost / actual_cost | Budget adherence |
| Reliability | Success Rate | successful_runs / total_runs | Trust |
| Reliability | Failure Mode | Categorize failures (spec unclear, executor error, etc.) | Debugging |
