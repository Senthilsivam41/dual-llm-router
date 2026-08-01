# Dual-LLM Router — Planner/Executor Split (Hermes 4 + Laguna S 2.1)

Prompt co-evolution docs: [`docs/Evolution.md`](docs/Evolution.md)

---

# Project Proposal: Dual-LLM Agentic Framework — Planner/Executor Split (Hermes 4 + Laguna S 2.1)

**Prepared by:** Sendil Sadasivam
**Date:** July 2026
**Context:** GenAI hobby/learning track, extending the Polaris Neuro Guard multi-agent architecture

---

## 1. Objective

Stand up an open-source agent framework that pairs two purpose-fit LLMs behind a single orchestration graph:

- **Hermes 4** — planning, routing, structured JSON/tool-call decisions, user-facing dialogue
- **Laguna S 2.1** — long-horizon agentic coding and tool execution (patches, terminal, multi-file work)

Goal is to validate a **role-specialized dual-model pattern** (rather than a single general-purpose model) as a reusable building block for Polaris Neuro Guard's ADK 2.0 multi-agent graph, and as a standalone reference implementation others can fork.

## 2. Motivation

A single model doing both planning and execution forces a tradeoff between cost/latency (planning is frequent, cheap, and structured) and depth (execution needs long context, tool reliability, and sustained reasoning). Splitting these across two models sized for their job is a pattern already proven in Nous Research's own Hermes Agent framework (model-agnostic routing by task type) — this proposal adapts that pattern into ADK 2.0 rather than adopting Hermes Agent wholesale, so it stays consistent with the Polaris Neuro Guard stack.

## 3. Scope

**In scope:**
- Two-node ADK 2.0 pipeline: `planner_agent` (Hermes 4) → `executor_agent` (Laguna S 2.1)
- OpenRouter integration for both models via `LiteLlm`, using the existing OpenRouter API key
- Tool layer: `apply_patch`, `run_shell` (sandboxed), extensible to drift-detection-specific tools later
- Structured task-spec handoff (JSON) between planner and executor
- Basic eval harness: does the executor meet the planner's acceptance criteria, pass/fail logged per run
- Cost/latency logging per model call (OpenRouter usage metadata)

**Out of scope (phase 1):**
- Self-hosted inference for Laguna S 2.1 (stay on OpenRouter until the pattern is validated)
- Loop-back re-planning on failure (start with `SequentialAgent`; upgrade to `LoopAgent` in phase 2 if needed)
- Production deployment / auth / multi-tenant concerns

## 4. Proposed Architecture

```
User/Trigger
     |
     v
[Planner: Hermes 4]  --- emits task_spec (JSON: goal, files, acceptance criteria)
     |
     v
[Executor: Laguna S 2.1]  --- calls apply_patch / run_shell iteratively
     |
     v
Summary + acceptance-criteria check --> back to user
```

- Orchestration: ADK 2.0 `SequentialAgent` wrapping the two `LlmAgent` nodes
- Model access: `LiteLlm` wrapper, OpenRouter as the model provider for both
- Session/state: ADK's built-in `SessionService`, `task_spec` passed via `output_key`
- Sandbox: whatever execution sandbox Polaris Neuro Guard already uses for tool calls, reused here

## 5. Milestones

| Phase | Deliverable | Est. effort |
|---|---|---|
| 1 | Wire planner + executor nodes, validate OpenRouter connectivity for both models | 0.5–1 day |
| 2 | Implement `apply_patch`/`run_shell` against a real sandbox, run end-to-end on a toy repo task | 1–2 days |
| 3 | Add cost/latency logging per node, compare against a single-model (Hermes-only or Laguna-only) baseline | 1 day |
| 4 | Write up findings; decide whether to fold this pattern into Polaris Neuro Guard's ADK 2.0 graph as a reusable sub-agent pair | 0.5 day |

## 6. Success Criteria

- Planner reliably emits valid, parseable `task_spec` JSON (target: >95% of runs, no manual retry)
- Executor completes toy coding tasks end-to-end using only `apply_patch`/`run_shell`, no manual intervention
- Dual-model pattern shows measurable latency/cost benefit over routing everything through Laguna S 2.1 alone for planning-only steps
- Pattern is documented well enough to be lifted directly into Polaris Neuro Guard's multi-agent graph

## 7. Risks & Open Questions

- **Laguna S 2.1 cost on OpenRouter** for iterative tool-calling loops — needs a usage cap/budget check before scaling beyond toy tasks
- **JSON reliability from Hermes 4** under ChatML — worth a quick eval pass with a few adversarial/edge-case prompts before trusting it unguarded
- **Loop-back design** — if executor fails acceptance criteria, decide re-planning strategy (fixed retry count vs. planner-driven replan) before phase 2
- Should this become a **standalone open-source repo** (separate from Polaris Neuro Guard) so it's independently forkable? Recommend yes, given the "reusable reference implementation" goal in Section 1.

## 8. Next Steps

1. Confirm OpenRouter budget/rate limits are sufficient for iterative Laguna S 2.1 tool-calling
2. Scaffold repo structure (reuse `adk_hermes_laguna_agent.py` sketch as the starting point)
3. Run phase 1 milestone, then decide on phase 2 scope based on findings
