# Live invoice reconciliation architecture rerun

November 14, 2026 IST. 32 paired blocks across 16 held-out scenarios, with 2 repetitions per scenario and 4 concurrent blocks.

[Per-trial measurements](rerun.json) · [Initial pilot](initial-pilot.md) · [Earlier retry-feedback study](../reconciliation-feedback-20261112.md)

## Results

| Arm | Verified / scored | Unscored | Total model USD | USD per verified success | Median seconds | p95 seconds | Human interventions | Calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single executor | 30/32 | 0 | 0.014216 | 0.000474 | 5.04 | 10.93 | 0/32 | 32 |
| Dynamic router | 28/32 | 0 | 0.095428 | 0.003408 | 5.96 | 31.64 | 0/32 | 32 |
| Planner/executor | 32/32 | 0 | 0.070271 | 0.002196 | 11.93 | 16.59 | 0/32 | 64 |

## Paired success differences

The 95% bootstrap intervals resample scenarios as clusters. They are descriptive pilot estimates.

| Comparison | Complete pairs | Gains | Regressions | Difference | 95% interval |
| --- | ---: | ---: | ---: | ---: | --- |
| Dynamic router vs Single executor | 32 | 1 | 3 | -6.2 pp | [-18.8, +6.2] pp |
| Planner/executor vs Single executor | 32 | 2 | 0 | +6.2 pp | [+0.0, +15.6] pp |
| Planner/executor vs Dynamic router | 32 | 4 | 0 | +12.5 pp | [+0.0, +28.1] pp |

## Results by fixture family

| Fixture family | Blocks | Single executor | Dynamic router | Planner/executor | Planner gains vs single | Planner regressions vs single |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aggregation | 8 | 7/8 | 8/8 | 8/8 | 1 | 0 |
| duplicates | 8 | 7/8 | 4/8 | 8/8 | 1 | 0 |
| links and currency | 8 | 8/8 | 8/8 | 8/8 | 0 | 0 |
| mixed | 8 | 8/8 | 8/8 | 8/8 | 0 | 0 |

## Failure counts

- Dynamic router · invalid response · 4
- Single executor · private fixture failed · 1
- Single executor · public fixture failed · 1

## Promotion decision

Keep dual-model planning at pilot status. Every family contains four scenario clusters and shares the same task specification. A promotion decision needs replicated paired gains on distinct tasks within the target class, with the extra model cost and latency accounted for.

## Protocol and measurement

- Single executor used `fireworks_ai/accounts/fireworks/models/glm-5p3-flash` on every block.
- Dynamic routing used `fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash` as the sole executor when the visible payments contained a duplicate ID (16 blocks). The router chose the default executor on the remaining 16 blocks. The two models' relative capabilities were assumed by this policy and tested only through these observed outcomes.
- Planner/executor used `fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash` to create a TaskSpec and the default executor to implement it. Each arm received one executor attempt. The planner could retry TaskSpec generation once.
- All arms used the repository executor prompt and received the same invoice policy and visible fixture. The rerun appended an explicit single-patch instruction to that prompt for every arm. Each ran in a fresh workspace. The harness applied a validated patch for `reconcile.py` and graded it in the network-disabled Docker verifier against the visible scenario and two private probes.
- Wall time includes model inference, patching, and visible verification. Private grading and provider preflight are excluded. Latency percentiles use scored trials. Cost includes model calls across all attempted trials and uses provider cost where reported, or token usage with the repository's November 12 price snapshot for the Fireworks models.
- Runs were unattended and allowed no manual repair. The intervention count measures observed interventions in this harness. It leaves the need for human assistance under an escalation policy unmeasured.
- Scenario corpus SHA-256 `b84666c7fd6fe447fb72351744e00ce65ed2099e89e1ab16558db8a2c32f544b`.
- Invoice policy SHA-256 `a792947fee30c001f38854f83f21f33737f08eebc1808af98f4cc037c8fa9a81`.

The November 12 evolution dashboard's 100 runs and 0.9125 score measure internal fitness for the active prompt pair. The success rates above come from independent workspace verification.
