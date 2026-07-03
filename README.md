# CogniEDA

CogniEDA is a governed research-state system for analytical investigation. Its goal is not to make an agent remember more chat history. Its goal is to keep analytical conclusions traceable to the data, method, parameters, evidence, and validity scope that support them.

## Current Implementation Status

Implemented or partially implemented today:

- Pydantic schemas under `src/schemas/` for the target FCO set: `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.
- Typed provenance records for user decisions, plus explicit `AnalysisFrame` and `ExecutionRun` references on `Evidence`.
- SQLModel tables under `src/db/` and thin repositories under `src/repositories/`.
- Append-only repository surfaces for `DataProfile`, `Evidence`, `Discovery`, and `SessionFrame`.
- Baseline dataframe profiling under `src/data/`, producing immutable `DataProfile` records with dataset path and optional DVC identity.
- A DVC adapter interface that makes executable DVC integration explicit but not yet implemented.
- `SessionFrameBuilder` and `SessionContextBuilder` under `src/memory/session_frame.py`, including planning vs conclusion context projection.
- LangGraph planner node names and graph wiring under `src/agents/planner/`, with most planner node bodies still stubbed.

Not implemented yet:

- Executable DVC integration.
- Full `AnalysisFrame`, `ExecutionRun`, `PlannerOperation`, and evidence-cache persistence records.
- Operation-before-commit planner persistence.
- Graph-level retrieval policy; current context type safety is local to `SessionFrame` projection.
- A production CLI or service API. The `cognieda` entrypoint is currently a placeholder.

## Target Architecture Summary

The architecture defines exactly these first-class objects:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

Other important concepts are deliberately not FCOs:

- `Workspace` is a filesystem/runtime boundary.
- `Question` is UI input that becomes a `Task`.
- `AnalysisFrame` is provenance/data-view state.
- `GeneratedView` is runtime output, not `Discovery`.
- `PlannerOperation` is pending mutation.
- `ExecutionRun` is provenance.
- `EvidenceCacheEntry` is cache.

## Setup

Prerequisites:

- Python 3.12+
- `uv`

Local setup:

```powershell
uv sync
copy .env.example .env
```

The default database URL resolves to `.local/cognieda_graph.sqlite3` unless `COGNIEDA_DB_URL` is set. Each filesystem workspace should use its own graph database file.

## Verification

Commands declared by the repo:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

## Repository Structure

```text
src/
  agents/        LangGraph agent scaffolds and planner/executor contracts
  data/          Dataset loaders, DVC boundary, validation, and baseline profiling
  db/            SQLModel tables, engine setup, and init helper
  memory/        SessionFrame and context builders
  repositories/  Thin persistence repositories
  schemas/       Pydantic FCO and value-object schemas
  tools/         Tool manager and MCP/toolset scaffolding
tests/           Repository, profiling, DB, and session-frame tests
docs/            Architecture, workflow, concept, development, and reference docs
artifacts/       Git-tracked DataProfile mirror template surface
data/            Raw, derived, and sample data directories
config/          Agent and MCP config placeholders
```

## Documentation

Start here:

- [Documentation Index](docs/index.md)
- [Architecture Overview](docs/architecture/overview.md)
- [First-Class Objects](docs/architecture/first-class-objects.md)
- [Implementation Gap Analysis](docs/architecture/implementation-gap-analysis.md)
- [User Research Workflow](docs/workflows/user-research-workflow.md)
- [Development Setup](docs/development/setup.md)
- [Testing](docs/development/testing.md)
