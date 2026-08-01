# Agent conventions — memory & Codegraph

Standing rules for any agent working in this repository.

## Memory folder

Path: [`memory/`](./README.md) (committed).

| When | Action |
| --- | --- |
| Start of substantial work | Read `memory/STATUS.md` + `memory/FUTURE.md` |
| After a milestone / PR-ready slice | Update STATUS (what shipped) and FUTURE (what remains) |
| New standing process | Document here or in STATUS |

Do **not** put secrets or `.autoclaw/` runtime dumps in `memory/`.

## Codegraph (required when available)

1. **Prefer Codegraph for discovery** — use `codegraph_explore` with `projectPath` = repo root to find files/symbols/call paths. Do **not** scan the full repo with Grep/Glob/find when `.codegraph/` exists.
2. **After major implementation** — re-index so the graph matches new code:
   ```bash
   codegraph init     # first time only, if no .codegraph/
   codegraph sync     # after edits
   # or: codegraph index   # full rebuild
   ```
3. **If no index** — MCP will refuse Codegraph for the session; fall back to targeted Read/Grep, and tell the user to run `codegraph init` (or run it when they have asked for indexing).
4. **Scope** — at minimum keep `evals/`, `router/`, `scripts/`, `benchmark/`, and `src/` accurately indexed after those change.

## Codebase-memory MCP (optional shareable graph)

- Local CLI Codegraph (`.codegraph/`) is the primary agent discovery index.
- Shareable MCP artifact lives in `.codebase-memory/graph.db.zst` (may be committed).
- Refresh with `index_repository(repo_path=…, mode="full", persistence=true)` after large structural changes.
- Use `search_graph` / `trace_path` / `get_architecture` against project name `dual-llm-router` when the MCP graph is current.

## Related paths

- Evolution docs: `docs/Evolution.md`
- Benchmark suite: `benchmark/README.md`
- CI/CD notes: `benchmark/benchmark-cicd.md`
- Runtime state (gitignored): `.autoclaw/`
- Local Codegraph DB (gitignored): `.codegraph/`
