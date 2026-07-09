# Storage Layers

## Target Design

The target architecture defines five conceptual layers inside a workspace:

| Layer | Target role |
| --- | --- |
| Filesystem workspace | Physical files, datasets, scripts, notebooks, outputs, reports, graph DB, provenance logs, cache, and DVC metadata. Not an FCO. |
| Research graph/database | Target FCOs with durable scientific or workflow meaning. |
| Workflow store | Task hierarchy, task state, pending approvals, active planning state, and `SessionFrame` state. |
| Provenance store | `ObjectiveRevision`, `PlannerOperation`, `ExecutionRun`, `AnalysisFrame`, rejected paths, cleaning decisions, tool calls, code versions, user decisions, and raw interaction traces when needed for audit. |
| Evidence cache | Reusable computation references keyed by `DataProfile`, `AnalysisFrame`, method, parameters, code version, environment, and seed. |

## Current Implementation

The current implementation uses:

- local filesystem directories for `data/`, `artifacts/`, `docs/`, `config/`, and source code
- a local SQLModel store, defaulting to `.local/cognieda_graph.sqlite3`
- Git-tracked DataProfile mirror templates under `artifacts/data_profiles/`
- no graph database implementation
- no migration tooling
- partial typed provenance via `UserDecision` and Evidence references
- no target evidence cache

The SQLModel store currently persists tables for:

- `objectives`
- `data_profiles`
- `assumptions`
- `tasks`
- `hypotheses`
- `evidence`
- `discoveries`
- `user_decisions`
- `session_frames`

## Implementation Status

| Storage concern | Status | Current implementation note |
| --- | --- | --- |
| Filesystem workspace | Partially implemented | Repo has data/artifact folders and workspace-local DB default, but no workspace initializer or registry. |
| SQLModel runtime store | Implemented | `src/db/session.py` and `src/db/init_db.py` provide local DB setup. |
| Research graph/database | Partially implemented | The current store is relational SQLModel rather than a graph database, but it stores the target FCO set. |
| Workflow store | Partially implemented | Tasks, SessionFrames, minimal PlannerOperations, and a skeleton commit boundary exist; full planner runtime and approval UX are missing. |
| Provenance store | Partially implemented | `UserDecision`, minimal `AnalysisFrame`, minimal `ExecutionRun`, and Evidence provenance refs exist; full reproducibility records are missing. |
| Evidence cache | Not implemented | No cache lookup service exists. |
| DVC integration | Partially implemented | `DvcAdapter` defines the boundary and raises explicit not-implemented behavior. Executable DVC support is not declared as a runtime dependency. |

## Current Runtime Source Of Truth

The current operational source of truth is the workspace-local SQLModel database. Git-tracked JSON under `artifacts/` is a reviewable mirror/template surface, not a complete runtime state model.
