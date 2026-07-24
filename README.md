# CogniEDA

CogniEDA is a governed research-state system for analytical investigation. Its goal is not to make an agent remember more chat history. Its goal is to keep analytical conclusions traceable to the data, method, parameters, evidence, and validity scope that support them.

## Current Implementation Status

Implemented or partially implemented today:

- Pydantic schemas under `src/schemas/` for the target FCO set: `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.
- Typed provenance/workflow records for user decisions, `AnalysisFrame`, `ExecutionRun`, execution approval/outbox/inbox, and `PlannerOperation`.
- SQLModel tables under `src/db/`, targeted SQLite migrations, and repositories under `src/repositories/`.
- Append-only repository surfaces for `DataProfile`, `Evidence`, `Discovery`, and `SessionFrame`.
- Baseline dataframe profiling under `src/data/`, producing immutable `DataProfile` records with dataset path and optional DVC identity.
- A DVC adapter interface that makes executable DVC integration explicit but not yet implemented.
- `SessionFrameBuilder` and `SessionContextBuilder` under `src/memory/session_frame.py`, including planning vs conclusion context projection.
- Bounded SQL-backed Discovery retrieval with lifecycle/profile filtering, structural and lexical
  relevance, deterministic ranking, and inclusion/exclusion reasons.
- A configured natural-language request-understanding adapter plus public `/manage_task`, `/decompose`, and `/objective` typed proposal paths. Proposed operations remain uncommitted until the caller approves the exact persisted ordered batch.
- A user-governed one-active-Objective lifecycle with explicit transitions, optimistic locking, immutable non-FCO revision provenance, and atomic successor SessionFrame updates.
- A narrow approval-gated planner execution admission path that atomically persists `Hypothesis`, `ExecutionRun`, and execution outbox state.
- A durable local worker protocol with lease/fencing transitions, an observation-only result inbox,
  reconciliation helpers, and atomic AnalysisFrame/Evidence admission.
- A durable-worker-to-domain adapter and per-runtime Data Explorer registry/dispatcher under
  `src/agents/executor/`. Its only durable output is the canonical observation-only
  `DataExplorerResult`. The Hypothesis Analyst has an isolated PydanticAI protected-evaluation
  boundary and durable fenced proposal/failure control. Exact proposal governance, atomic
  Discovery admission, active retrieval exclusion, and atomic validity propagation are
  implemented for the local SQLite boundary.
- A fail-closed composition root under `src/application/runtime.py` that loads
  an explicit `COGNIEDA_RUNTIME_FACTORY=module:factory` deployment hook.

Not implemented yet:

- Executable DVC integration.
- A concrete Data Explorer adapter, production worker process, and general end-to-end product loop.
- Graph/vector retrieval and general production context assembly; protected Hypothesis evaluation
  now uses a canonical repository-built bundle, while broader context support remains a pure
  policy, local `SessionFrame` projection, and bounded SQL-backed Discovery retrieval.
- Evidence-cache persistence and reuse.
- A deployment-supplied authentication resolver, Analyst model provider, Data Explorer factory,
  service API, worker process, or product CLI. CogniEDA exposes no supported CLI product surface at Gate 0.
- A working checked-in MCP/tool configuration for model-backed agents; the current agent config
  names MCP servers that are not defined in `config/mcp.toml`.


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
  application/   composition root, execution orchestration, and governed admissions
  data/          Dataset loaders, DVC boundary, validation, and baseline profiling
  db/            SQLModel tables, engine setup, and init helper
  memory/        SessionFrame and context builders
  repositories/  Thin persistence repositories
  schemas/       Pydantic FCO and value-object schemas
  tools/         Tool manager and MCP/toolset/skill loading
tests/           Repository, profiling, DB, and session-frame tests
docs/            Architecture, workflow, concept, development, and reference docs
artifacts/       Git-tracked DataProfile mirror template surface
data/            Raw, derived, and sample data directories
config/          Agent, skill, and MCP configuration
```

## Documentation

Start here:

- [Documentation Index](docs/index.md)
- [Architecture Overview](docs/architecture/overview.md)
- [First-Class Objects](docs/architecture/first-class-objects.md)
- [Implementation Gap Analysis](docs/architecture/implementation-gap-analysis.md)
- [Agent Responsibility Boundaries](docs/architecture/agent-responsibility-boundaries.md)
- [Canonical Investigation Workflow](docs/architecture/canonical-investigation-workflow.md)
- [Scientific Specialist Contracts](docs/architecture/scientific-specialist-contracts.md)
- [User Research Workflow](docs/workflows/user-research-workflow.md)
- [Development Setup](docs/development/setup.md)
- [Testing](docs/development/testing.md)
