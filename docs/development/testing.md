# Testing

## Available Commands

The repo declares these verification commands:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

`pyproject.toml` configures pytest to run tests under `tests` and doctests over `README.md`.

## Current Test Coverage

Current tests cover:

- target FCO admission exclusions for non-FCO names
- repository CRUD and query behavior for current FCOs and user-decision provenance
- workspace/database isolation by separate SQLite URLs
- SQL foreign-key enforcement in SQLite
- append-only repository surfaces for `DataProfile`, `Evidence`, `Discovery`, and `SessionFrame`
- DataProfile and Evidence immutability
- Discovery requires Evidence and validity basis
- Task admission guards before Hypothesis creation
- database uniqueness/repository guards for one terminal Task to one Hypothesis
- database uniqueness/repository guards for one Hypothesis to one Discovery
- repository-level Evidence supersession/invalidation flagging for dependent Discoveries
- repository-level DataProfile supersession and historical scoping for dependent Evidence/Discovery
- Assumption testability admission and contradiction flagging without statement rewrite
- protected Discovery Synthesis Context excludes Assumptions, Tasks, existing Discoveries, stale context, and caches
- baseline profiling semantic dtype behavior
- `SessionFrameBuilder` profile/evidence/discovery selection behavior
- `SessionContextBuilder` planning/answer/discovery-synthesis projection and assumption exclusion
- planner/executor authoring contract separation

## Important Gaps

No tests were found for these runtime or graph-level invariants:

- planner operation approval before durable Task creation
- migration coverage for applying uniqueness constraints to older local SQLite files
- full `AnalysisFrame` provenance records
- full `ExecutionRun` provenance records
- operation-before-commit planner mutation
- graph-retrieved Planning Context vs Discovery Synthesis Context exclusion rules
- runtime propagation and user-review workflow after Evidence supersession/invalidation
- runtime propagation and retrieval policy after DataProfile supersession
- evidence cache validity keys

## Testing Guidance

When implementing target architecture, tests should protect invariants before broad behavior:

- immutability and allowed lifecycle transitions
- FCO admission rules
- context exclusion by epistemic role
- hypothesis/discovery cardinality
- Evidence/Discovery provenance completeness
- planner operation generation before commit
- user-review behavior for conflicts
