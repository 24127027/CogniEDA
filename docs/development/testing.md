# Testing strategy

Tests establish bounded claims about code. A passing focused test does not make
an absent product process, provider, worker, adapter, or backend supported.
Read the [contributor hub](index.md) and the source owner before selecting a
test family.

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
Strict mypy has known baseline debt and is not currently a clean gate.

## What each test family proves

| Test family | Primary locations | What it establishes | What it does not establish |
| --- | --- | --- | --- |
| Schema contracts | `tests/schemas/` | validation, closed contracts, enums, snapshots, and object shape | persistence, transaction, or user workflow behavior |
| Repository behavior | `tests/repositories/` | mapping, guards, active/historical reads, and persistence-local rules | application transaction ownership |
| Application transitions | `tests/application/` | owner-specific state transitions and service contracts | a hosted product loop |
| Race, replay, rollback | application, repository, and E2E tests around execution, evaluation, Discovery, and validity | SQLite fencing, claims, compare-and-set, deterministic replay, and rollback boundaries | another backend or multi-host coordination |
| Planner | `tests/agents/planner/`, `tests/application/orchestrator/`, and operation tests | operation proposal/approval, graph shape, ordinary commit, and fail-closed guards | Planner scientific authorship or a complete product interaction |
| Memory and retrieval | `tests/memory/` | frame projection, lifecycle exclusion, bounded candidate/ranking behavior | semantic index, Graph Miner, or complete resume |
| Database and migration | `tests/db/` | initialization, targeted upgrade, legacy quarantine, model facade, and SQLite equivalence | immutable revision identities, general downgrade, or backend portability |
| Architecture enforcement | `tests/architecture/test_architecture_enforcement.py` | FCO ontology, import restrictions, writer confinement, transaction boundaries, facade constraints, enum/timestamp ownership, and initialization ordering | full product capability |
| Documentation integrity | `tests/architecture/test_documentation_integrity.py` | canonical journey, contributor classification, local links/anchors, source references, and overclaim guards | live behavior beyond the documented source/tests |
| End-to-end scientific lifecycle | `tests/e2e/test_research_lineage.py` | a direct/injected scientific lineage across guarded infrastructure | a supported UI, API, worker, or restart-safe product journey |

Architecture tests protect boundaries. They do not prove complete product
behavior. Do not weaken them merely to make a new dependency convenient. If a
boundary legitimately changes: review the decision, change source, run focused
tests, update the architecture test, update documentation, and add/update an
decision record when the change is durable.

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
[Persistence and transactions](../operations/persistence-and-transactions.md)
and [SQLite and portability](../operations/sqlite-and-portability.md).

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

## Selecting commands

Run the closest test directory plus the tests named by the changed owner. These
stable starting points intentionally omit fixed result totals:

```powershell
uv run pytest -q tests/architecture/test_documentation_integrity.py
uv run pytest -q tests/architecture
uv run pytest -q tests/application/<area>
uv run pytest -q tests/agents/planner
uv run pytest -q tests/memory
uv run pytest -q tests/repositories
uv run pytest -q tests/db
uv run pytest -q tests/e2e
uv run ruff check .
```

Run the full suite when changing a shared enum or schema, persistence model or
migration, transaction owner, architecture boundary, runtime composition, or
cross-cutting documentation classification. A scientific lifecycle change needs
transition and race/replay/rollback coverage, not only schema coverage. A
retrieval change needs lifecycle/validity checks before ranking assertions. A
migration needs fresh/existing-database and SQLite-equivalence coverage.

External analytical/model work is normally tested with injected fakes. Passing
those tests does not demonstrate a live provider, product authentication,
concrete Data Explorer, CLI/API/worker/daemon, DVC workflow, semantic index, or
portable database behavior.
