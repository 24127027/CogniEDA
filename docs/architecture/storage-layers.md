# Storage Layers

## Target Design

The target architecture defines five conceptual layers inside a workspace:

| Layer | Target role |
| --- | --- |
| Filesystem workspace | Physical files, datasets, scripts, notebooks, outputs, reports, graph DB, provenance logs, cache, and DVC metadata. Not an FCO. |
| Research Knowledge Graph | Target FCOs with durable scientific or workflow meaning. |
| Workflow Store | Task hierarchy, task state, pending approvals, active planning state, and `SessionFrame` state. |
| Provenance Store | `ObjectiveRevision`, `PlannerOperation`, `ExecutionRun`, `AnalysisFrame`, rejected paths, cleaning decisions, tool calls, code versions, user decisions, and raw interaction traces when needed for audit. |
| Evidence Cache | Reusable computation references keyed by `DataProfile`, `AnalysisFrame`, method, parameters, code version, environment, and seed. |

## Current Implementation

The current implementation uses:

- local filesystem directories for `data/`, `artifacts/`, `docs/`, `config/`, and source code
- a local SQLModel store, defaulting to `.local/cognieda_artifacts.sqlite3`
- Git-tracked metadata mirror templates under `artifacts/dataset_assets/` and `artifacts/data_profiles/`
- no graph database implementation
- no migration tooling
- no separate provenance store
- no target evidence cache

The SQLModel store currently persists tables for:

- `projects`
- `dataset_assets`
- `dataset_lineage_links`
- `data_profiles`
- `assumptions`
- `hypotheses`
- `hypothesis_assumption_links`
- `hypothesis_dataset_links`
- `evidence`
- `evidence_assumption_links`
- `evidence_hypothesis_links`
- `evidence_decision_links`
- `decision_logs`
- `decision_assumption_links`
- `decision_hypothesis_links`
- `session_frames`

## Implementation Status

| Storage concern | Status | Current implementation note |
| --- | --- | --- |
| Filesystem workspace | Partially implemented | Repo has data/artifact folders, but no workspace initializer or one-graph-per-workspace enforcement. |
| SQLModel runtime store | Implemented | `src/db/session.py` and `src/db/init_db.py` provide local DB setup. |
| Research Knowledge Graph | Not implemented | The current store is relational SQLModel, not a graph. |
| Workflow Store | Partially implemented | Session frames exist; `Task` and planner operation state do not. |
| Provenance Store | Partially implemented | Some provenance is embedded in current artifacts; no separate provenance records exist. |
| Evidence Cache | Not implemented | No `EvidenceCacheEntry` or cache lookup service exists. |
| DVC integration | Design target | Docs mention DVC, but DVC is not declared in `pyproject.toml` and no DVC commands are implemented. |

## Current Runtime Source Of Truth

The current operational source of truth is the SQLModel database. Git-tracked JSON under `artifacts/` is a reviewable mirror/template surface for dataset assets and data profiles, not a complete runtime state model.
