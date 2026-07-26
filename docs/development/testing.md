# Testing

## Repository commands

```powershell
uv run pytest
uv run ruff check .
uv run python -m compileall -q src
uv run mypy src
```

`pyproject.toml` configures pytest for `tests/` plus README doctests, Ruff for all
rules with a small ignore set, and strict mypy for `src`.

Counts are checkout-specific and must not be copied forward as current facts.
The S4 audit records the exact reviewed commands and results. Strict mypy has
known baseline debt and is not currently a clean gate.

## Covered boundaries

The suite includes:

- FCO classification, schema/model ownership, and import safety;
- Task-Hypothesis-Discovery cardinality and terminal-writer guards;
- Planner proposal/approval and fail-closed scientific operation handling;
- execution outbox/inbox, lease, fencing, retry, race, and recovery behavior;
- atomic Evidence and Discovery admission with rollback/replay/concurrency;
- protected synthesis-bundle exclusion and Analyst typed outputs;
- governance authority, exact proposal decision, and consumption fencing;
- validity authority, full dependent effects, replay, races, and retrieval
  exclusion;
- SessionFrame projection and bounded Discovery retrieval;
- SQLite migrations, legacy quarantine, deterministic model-facade
  registration, and trigger equivalence;
- canonical documentation inventory, links, anchors, and forbidden phantom
  source claims.

Concurrency tests use file-backed SQLite where independent connections matter.
External analytical/model work uses injected fakes; passing tests do not prove a
live provider, worker, or production adapter.

The claims supported by these suites are summarized in
[Persistence and transaction ownership](../persistence-and-transaction-ownership.md)
and [SQLite boundary and portability](../sqlite-boundary-and-portability.md).

## Important limitations

Tests do not make the absent product surfaces real. Notably absent or partial:

- a supported CLI/API/worker bootstrap and deployment authentication adapter;
- a concrete production Data Explorer adapter and live Analyst model;
- executable DVC/cleaning/version workflows;
- complete answer/suggest/plan Planner branches and a Planner application
  facade;
- Graph Miner traversal, persistent semantic index, and Evidence cache;
- multi-host crash semantics and external side-effect idempotency;
- a clean strict-mypy baseline.

When adding behavior, protect immutable knowledge, context-role exclusion,
admission/cardinality, transaction ownership, fencing/idempotency, and
evidence-bound Discovery creation first.
