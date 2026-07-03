# Persistence Notes

This file is retained as a legacy entry point for current persistence behavior. See [architecture/storage-layers.md](architecture/storage-layers.md) for the current code/target comparison.

## Current Implementation

CogniEDA currently uses a local SQLModel-backed store. By default it writes to `.local/cognieda_graph.sqlite3` unless `COGNIEDA_DB_URL` is set.

Implemented persistence surfaces:

- SQLModel tables in `src/db/models.py`
- database setup in `src/db/session.py`
- table creation in `src/db/init_db.py`
- repositories in `src/repositories/`
- SQLite foreign-key enforcement

## Current Invariants

- Workspace/database isolation is handled by using a separate database URL per workspace.
- `DataProfileRepository`, `EvidenceRepository`, `DiscoveryRepository`, and `SessionFrameRepository` do not expose `update()`.
- Evidence references Hypothesis, DataProfile, AnalysisFrame, and ExecutionRun identifiers.
- Discovery requires Evidence and `validity_basis`.
- `SessionFrame` conclusion projection excludes assumptions and other planning-only context.

## Target Gaps

The target architecture calls for full graph retrieval policy, workflow store, provenance store, and evidence cache. The current implementation does not yet provide persisted `PlannerOperation`, full `AnalysisFrame`, full `ExecutionRun`, or cache records.
