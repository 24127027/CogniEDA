# Testing

## Repository commands

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

`pyproject.toml` configures pytest for `tests/` plus README doctests, Ruff for all rules with a small ignore set, and mypy strict mode for `src`.

## Verified snapshot — 2026-07-16

| Check | Result |
| --- | --- |
| Full pytest on `tests` + `README.md` | **210 passed** in 12.94 seconds on the final post-doc rerun |
| Ruff on `src` + `tests` | **Failed: 12 findings**, 8 auto-fixable |
| Strict mypy on `src` | **Failed: 132 errors in 14 files** |

The authoritative invocation used absolute `--project` and `--rootdir` paths because the audit sandbox denied `Set-Location`. A first run accidentally collected from `C:\` and produced 234 system-permission collection errors; that run is an environment artifact, not a repository test result.

## Covered behavior

The 20 test files cover:

- canonical FCO admission and architecture ownership boundaries;
- repository CRUD/query, append-only surfaces, immutability and lifecycle guards;
- one Task–one Hypothesis and one Hypothesis–one Discovery constraints;
- Evidence/Discovery/DataProfile supersession/historical review semantics;
- Task motivation provenance;
- SQLite foreign keys, URL isolation and targeted migration boundaries;
- deterministic DataProfile semantics;
- RetrievalPolicy and SessionFrame planning/answer/synthesis projections;
- planner request parsing with injected fake classification models;
- planner graph topology and approval-gated execution admission;
- PlannerOperation persistence/commit behavior for covered cases;
- executor capability registry/dispatcher plumbing;
- attempt transition, lease, fencing, race and recovery cases;
- scientific processing and overlapping scientific-finalization races;
- tool-manager configuration loading.

No test is marked skipped or xfailed in the audited snapshot. Concurrency tests use file-backed SQLite where independent connections matter; external analytical work is represented by fake executors.

## Important gaps

Passing tests do not cover:

- default `_ConfiguredRequestUnderstandingModel` construction (it currently raises `TypeError`);
- successful public `authorize_retry()` (current code fails and conflicts with Hypothesis cardinality);
- rejection of an outbox-only execution bundle (current code reports false success);
- runnable GraphMiner/HypothesisAnalyst graphs;
- DVC execution or cleaning/version creation;
- natural-language end-to-end planning, retrieval or prompt construction;
- production CLI/API/worker bootstrap;
- process crash or multi-host worker behavior;
- external executor side-effect idempotency;
- cache validity/reuse;
- Ruff/mypy compliance.

## Test credibility boundary

Use “210 tests pass” to claim that covered local contracts pass. Do not use it to claim that CogniEDA is product-ready, that the default natural-language path works, or that static quality gates are green.

When adding behavior, protect invariants first: immutable knowledge, context-role exclusion, admission/cardinality, transition ownership/fencing, operation atomicity, and evidence-bound Discovery creation.
