# Graph Report - dual-llm-router  (2026-11-12)

## Corpus Check
- 210 files · ~75,758 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1258 nodes · 2562 edges · 113 communities (82 shown, 31 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b39d7f6a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_p1_functionality.py
- BenchmarkRunner
- EvolutionEngine
- test_p0_security.py
- evals/__init__.py
- TaskSpec
- BenchmarkDashboard
- session.py
- executor.py
- add
- EvolvingRouter
- DualLLMRouterOrchestrator
- Dual-LLM Router
- STATUS.md
- Metrics & Benchmarking Guide
- Benchmark CI/CD — feasibility & implementation
- Benchmark Results — 2026-08-01T07:52:36.396339Z
- Benchmark Results — 2026-08-01T08:44:07.092711Z
- Benchmark Results — 2026-08-01T08:45:11.492151Z
- Benchmark Results — 2026-10-25T07:15:43.118109Z
- Project Proposal: Dual-LLM Agentic Framework — Planner/Executor Split (Hermes 4 + Laguna S 2.1)
- Benchmark Results — 2026-08-01T07:36:58.134222Z
- Benchmark Results — 2026-08-01T07:39:21.934091Z
- Dual-LLM Router Prompt Evolution
- Agent conventions — memory & Codegraph
- Current status
- benchmark_publishing_results.md
- INDEX.md
- Quickstart
- Future changes
- Architecture
- Configuration
- action_schemas.py
- full_benchmark.sh
- minimal_setup.sh
- test_issue_to_fix.py
- system.py
- hermes/few_shot/coding_examples.py
- laguna/few_shot/coding_examples.py
- cron_evolve.sh
- co-evaluation-tracking.md
- basic_function.py
- file_creation.py
- simple_function.py
- simple_refactor.py
- multi_service.py
- performance_critical.py
- security_audit.py
- architecture_change.py
- bug_hunt.py
- feature_from_scratch.py
- performance_optimization.py
- api_endpoint.py
- calculator_class.py
- multi_file_feature.py
- test_coverage.py
- prompts/__init__.py
- src/__init__.py
- dual-llm-router
- runner.py
- apply_patch
- Benchmark Results — 2026-08-01T08:52:51.156392Z
- Benchmark Results — 2026-08-02T05:27:59.464453Z
- Benchmark Results — 2026-08-09T03:39:56.336385Z
- Benchmark Results — 2026-08-11T15:57:03.662076Z
- Benchmark Results — 2026-08-11T16:08:23.322244Z
- Benchmark Results — 2026-08-16T02:57:47.656796Z
- Benchmark Results — 2026-08-23T03:00:00.747348Z
- Benchmark Results — 2026-08-25T02:17:00.773187Z
- Benchmark Results — 2026-09-06T06:50:17.518280Z
- Benchmark Results — 2026-09-13T07:09:35.348146Z
- Benchmark Results — 2026-09-20T07:25:59.405103Z
- Benchmark Results — 2026-09-27T07:34:48.191581Z
- Benchmark Results — 2026-10-03T10:53:46.882948Z
- Benchmark Results — 2026-10-11T08:16:39.722209Z
- Benchmark Results — 2026-10-18T06:57:01.050795Z
- Benchmark Results — 2026-10-25T07:15:43.118109Z
- workspace_acceptance.py
- Benchmark Results — 2026-08-30T07:51:09.169719Z
- Benchmark Results — 2026-10-04T07:45:03.873959Z
- config.py
- Invoice total is wrong
- billing.py
- billing_coupon.py
- showcase_success_rate.md
- verification/__init__.py
- evals/fitness_dashboard.py
- evaluate_promotion
- calculate_fitness
- study.py
- reset.py
- test_weekly_summary.py
- evolution_engine.py
- ABTestManager
- invoice_total
- Invoice total is wrong
- ADR 0001: Careful genome promotion
- Benchmark Suite
- run_shell
- Invoice reconciliation feedback benchmark
- feedback.py
- .__init__
- reconciliation/__init__.py

## God Nodes (most connected - your core abstractions)
1. `EvolutionEngine` - 100 edges
2. `BenchmarkRunner` - 38 edges
3. `TaskSpec` - 33 edges
4. `DualLLMRouterOrchestrator` - 32 edges
5. `MetricsLogger` - 26 edges
6. `evaluate_promotion()` - 25 edges
7. `BenchmarkDashboard` - 21 edges
8. `publish_results()` - 21 edges
9. `BenchmarkTask` - 21 edges
10. `EvolvingRouter` - 20 edges

## Surprising Connections (you probably didn't know these)
- `test_ab_test_reaches_significance()` --calls--> `ABTestManager`  [EXTRACTED]
  tests/test_ab_test.py → evals/ab_test.py
- `BenchmarkTask` --uses--> `EvolvingRouter`  [INFERRED]
  evals/benchmark_runner.py → router/router.py
- `BenchmarkResult` --uses--> `EvolvingRouter`  [INFERRED]
  evals/benchmark_runner.py → router/router.py
- `BenchmarkRunner` --uses--> `EvolvingRouter`  [INFERRED]
  evals/benchmark_runner.py → router/router.py
- `CoEvolver` --uses--> `EvolutionEngine`  [INFERRED]
  router/evolver.py → evals/evolution_engine.py

## Import Cycles
- None detected.

## Communities (113 total, 31 thin omitted)

### Community 0 - "test_p1_functionality.py"
Cohesion: 0.16
Nodes (17): PlannerAgent, completion_response(), planner_response(), SimpleNamespace, Implemented planner, executor, orchestrator, and router behavior. These tests…, task_spec(), test_evolving_router_records_only_observed_quality_metrics(), test_executor_fails_when_litellm_is_unavailable() (+9 more)

### Community 1 - "BenchmarkRunner"
Cohesion: 0.06
Nodes (48): load_task_modules(), Any, Load benchmark task definitions from benchmark/{easy,medium,hard,extreme}/., Import TASK dicts from category packages., task_to_jsonable(), BenchmarkResult, BenchmarkRunner, BenchmarkTask (+40 more)

### Community 2 - "EvolutionEngine"
Cohesion: 0.09
Nodes (14): EvolutionEngine, Manages the full evolution loop for dual-llm-router. Flow: 1. After every run,…, Record a run result after execution. Called after every dual-llm-router run., Assign the least-sampled variant from an active observed-run test., Record only observed run outcomes in active A/B tests., Check if it's time to evolve., Evaluate fitness of current active variants., Main evolution function. (+6 more)

### Community 3 - "test_p0_security.py"
Cohesion: 0.38
Nodes (13): patch, ExecutorAgent, completion_response(), SimpleNamespace, task_spec(), test_action_batch_is_validated_before_any_action_executes(), test_default_agents_use_fireworks_credentials(), test_executor_dispatches_a_valid_shell_action() (+5 more)

### Community 4 - "evals/__init__.py"
Cohesion: 0.14
Nodes (24): Prompt evolution: scoring, mutation, A/B testing, and lineage tracking., append_run_result(), _atomic_write_json(), _exclusive_file_lock(), _load_run_document(), load_run_results(), _path_lock(), Path (+16 more)

### Community 5 - "TaskSpec"
Cohesion: 0.14
Nodes (18): model_validator, Check, BaseModel, field_validator, One expected value the executor's tests must assert., TaskSpec, expected_amounts(), planner_accuracy() (+10 more)

### Community 6 - "BenchmarkDashboard"
Cohesion: 0.08
Nodes (37): datetime, BenchmarkDashboard, Path, Generate benchmark reports and console dashboards., Render a compact Markdown summary for GitHub Actions step summaries., Generate benchmark reports and visualizations., _utc_now(), changed_files() (+29 more)

### Community 7 - "session.py"
Cohesion: 0.14
Nodes (31): main(), Issue-to-fix showcase commands., build_run_record(), costs_by_role(), publish_success_rate(), Any, Path, Terminal, HTML, and Markdown reports for an issue-to-fix run. (+23 more)

### Community 8 - "executor.py"
Cohesion: 0.15
Nodes (26): RuntimeError, _is_file_existence_criterion(), _is_safe_action_criterion(), Return whether a criterion is an objective file-existence assertion., Recognize criteria directly proven by validated tool execution., build_planner_user_message(), Any, Give the planner the bug report, the file list, and a prior validation error. (+18 more)

### Community 9 - "add"
Cohesion: 0.16
Nodes (10): add(), Add two numbers and return the result. Args: a: The first number. b: The second…, Test addition of two positive numbers., Test addition of two negative numbers., Test addition of a positive and a negative number., Test addition involving zero., Test addition of floating point numbers., Test addition of large numbers. (+2 more)

### Community 10 - "EvolvingRouter"
Cohesion: 0.12
Nodes (16): CoEvolver, Any, Path, Co-evolution integration point for DualLLMRouter., Bridge between router runs and the evolution engine., Router package: Dual-LLM orchestration + co-evolution integration., DualLLMRouter, EvolvingRouter (+8 more)

### Community 11 - "DualLLMRouterOrchestrator"
Cohesion: 0.11
Nodes (13): main(), Example execution entrypoint for the Dual-LLM Router framework., DualLLMRouterOrchestrator, Any, Path, Runs Planner node -> Executor node pipeline sequentially., Execute an accepted plan, optionally continuing a previous attempt., CallMetric (+5 more)

### Community 12 - "Dual-LLM Router"
Cohesion: 0.14
Nodes (14): Architecture, Benchmarks, Co-evolution loop, Cron (optional), Design notes, Dual-LLM Router, How a run is scored, Invoice reconciliation (+6 more)

### Community 13 - "STATUS.md"
Cohesion: 0.23
Nodes (3): Fitness dashboard, Promoted genomes, Invoice reconciliation

### Community 14 - "Metrics & Benchmarking Guide"
Cohesion: 0.20
Nodes (10): 1. Metrics to measure, 2. Progressive benchmark suite, 3. Execution & reporting stack, 4. Scoring integration, 5. Quick start, 6. Targets cheat sheet, 7. Adding a task, A. Task-level (per run) (+2 more)

### Community 15 - "Benchmark CI/CD — feasibility & implementation"
Cohesion: 0.22
Nodes (9): Benchmark CI/CD — feasibility & implementation, CLI contracts (this repo), Expected artifacts, Feasibility verdict, Job map (`benchmark.yml`), Local dry-run (mirrors CI), Secrets (optional), What we intentionally did not copy (+1 more)

### Community 16 - "Benchmark Results — 2026-08-01T07:52:36.396339Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-01T07:52:36.396339Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 17 - "Benchmark Results — 2026-08-01T08:44:07.092711Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-01T08:44:07.092711Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 18 - "Benchmark Results — 2026-08-01T08:45:11.492151Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-01T08:45:11.492151Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 19 - "Benchmark Results — 2026-10-25T07:15:43.118109Z"
Cohesion: 0.22
Nodes (9): Artifacts, Benchmark Results — 2026-10-25T07:15:43.118109Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 20 - "Project Proposal: Dual-LLM Agentic Framework — Planner/Executor Split (Hermes 4 + Laguna S 2.1)"
Cohesion: 0.22
Nodes (9): 1. Objective, 2. Motivation, 3. Scope, 4. Proposed Architecture, 5. Milestones, 6. Success Criteria, 7. Risks & Open Questions, 8. Next Steps (+1 more)

### Community 21 - "Benchmark Results — 2026-08-01T07:36:58.134222Z"
Cohesion: 0.25
Nodes (7): Artifacts, Benchmark Results — 2026-08-01T07:36:58.134222Z, By category, By variant combo, Overall metrics, Per-task results, Run metadata

### Community 22 - "Benchmark Results — 2026-08-01T07:39:21.934091Z"
Cohesion: 0.25
Nodes (7): Artifacts, Benchmark Results — 2026-08-01T07:39:21.934091Z, By category, By variant combo, Overall metrics, Per-task results, Run metadata

### Community 23 - "Dual-LLM Router Prompt Evolution"
Cohesion: 0.22
Nodes (9): Alerting, CI schedules, CLI, Cron (Phase 5), Dual-LLM Router Prompt Evolution, Goals, Implementation checklist, Layout (+1 more)

### Community 24 - "Agent conventions — memory & Codegraph"
Cohesion: 0.25
Nodes (6): Agent conventions — memory & Codegraph, Codebase-memory MCP (optional shareable graph), Codegraph (required when available), Memory folder, Related paths, Project memory

### Community 25 - "Current status"
Cohesion: 0.25
Nodes (8): CI/CD, Current status, Indexes (2026-08-01), Known gaps, Portfolio productization (2026-08-25), Product shape, Shipped on this branch (recent), Verification snapshot

### Community 26 - "benchmark_publishing_results.md"
Cohesion: 0.29
Nodes (3): Key Metrics Summary, System-Level Metrics, Task-Level Metrics

### Community 27 - "INDEX.md"
Cohesion: 0.29
Nodes (5): Published Benchmark Results, Published Benchmark Results, Reading results, Standard, When results are published

### Community 28 - "Quickstart"
Cohesion: 0.29
Nodes (7): Five-minute demo (no API key), Live path (optional), More, Prerequisites, Quality gate, Quickstart, Setup

### Community 29 - "Future changes"
Cohesion: 0.33
Nodes (6): Future changes, P0 — Merge & CI hygiene, P1 — Live evaluation quality, P2 — Evolution productization, P3 — Docs / polish, Process (always)

### Community 30 - "Architecture"
Cohesion: 0.25
Nodes (8): Architecture, Co-evolution loop, Ecosystem role, Evaluation surface, Feedback within a run, Layers and their responsibilities, Runtime pipeline, Tool selection and dispatch

### Community 31 - "Configuration"
Cohesion: 0.40
Nodes (5): Benchmarks, Configuration, Environment, Evolution, Portfolio commands

### Community 32 - "action_schemas.py"
Cohesion: 0.17
Nodes (13): ActionModel, Enum, parametrize, ActionType, PatchAction, Any, BaseModel, field_validator (+5 more)

### Community 35 - "test_issue_to_fix.py"
Cohesion: 0.16
Nodes (20): filename_from_seed_comment(), Path, Write benchmark and showcase seed files under their real paths., Use a leading `# module.py` comment as the filename. Older tasks stored that…, write_legacy_seed(), write_seed_files(), load_billing(), Path (+12 more)

### Community 69 - "runner.py"
Cohesion: 0.35
Nodes (12): _copy_workspace(), _docker_can_import_pytest(), _docker_image(), Path, PytestOutcome, Run executor-written pytest in a restricted subprocess, or Docker when it can., Pick docker only when it is requested or the image can import pytest., _restricted_env() (+4 more)

### Community 70 - "apply_patch"
Cohesion: 0.22
Nodes (8): apply_patch(), Any, Write a file through pinned directory descriptors without following symlinks., _secure_open_flags(), test_apply_patch_never_follows_final_symlink_inside_workspace(), test_apply_patch_rejects_absolute_paths(), test_apply_patch_rejects_parent_directory_traversal(), test_apply_patch_rejects_symlink_escape()

### Community 71 - "Benchmark Results — 2026-08-01T08:52:51.156392Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-01T08:52:51.156392Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 72 - "Benchmark Results — 2026-08-02T05:27:59.464453Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-02T05:27:59.464453Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 73 - "Benchmark Results — 2026-08-09T03:39:56.336385Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-09T03:39:56.336385Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 74 - "Benchmark Results — 2026-08-11T15:57:03.662076Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-11T15:57:03.662076Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 75 - "Benchmark Results — 2026-08-11T16:08:23.322244Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-11T16:08:23.322244Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 76 - "Benchmark Results — 2026-08-16T02:57:47.656796Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-16T02:57:47.656796Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 77 - "Benchmark Results — 2026-08-23T03:00:00.747348Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-23T03:00:00.747348Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 78 - "Benchmark Results — 2026-08-25T02:17:00.773187Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-25T02:17:00.773187Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 79 - "Benchmark Results — 2026-09-06T06:50:17.518280Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-09-06T06:50:17.518280Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 80 - "Benchmark Results — 2026-09-13T07:09:35.348146Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-09-13T07:09:35.348146Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 81 - "Benchmark Results — 2026-09-20T07:25:59.405103Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-09-20T07:25:59.405103Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 82 - "Benchmark Results — 2026-09-27T07:34:48.191581Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-09-27T07:34:48.191581Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 83 - "Benchmark Results — 2026-10-03T10:53:46.882948Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-10-03T10:53:46.882948Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 84 - "Benchmark Results — 2026-10-11T08:16:39.722209Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-10-11T08:16:39.722209Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 85 - "Benchmark Results — 2026-10-18T06:57:01.050795Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-10-18T06:57:01.050795Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 86 - "Benchmark Results — 2026-10-25T07:15:43.118109Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-10-25T07:15:43.118109Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 87 - "workspace_acceptance.py"
Cohesion: 0.12
Nodes (31): AST, _collected_tests(), expected_numbers(), _file_existence_target(), _is_pytest_criterion(), _judge_criterion(), Any, Decimal (+23 more)

### Community 88 - "Benchmark Results — 2026-08-30T07:51:09.169719Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-08-30T07:51:09.169719Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 89 - "Benchmark Results — 2026-10-04T07:45:03.873959Z"
Cohesion: 0.20
Nodes (9): Artifacts, Benchmark Results — 2026-10-04T07:45:03.873959Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 90 - "config.py"
Cohesion: 0.29
Nodes (5): fixture, Config, fireworks_test_credentials(), Point the suite at Fireworks when that key is configured., Use FIREWORKS_API_KEY for default planner and executor models. A dummy key is…

### Community 91 - "Invoice total is wrong"
Cohesion: 0.50
Nodes (3): Case 1 — coupon applied after tax, Case 2 — per-line rounding, Invoice total is wrong

### Community 96 - "evals/fitness_dashboard.py"
Cohesion: 0.15
Nodes (26): build_fitness_report(), dashboard_dir_for(), _esc(), fitness_fingerprint(), _metric_table(), Any, Path, Durable fitness trend report. The console summary in scripts/analyze.py stays. (+18 more)

### Community 97 - "evaluate_promotion"
Cohesion: 0.17
Nodes (34): _agent_row(), apply_promotion(), _challenger_block(), evaluate_promotion(), _load_latest(), _pair_fitness(), promotion_dir_for(), _prompt_sha256() (+26 more)

### Community 98 - "calculate_fitness"
Cohesion: 0.20
Nodes (16): calculate_fitness(), get_top_variants(), Calculate composite fitness score for a (hermes, laguna) pair. Returns weighted…, Get top N variant combinations by composite score., Path, Create an isolated project root with prompts + .autoclaw baselines., _rich_run(), _seed_project() (+8 more)

### Community 99 - "study.py"
Cohesion: 0.07
Nodes (69): Namespace, _arguments(), _live(), main(), Path, _amount(), _case(), _csv() (+61 more)

### Community 100 - "reset.py"
Cohesion: 0.22
Nodes (8): Current Hermes 4 planner system prompt (v1 baseline)., Current Laguna S 2.1 executor system prompt (v1 baseline)., _genome(), main(), Path, reset_state(), _utc_now(), _write()

### Community 101 - "test_weekly_summary.py"
Cohesion: 0.10
Nodes (32): _append_alert_log(), detect_significant_improvement(), emit_alerts(), post_json_webhook(), _post_webhook(), Any, Path, Alerting for significant evolution improvements. (+24 more)

### Community 102 - "evolution_engine.py"
Cohesion: 0.14
Nodes (17): _load_yaml_evolution_config(), Any, Path, Core evolution engine for dual-llm-router co-evolution. Manages the full…, Read prompt text from a .py module or plain text file., _read_prompt_text(), _write_prompt_module(), apply_prompt_mutation() (+9 more)

### Community 103 - "ABTestManager"
Cohesion: 0.15
Nodes (9): ABTestManager, A/B testing framework for comparing variant combinations., Get status of all active tests., Manages A/B tests for dual-llm-router variants. Tracks: - Variant…, Start a new A/B test., Record a result for a variant in an A/B test., Check if an A/B test reached statistical significance., Simplified significance calculation. (+1 more)

### Community 104 - "invoice_total"
Cohesion: 0.39
Nodes (6): invoice_total(), Invoice totals. `invoice_total` charges a fixed coupon and an optional tax…, test_coupon_applied_before_tax(), test_coupon_exceeds_subtotal(), test_half_cent_rounds_up(), test_no_per_line_rounding()

### Community 105 - "Invoice total is wrong"
Cohesion: 0.50
Nodes (3): Case 1 — coupon applied after tax, Case 2 — per-line rounding, Invoice total is wrong

### Community 106 - "ADR 0001: Careful genome promotion"
Cohesion: 0.40
Nodes (5): ADR 0001: Careful genome promotion, Alternatives considered, Consequences, Context, Decision

### Community 107 - "Benchmark Suite"
Cohesion: 0.67
Nodes (3): Benchmark Suite, Published reports (standard), Quick start

### Community 108 - "run_shell"
Cohesion: 0.24
Nodes (9): _is_within_workspace(), Any, Check if a path is within the workspace root (resolves symlinks)., Return an error when a command argument can address outside the workspace., Execute a capability-limited command inside workspace root. Security features:…, run_shell(), _validate_command_paths(), test_run_shell_cannot_read_above_workspace() (+1 more)

### Community 109 - "Invoice reconciliation feedback benchmark"
Cohesion: 0.40
Nodes (4): Gains and regressions by family, Invoice reconciliation feedback benchmark, Paired comparisons, Pricing sources

### Community 110 - "feedback.py"
Cohesion: 0.67
Nodes (3): build_executor_feedback(), Feedback handed to the executor on the next attempt. The plan stays fixed., workspace_snapshot()

## Knowledge Gaps
- **295 isolated node(s):** `full_benchmark.sh script`, `PYTHONPATH`, `minimal_setup.sh script`, `PYTHONPATH`, `dual-llm-router` (+290 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EvolutionEngine` connect `EvolutionEngine` to `evals/fitness_dashboard.py`, `BenchmarkRunner`, `evaluate_promotion`, `study.py`, `evals/__init__.py`, `test_weekly_summary.py`, `evolution_engine.py`, `ABTestManager`, `BenchmarkDashboard`, `calculate_fitness`, `EvolvingRouter`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Why does `TaskSpec` connect `TaskSpec` to `test_p1_functionality.py`, `study.py`, `test_issue_to_fix.py`, `test_p0_security.py`, `executor.py`, `DualLLMRouterOrchestrator`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `compare_output()` connect `study.py` to `add`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `EvolutionEngine` (e.g. with `BenchmarkResult` and `BenchmarkRunner`) actually correct?**
  _`EvolutionEngine` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `BenchmarkRunner` (e.g. with `EvolutionEngine` and `EvolvingRouter`) actually correct?**
  _`BenchmarkRunner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `TaskSpec` (e.g. with `TrialRunner` and `TestDualLLMRouter`) actually correct?**
  _`TaskSpec` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `DualLLMRouterOrchestrator` (e.g. with `DualLLMRouter` and `EvolvingRouter`) actually correct?**
  _`DualLLMRouterOrchestrator` has 5 INFERRED edges - model-reasoned connections that need verification._