# Persistence Notes

This file is retained as a legacy entry point. See [architecture/storage-layers.md](architecture/storage-layers.md) and [architecture/implementation-gap-analysis.md](architecture/implementation-gap-analysis.md) for the current status comparison.

## Current Implementation

CogniEDA currently uses a local SQLModel-backed store. By default it writes to `.local/cognieda_graph.sqlite3` unless `COGNIEDA_DB_URL` is set.

Implemented persistence surfaces:

- SQLModel tables in bounded modules under `src/db/models/`
- the explicit `db.models` facade in `src/db/models/__init__.py`, which registers and exports all
  persisted table classes without redefining them
- database setup in `src/db/session.py`
- table creation in `src/db/init_db.py`
- bounded repositories under `src/repositories/`
- SQLite foreign-key enforcement
- targeted execution/task-motivation migrations
- durable `PlannerOperation`, `AnalysisFrame`, `ExecutionRun`, execution approval/outbox/inbox, and `UserDecision` records

## Current Invariants

- Workspace/database isolation is handled by using a separate database URL per workspace.
- `DataProfileRepository`, `EvidenceRepository`, `DiscoveryRepository`, and `SessionFrameRepository` do not expose `update()`.
- `AnalysisFrameRepository` exposes only reads plus the transaction-private
  `_stage_create_from_evidence_admission()` hook; atomic Evidence admission is its sole production
  caller.
- Evidence references Hypothesis, DataProfile, AnalysisFrame, and ExecutionRun identifiers.
- Discovery requires Evidence and `validity_basis`.
- `SessionFrame` conclusion projection excludes assumptions and other planning-only context.

## Target Gaps

The target architecture calls for graph retrieval, a complete workflow/provenance store and evidence cache. The current implementation persists minimal `PlannerOperation`, `AnalysisFrame`, `ExecutionRun`, approval/outbox/inbox and user-decision records, but it does not provide full reproducibility detail, a general migration framework, cache records, or production retrieval.
