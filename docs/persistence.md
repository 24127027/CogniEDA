# Persistence Notes

This file is retained as a legacy entry point. See [architecture/storage-layers.md](architecture/storage-layers.md) and [implementation/SRC_IMPLEMENTATION_STATUS.md](implementation/SRC_IMPLEMENTATION_STATUS.md) for the audited current comparison.

## Current Implementation

CogniEDA currently uses a local SQLModel-backed store. By default it writes to `.local/cognieda_graph.sqlite3` unless `COGNIEDA_DB_URL` is set.

Implemented persistence surfaces:

- SQLModel tables in `src/db/models.py`
- database setup in `src/db/session.py`
- table creation in `src/db/init_db.py`
- repositories in `src/repositories/`
- SQLite foreign-key enforcement
- targeted execution/task-motivation migrations
- durable `PlannerOperation`, `AnalysisFrame`, `ExecutionRun`, execution approval/outbox/inbox, and `UserDecision` records

## Current Invariants

- Workspace/database isolation is handled by using a separate database URL per workspace.
- `DataProfileRepository`, `EvidenceRepository`, `DiscoveryRepository`, and `SessionFrameRepository` do not expose `update()`.
- Evidence references Hypothesis, DataProfile, AnalysisFrame, and ExecutionRun identifiers.
- Discovery requires Evidence and `validity_basis`.
- `SessionFrame` conclusion projection excludes assumptions and other planning-only context.

## Target Gaps

The target architecture calls for graph retrieval, a complete workflow/provenance store and evidence cache. The current implementation persists minimal `PlannerOperation`, `AnalysisFrame`, `ExecutionRun`, approval/outbox/inbox and user-decision records, but it does not provide full reproducibility detail, a general migration framework, cache records, or production retrieval.
