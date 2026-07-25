# CogniEDA

CogniEDA is a governed research-state system for analytical investigation. Its goal is not to make an agent remember more chat history. Its goal is to keep analytical conclusions traceable to the data, method, parameters, evidence, and validity scope that support them.

## Current Implementation Status

Implemented or verified in the structural foundation (Gate 0 through Package S4):

- **First-Class Objects (FCOs)**: Pydantic schemas and SQLModel tables for `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.
- **Bounded Context Architecture**: Decomposed, single-owner bounded contexts across `application`, `schemas`, `repositories`, and `db.models`.
- **Specialist Scientific Boundaries**: Observation-only Data Explorer, PydanticAI protected-evaluation Hypothesis Analyst, and user-governed proposal authorization.
- **Atomic Admission Services**: `AtomicDiscoveryAdmissionService` (sole Discovery materialization transaction owner) and `AtomicValidityPropagationService` (sole validity propagation transaction owner).
- **SQLite Persistence & Triggers**: Fenced execution lease tracking, immutable governance authority tables, and DDL triggers enforcing exact claim consumption.
- **Canonical Documentation & Structural Exit**: Reconstructed canonical documentation (`docs/index.md`) and verified Package 7 readiness (`docs/architecture/structural-exit-status.md`).

Not implemented yet (Scheduled for Package 7+):

- Supported CLI binary, HTTP REST/gRPC service, or worker daemon process.
- Executable DVC integration.
- Production Data Explorer sandbox runner and production model adapters.
- Graph Miner semantic vector index persistence.

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

Other concepts are deliberately not FCOs:

- `Workspace` is a filesystem/runtime boundary.
- `Question` is UI input that decomposes into a `Task`.
- `AnalysisFrame` is provenance/data-view state.
- `GeneratedView` is runtime output, not `Discovery`.
- `PlannerOperation` is pending state mutation.
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
uv run python -m compileall -q src
uv run mypy src
```

## Repository Structure

```text
src/
  agents/        Planner graph and Data Explorer / Analyst specialist agents
  application/   Composition root, execution transition, and governed admissions
  data/          Dataset loaders and baseline profiling
  db/            SQLModel table models facade (`db.models`) and SQLite migrations
  memory/        SessionFrame and context builders
  repositories/  Persistence repositories across bounded contexts
  schemas/       Pydantic value-object schemas across bounded contexts
  tools/         Tool manager and configuration
tests/           Repository, profiling, DB, application, and architecture tests
docs/            Canonical architecture, workflow, decision, and exit status docs
```

## Documentation

Start here:

- [Canonical Documentation Index](docs/index.md)
- [Project Purpose](docs/project-purpose.md)
- [Master Development Roadmap](docs/roadmap.md)
- [Architecture Overview](docs/architecture/overview.md)
- [Research-State Model](docs/architecture/research-state-model.md)
- [Scientific Specialist Contracts](docs/architecture/scientific-specialist-contracts.md)
- [Context Type Safety](docs/architecture/context-type-safety.md)
- [Bounded Contexts](docs/architecture/bounded-contexts.md)
- [Persistence and Transactions](docs/architecture/persistence-and-transactions.md)
- [Structural Exit Status Report](docs/architecture/structural-exit-status.md)
