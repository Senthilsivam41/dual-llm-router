# Graph Report - dual-llm-router  (2026-10-03)

## Corpus Check
- 126 files · ~31,581 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 670 nodes · 1232 edges · 69 communities (43 shown, 26 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 38 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `24bcb0b3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_p1_functionality.py
- BenchmarkRunner
- EvolutionEngine
- test_p0_security.py
- evolution_engine.py
- ABTestManager
- benchmark_publisher.py
- BenchmarkDashboard
- apply_prompt_mutation
- add
- EvolvingRouter
- reset.py
- Dual-LLM Router
- Metrics & Benchmarking Guide
- Benchmark CI/CD — feasibility & implementation
- Benchmark Results — 2026-08-01T07:52:36.396339Z
- Benchmark Results — 2026-08-01T08:44:07.092711Z
- Benchmark Results — 2026-08-01T08:45:11.492151Z
- Benchmark Results — 2026-08-01T08:45:11.492151Z
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
- Published Benchmark Results
- full_benchmark.sh
- minimal_setup.sh
- Benchmark Suite
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

## God Nodes (most connected - your core abstractions)
1. `EvolutionEngine` - 68 edges
2. `BenchmarkRunner` - 35 edges
3. `BenchmarkDashboard` - 21 edges
4. `EvolvingRouter` - 20 edges
5. `BenchmarkTask` - 18 edges
6. `DualLLMRouterOrchestrator` - 18 edges
7. `TaskSpec` - 17 edges
8. `MetricsLogger` - 17 edges
9. `ExecutorAgent` - 16 edges
10. `publish_results()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `BenchmarkTask` --uses--> `EvolvingRouter`  [INFERRED]
  evals/benchmark_runner.py → router/router.py
- `BenchmarkResult` --uses--> `EvolvingRouter`  [INFERRED]
  evals/benchmark_runner.py → router/router.py
- `BenchmarkRunner` --uses--> `EvolvingRouter`  [INFERRED]
  evals/benchmark_runner.py → router/router.py
- `CoEvolver` --uses--> `EvolutionEngine`  [INFERRED]
  router/evolver.py → evals/evolution_engine.py
- `DualLLMRouter` --uses--> `EvolutionEngine`  [INFERRED]
  router/router.py → evals/evolution_engine.py

## Import Cycles
- None detected.

## Communities (69 total, 26 thin omitted)

### Community 0 - "test_p1_functionality.py"
Cohesion: 0.06
Nodes (52): main(), Example execution entrypoint for the Dual-LLM Router framework., patch, Router package: Dual-LLM orchestration + co-evolution integration., DualLLMRouter, Prompt, Dual-LLM router with optional co-evolution integration., Public router entrypoint used by scripts and evolution. (+44 more)

### Community 1 - "BenchmarkRunner"
Cohesion: 0.08
Nodes (32): load_task_modules(), Any, Load benchmark task definitions from benchmark/{easy,medium,hard,extreme}/., Import TASK dicts from category packages., task_to_jsonable(), BenchmarkResult, BenchmarkRunner, BenchmarkTask (+24 more)

### Community 2 - "EvolutionEngine"
Cohesion: 0.08
Nodes (23): EvolutionEngine, Manages the full evolution loop for dual-llm-router. Flow: 1. After every run,…, Record a run result after execution. Called after every dual-llm-router run., Assign the least-sampled variant from an active observed-run test., Record only observed run outcomes in active A/B tests., Check if it's time to evolve., Evaluate fitness of current active variants., Main evolution function. (+15 more)

### Community 3 - "test_p0_security.py"
Cohesion: 0.07
Nodes (38): ActionModel, Enum, field_validator, parametrize, ActionType, PatchAction, Any, BaseModel (+30 more)

### Community 4 - "evolution_engine.py"
Cohesion: 0.10
Nodes (33): Core evolution engine for dual-llm-router co-evolution. Manages the full…, Canonical filesystem paths for evolution state under .autoclaw/., append_run_result(), _atomic_write_json(), calculate_fitness(), _exclusive_file_lock(), get_top_variants(), _load_run_document() (+25 more)

### Community 5 - "ABTestManager"
Cohesion: 0.10
Nodes (21): ABTestManager, A/B testing framework for comparing variant combinations., Get status of all active tests., Manages A/B tests for dual-llm-router variants. Tracks: - Variant…, Start a new A/B test., Record a result for a variant in an A/B test., Check if an A/B test reached statistical significance., Simplified significance calculation. (+13 more)

### Community 6 - "benchmark_publisher.py"
Cohesion: 0.16
Nodes (22): datetime, changed_files(), _git(), git_metadata(), is_major_change(), publish_results(), Any, Path (+14 more)

### Community 7 - "BenchmarkDashboard"
Cohesion: 0.17
Nodes (9): BenchmarkDashboard, Path, Generate benchmark reports and console dashboards., Generate benchmark reports and visualizations., Render a compact Markdown summary for GitHub Actions step summaries., _utc_now(), main(), _append_summary() (+1 more)

### Community 8 - "apply_prompt_mutation"
Cohesion: 0.14
Nodes (15): _load_yaml_evolution_config(), Any, Path, Create a new mutated genome for hermes or laguna., Read prompt text from a .py module or plain text file., _read_prompt_text(), _write_prompt_module(), apply_prompt_mutation() (+7 more)

### Community 9 - "add"
Cohesion: 0.16
Nodes (10): add(), Add two numbers and return the result. Args: a: The first number. b: The second…, Test addition of two positive numbers., Test addition of two negative numbers., Test addition of a positive and a negative number., Test addition involving zero., Test addition of floating point numbers., Test addition of large numbers. (+2 more)

### Community 10 - "EvolvingRouter"
Cohesion: 0.16
Nodes (9): CoEvolver, Any, Path, Bridge between router runs and the evolution engine., EvolvingRouter, Any, Load prompt for a specific variant., Router with built-in Hermes/Laguna co-evolution. (+1 more)

### Community 11 - "reset.py"
Cohesion: 0.22
Nodes (8): Current Hermes 4 planner system prompt (v1 baseline)., Current Laguna S 2.1 executor system prompt (v1 baseline)., _genome(), main(), Path, reset_state(), _utc_now(), _write()

### Community 12 - "Dual-LLM Router"
Cohesion: 0.17
Nodes (12): Architecture, Benchmarks, Co-evolution loop, Cron (optional), Design notes, Dual-LLM Router, How a run is scored, Quick start (+4 more)

### Community 14 - "Metrics & Benchmarking Guide"
Cohesion: 0.20
Nodes (10): 1. Metrics to measure, 2. Progressive benchmark suite, 3. Execution & reporting stack, 4. Scoring integration, 5. Quick start, 6. Targets cheat sheet, 7. Adding a task, A. Task-level (per run) (+2 more)

### Community 15 - "Benchmark CI/CD — feasibility & implementation"
Cohesion: 0.22
Nodes (9): Benchmark CI/CD — feasibility & implementation, CLI contracts (this repo), Expected artifacts, Feasibility verdict, Job map (`benchmark.yml`), Local dry-run (mirrors CI), Secrets (optional), What we intentionally did not copy (+1 more)

### Community 16 - "Benchmark Results — 2026-08-01T07:52:36.396339Z"
Cohesion: 0.22
Nodes (9): Artifacts, Benchmark Results — 2026-08-01T07:52:36.396339Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 17 - "Benchmark Results — 2026-08-01T08:44:07.092711Z"
Cohesion: 0.22
Nodes (9): Artifacts, Benchmark Results — 2026-08-01T08:44:07.092711Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 18 - "Benchmark Results — 2026-08-01T08:45:11.492151Z"
Cohesion: 0.22
Nodes (9): Artifacts, Benchmark Results — 2026-08-01T08:45:11.492151Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

### Community 19 - "Benchmark Results — 2026-08-01T08:45:11.492151Z"
Cohesion: 0.22
Nodes (9): Artifacts, Benchmark Results — 2026-08-01T08:45:11.492151Z, By category, By domain, By variant combo, Overall metrics, Per-task results, Run metadata (+1 more)

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
Cohesion: 0.25
Nodes (8): Alerting, CLI, Cron (Phase 5), Dual-LLM Router Prompt Evolution, Goals, Implementation checklist, Layout, Lifecycle

### Community 24 - "Agent conventions — memory & Codegraph"
Cohesion: 0.25
Nodes (6): Agent conventions — memory & Codegraph, Codebase-memory MCP (optional shareable graph), Codegraph (required when available), Memory folder, Related paths, Project memory

### Community 25 - "Current status"
Cohesion: 0.25
Nodes (8): CI/CD, Current status, Indexes (2026-08-01), Known gaps, Portfolio productization (2026-08-25), Product shape, Shipped on this branch (recent), Verification snapshot

### Community 26 - "benchmark_publishing_results.md"
Cohesion: 0.29
Nodes (3): Key Metrics Summary, System-Level Metrics, Task-Level Metrics

### Community 28 - "Quickstart"
Cohesion: 0.29
Nodes (7): Five-minute demo (no API key), Live path (optional), More, Prerequisites, Quality gate, Quickstart, Setup

### Community 29 - "Future changes"
Cohesion: 0.33
Nodes (6): Future changes, P0 — Merge & CI hygiene, P1 — Live evaluation quality, P2 — Evolution productization, P3 — Docs / polish, Process (always)

### Community 30 - "Architecture"
Cohesion: 0.40
Nodes (5): Architecture, Co-evolution loop, Ecosystem role, Evaluation surface, Runtime pipeline

### Community 31 - "Configuration"
Cohesion: 0.40
Nodes (5): Benchmarks, Configuration, Environment, Evolution, Portfolio commands

### Community 32 - "Published Benchmark Results"
Cohesion: 0.50
Nodes (4): Published Benchmark Results, Reading results, Standard, When results are published

### Community 35 - "Benchmark Suite"
Cohesion: 0.67
Nodes (3): Benchmark Suite, Published reports (standard), Quick start

## Knowledge Gaps
- **132 isolated node(s):** `full_benchmark.sh script`, `PYTHONPATH`, `minimal_setup.sh script`, `PYTHONPATH`, `dual-llm-router` (+127 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EvolutionEngine` connect `EvolutionEngine` to `test_p1_functionality.py`, `BenchmarkRunner`, `evolution_engine.py`, `ABTestManager`, `benchmark_publisher.py`, `apply_prompt_mutation`, `EvolvingRouter`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `EvolvingRouter` connect `EvolvingRouter` to `test_p1_functionality.py`, `BenchmarkRunner`, `EvolutionEngine`, `evolution_engine.py`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `DualLLMRouterOrchestrator` connect `test_p1_functionality.py` to `EvolvingRouter`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `EvolutionEngine` (e.g. with `BenchmarkResult` and `BenchmarkRunner`) actually correct?**
  _`EvolutionEngine` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `BenchmarkRunner` (e.g. with `EvolutionEngine` and `EvolvingRouter`) actually correct?**
  _`BenchmarkRunner` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `EvolvingRouter` (e.g. with `BenchmarkResult` and `BenchmarkRunner`) actually correct?**
  _`EvolvingRouter` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `BenchmarkTask` (e.g. with `EvolutionEngine` and `EvolvingRouter`) actually correct?**
  _`BenchmarkTask` has 2 INFERRED edges - model-reasoned connections that need verification._