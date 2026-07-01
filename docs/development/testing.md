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

- repository CRUD and query behavior for current artifacts
- SQL foreign-key enforcement in SQLite
- dataset asset uniqueness by `project_id + name + version`
- normalized relationship round trips for dataset lineage, hypotheses, evidence, and decisions
- append-only repository surfaces for `DataProfile`, `Evidence`, and `SessionFrame`
- baseline profiling semantic dtype behavior
- `SessionFrameBuilder` evidence and dataset selection behavior

## Important Gaps

No tests were found for target-only invariants:

- target FCO admission rules
- `Objective` lifecycle
- `Task` lifecycle and terminal analytical readiness
- proposed Task cannot execute
- one terminal Task generates exactly one Hypothesis
- one Hypothesis produces exactly one Discovery
- parent Tasks do not produce Discoveries
- `Discovery` validity envelope
- `AnalysisFrame` provenance requirements
- operation-before-commit planner mutation
- Planning Context vs Conclusion Context exclusion rules
- Assumption quarantine
- Evidence supersession/invalidation propagation
- DataProfile supersession propagation
- Evidence cache validity keys

## Testing Guidance

When implementing target architecture, tests should protect invariants before broad behavior:

- immutability and allowed lifecycle transitions
- FCO admission rules
- context exclusion by epistemic role
- hypothesis/discovery cardinality
- Evidence/Discovery provenance completeness
- planner operation generation before commit
- user-review behavior for conflicts
