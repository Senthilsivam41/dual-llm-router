# Published Benchmark Results

Versioned, human-readable benchmark publications for dual-llm-router.

## Standard

| Artifact | Naming / path |
| --- | --- |
| Report | `benchmark_results_<YYYYMMDD_HHMMSSZ>.md` |
| Sidecar JSON | `benchmark_results_<YYYYMMDD_HHMMSSZ>.json` |
| Latest pointer | `LATEST.md` (copy of newest report) |
| Catalog | `INDEX.md` + `index.json` |

Timestamps are **UTC** (`Z` suffix).

## When results are published

Automated publishes run when a commit changes **major** paths:

- `src/`, `router/`, `evals/`, `prompts/`
- `benchmark/` (task suite)
- `config/evolution.yaml`, `config/ab_tests.yaml`
- benchmark/evolution scripts

Local / CI entrypoint:

```bash
# Skip if commit is docs-only / non-major
python scripts/publish_benchmark_results.py --if-major --suite easy --simulate --trigger local

# Always publish
python scripts/publish_benchmark_results.py --force --suite all --simulate --trigger manual
```

CI workflow: `.github/workflows/benchmark.yml` (path-filtered on push/PR).

## Reading results

1. Open [`LATEST.md`](LATEST.md) for the newest run
2. Browse history in [`INDEX.md`](INDEX.md)
