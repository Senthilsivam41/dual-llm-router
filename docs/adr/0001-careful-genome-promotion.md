# ADR 0001: Careful genome promotion

- Status: Accepted
- Date: 2026-11-11

## Context

Prompt co-evolution writes Hermes and Laguna genomes under `.autoclaw/`, which is gitignored. The nightly workflow uploads that tree as a 30-day artifact and does not commit it. Winners therefore disappear with the artifact, while committing every mutant would mix runtime state into git and could publish prompt text that contains a secret.

The architecture is stable enough to record: planners and executors stay separate, fitness comes from `calculate_fitness`, and A/B tests promote a winner only after significance. What was missing is a durable, reviewed copy of the active pair and a fitness history that is not only a console print.

## Decision

1. Keep every mutant and run log in `.autoclaw/`. Do not auto-commit that tree.
2. Copy the active pair into `evolution/promoted/snapshots/<id>/` only when `evaluate_promotion` returns `baseline` or `promote`.
3. Require at least five scored runs, a composite gain of `promotion.min_delta` after the first snapshot, no success-rate drop, no secret-like genome fields, and no active variant that is still an A/B challenger.
4. Identical genomes produce `unchanged` and do not create another snapshot. A secret field added later is still rejected.
5. `--apply` is explicit. The nightly schedule uploads `promotion_decision.json` and does not commit `evolution/promoted/`. A manual dispatch with `promote=true` may commit that directory after `--apply --strict`.
6. Write fitness history to `evolution/dashboard/` (`fitness.html`, `fitness.json`, `LATEST.md`). Nightly CI may commit that dashboard. It is metrics, not genomes. Skip a new archive file when the fingerprint is unchanged.

## Consequences

- A winning prompt is recoverable after the Actions artifact expires, and only after the gates pass.
- Simulated nightly runs can still baseline or promote locally if someone passes `--apply`. The scheduled workflow does not.
- Dashboard commits on `main` can be noisy when each evolution step changes the history. The fingerprint suppresses commits when the scores did not change.
- Secret scanning covers secret-like field names, `sk-` tokens that include hyphens, and `api_key` / `secret` / `password` assignments. It is not a full secret detector.

## Alternatives considered

- Commit `.autoclaw/` from the nightly job. Rejected: that tree is runtime state and includes every mutant.
- Leave winners only in the 30-day artifact. Rejected: promotion then depends on artifact retention.
- Promote on composite gain alone. Rejected: a cheaper pair can raise composite while success rate falls.
