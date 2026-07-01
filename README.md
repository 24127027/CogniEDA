# CogniEDA

CogniEDA is a governed research-state system for analytical investigation. Its goal is not to make an agent remember more chat history. Its goal is to keep analytical conclusions traceable to the data, method, parameters, evidence, and validity scope that support them.

This repository is currently a scaffold. It contains typed artifact schemas, a SQLModel-backed local persistence layer, baseline profiling utilities, session-frame construction, and planner graph stubs. It does not yet implement the full final FCO architecture.

## Current Implementation Status

Implemented or partially implemented today:

- Pydantic schemas under `src/schemas/` for the current artifact set: `Project`, `DatasetAsset`, `DataProfile`, `Assumption`, `Hypothesis`, `Evidence`, `DecisionLog`, and `SessionFrame`.
- SQLModel tables under `src/db/` and thin repositories under `src/repositories/`.
- Append-only repository surfaces for `DataProfile`, `Evidence`, and `SessionFrame`.
- Baseline dataframe profiling under `src/data/`.
- `SessionFrameBuilder` under `src/memory/session_frame.py`.
- LangGraph planner node names and graph wiring under `src/agents/planner/`, with most planner node bodies still stubbed.
- Reviewable metadata mirror directories under `artifacts/dataset_assets/` and `artifacts/data_profiles/`.

Not implemented yet:

- Target `Objective`, `Task`, and `Discovery` FCO models.
- `ValidityEnvelope`, `AnalysisFrame`, `PlannerOperation`, `ExecutionRun`, and `EvidenceCacheEntry` records.
- Operation-before-commit planner persistence.
- Enforced context type safety between Planning Context and Conclusion Context.
- The target Task -> Hypothesis -> Evidence -> Discovery lifecycle.
- A production CLI or service API. The `cognieda` entrypoint is currently a placeholder.

## Target Architecture Summary

The target architecture defines exactly these first-class objects:

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

Some architecture docs describe design targets that are not yet fully implemented. Each major doc labels current implementation status, known deviations, and missing work.

## Setup

Prerequisites:

- Python 3.12+
- `uv`

Local setup:

```powershell
uv sync
copy .env.example .env
```

The default database URL resolves to `.local/cognieda_artifacts.sqlite3` unless `COGNIEDA_DB_URL` is set. The `.env.example` file currently declares:

```text
COGNIEDA_ENV=local
COGNIEDA_LOG_LEVEL=INFO
COGNIEDA_DB_URL=
COGNIEDA_DB_ECHO=false
```

Agent LLM creation in `src/agents/llm.py` also expects `COGNIEDA_MODEL_NAME` and `COGNIEDA_OPENAI_API_KEY`, but those variables are not yet listed in `.env.example`.

## Verification

Commands declared by the repo:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

The project has no separate documentation validation command in the current repo.

## Repository Structure

```text
src/
  agents/        LangGraph agent scaffolds and planner node stubs
  data/          Dataset loaders, validation, and baseline profiling
  db/            SQLModel tables, engine setup, and init helper
  memory/        SessionFrame builder
  repositories/  Thin persistence repositories
  schemas/       Pydantic artifact and value-object schemas
  tools/         Tool manager and MCP/toolset scaffolding
tests/           Repository, profiling, DB, and session-frame tests
docs/            Architecture, workflow, concept, development, and reference docs
artifacts/       Git-tracked metadata mirror templates for dataset assets and profiles
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
