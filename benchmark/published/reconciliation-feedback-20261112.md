# Invoice reconciliation feedback benchmark

**Live study · complete**

- Models — planner `fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash`, executor `fireworks_ai/accounts/fireworks/models/glm-5p3-flash`.
- Executed 12 development and 64 evaluation trials.
- Attempted study model calls — 160.
- First attempts eligible for retry — 3.
- Arm cost and timing cover scored trials and include the shared planning step and public verification. Private scoring and study orchestration are measured outside the arm.
- Some calls used estimated costs. Per-arm estimated call counts are in run.json.
- For zero-cost adapter responses with recorded token usage, the estimate applies the Fireworks list prices checked on 2026-11-12, with all input tokens priced at the uncached rate.
- Development produced zero actionable failures, so the prompt comparison has zero pairs.

| Arm | Passed / scored | Pass rate | Recovered / first failures | USD / verified task | Median seconds | p95 seconds | Calls | Incomplete |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| First attempt | 61/64 | 95.3% | — | 0.002632 | 12.62 | 16.46 | 128 | 0 |
| Generic retries | 64/64 | 100.0% | 3/3 | 0.002538 | 12.68 | 17.67 | 131 | 0 |
| Retries with diagnostics | 64/64 | 100.0% | 3/3 | 0.002568 | 12.68 | 23.37 | 133 | 0 |

## Paired comparisons

- Retries with diagnostics vs Generic retries — +0.0 pp, 95% interval [+0.0, +0.0] pp, 64 paired trials across 32 scenarios (flat).
- Development-guided prompt vs First attempt — — pp, 95% interval unavailable, 0 paired trials across 0 scenarios (inconclusive).
- Generic retries vs First attempt — +4.7 pp, 95% interval [+0.0, +10.9] pp, 64 paired trials across 32 scenarios (inconclusive).
- Retries with diagnostics vs First attempt — +4.7 pp, 95% interval [+0.0, +10.9] pp, 64 paired trials across 32 scenarios (inconclusive).

## Gains and regressions by family

- retry_feedback, aggregation — 0 gains and 0 regressions over 16 pairs.
- retry_feedback, duplicates — 0 gains and 0 regressions over 16 pairs.
- retry_feedback, links_and_currency — 0 gains and 0 regressions over 16 pairs.
- retry_feedback, mixed — 0 gains and 0 regressions over 16 pairs.

## Pricing sources

- `fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash` uses $0.30 per million input tokens and $1.20 per million output tokens. [Fireworks model pricing](https://fireworks.ai/models/deepseek-ai/deepseek-v4p1-flash)
- `fireworks_ai/accounts/fireworks/models/glm-5p3-flash` uses $0.15 per million input tokens and $0.50 per million output tokens. [Fireworks model pricing](https://fireworks.ai/models/fireworks/glm-5p3-flash)
