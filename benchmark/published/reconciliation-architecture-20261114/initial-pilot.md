# Live invoice reconciliation architecture initial pilot

November 14, 2026 IST. 32 paired blocks across 16 held-out scenarios, with 2 repetitions per scenario and 4 concurrent blocks.

[Per-trial measurements](initial-pilot.json)

## Results

| Arm | Verified / scored | Unscored | Total model USD | USD per verified success | Median seconds | p95 seconds | Human interventions | Calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single executor | 16/32 | 0 | 0.016553 | 0.001035 | 5.42 | 9.72 | 0/32 | 32 |
| Dynamic router | 9/32 | 0 | 0.059874 | 0.006653 | 7.13 | 11.40 | 0/32 | 32 |
| Planner/executor | 10/32 | 0 | 0.075658 | 0.007566 | 13.30 | 20.37 | 0/32 | 64 |

## Paired success differences

The 95% bootstrap intervals resample scenarios as clusters. They are descriptive pilot estimates.

| Comparison | Complete pairs | Gains | Regressions | Difference | 95% interval |
| --- | ---: | ---: | ---: | ---: | --- |
| Dynamic router vs Single executor | 32 | 5 | 12 | -21.9 pp | [-46.9, +3.1] pp |
| Planner/executor vs Single executor | 32 | 6 | 12 | -18.8 pp | [-46.9, +9.4] pp |
| Planner/executor vs Dynamic router | 32 | 5 | 4 | +3.1 pp | [-12.5, +18.8] pp |

## Results by fixture family

| Fixture family | Blocks | Single executor | Dynamic router | Planner/executor | Planner gains vs single | Planner regressions vs single |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| aggregation | 8 | 5/8 | 3/8 | 2/8 | 1 | 4 |
| duplicates | 8 | 6/8 | 1/8 | 1/8 | 0 | 5 |
| links and currency | 8 | 1/8 | 4/8 | 4/8 | 3 | 0 |
| mixed | 8 | 4/8 | 1/8 | 3/8 | 2 | 3 |

## Promotion decision

Keep dual-model planning at pilot status. Every family contains four scenario clusters and shares the same task specification. A promotion decision needs replicated paired gains on distinct tasks within the target class, with the extra model cost and latency accounted for.

## Protocol and measurement

- Single executor used `fireworks_ai/accounts/fireworks/models/glm-5p3-flash` on every block.
- Dynamic routing used `fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash` as the sole executor when the visible payments contained a duplicate ID (16 blocks). The router chose the default executor on the remaining 16 blocks. The two models' relative capabilities were assumed by this policy and tested only through these observed outcomes.
- Planner/executor used `fireworks_ai/accounts/fireworks/models/deepseek-v4p1-flash` to create a TaskSpec and the default executor to implement it. Each arm received one executor attempt. The planner could retry TaskSpec generation once.
- All arms used the repository executor prompt and received the same invoice policy and visible fixture. This initial run paired the generic prompt with a single-patch validator. Each ran in a fresh workspace. The harness applied a validated patch for `reconcile.py` and graded it in the network-disabled Docker verifier against the visible scenario and two private probes.
- Wall time includes model inference, patching, and visible verification. Private grading and provider preflight are excluded. Latency percentiles use scored trials. Cost includes model calls across all attempted trials and uses provider cost where reported, or token usage with the repository's November 12 price snapshot for the Fireworks models.
- Runs were unattended and allowed no manual repair. The intervention count measures observed interventions in this harness. It leaves the need for human assistance under an escalation policy unmeasured.
- Scenario corpus SHA-256 `b84666c7fd6fe447fb72351744e00ce65ed2099e89e1ab16558db8a2c32f544b`.
- Invoice policy SHA-256 `a792947fee30c001f38854f83f21f33737f08eebc1808af98f4cc037c8fa9a81`.

The November 12 evolution dashboard's 100 runs and 0.9125 score measure internal fitness for the active prompt pair. The success rates above come from independent workspace verification.
