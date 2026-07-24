# Testing

## Repository commands

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

`pyproject.toml` configures pytest for `tests/` plus README doctests, Ruff for all rules with a small ignore set, and mypy strict mode for `src`.

## Verified snapshot — Gate 0 Baseline (2026-07-24)

| Check | Result |
| --- | --- |
| Full pytest on `tests` + `README.md` | **564 passed** |
| Ruff on `src` + `tests` | **Passed clean** |
| Strict mypy on `src` | **Failed: 358 errors in 24 files** (baseline technical debt) |

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
- technical retry reuses its existing Hypothesis and creates a distinct successor attempt;
- rejection of an outbox-only execution bundle without marking an operation committed;
- runnable GraphMiner/HypothesisAnalyst graphs;
- DVC execution or cleaning/version creation;
- natural-language end-to-end planning, retrieval or prompt construction;
- production CLI/API/worker bootstrap;
- process crash or multi-host worker behavior;
- external executor side-effect idempotency;
- cache validity/reuse;
- Ruff/mypy compliance.

## Test credibility boundary

Use a passing test count only to claim that covered local contracts pass. Do not use it to claim that CogniEDA is product-ready, that a live configured model service is reachable, or that static quality gates are green.

When adding behavior, protect invariants first: immutable knowledge, context-role exclusion, admission/cardinality, transition ownership/fencing, operation atomicity, and evidence-bound Discovery creation.
