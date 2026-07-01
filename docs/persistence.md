# Persistence Notes

This file is retained as a legacy entry point for current persistence behavior. See [architecture/storage-layers.md](architecture/storage-layers.md) for the current code/target comparison.

## Current Implementation

CogniEDA currently uses a local SQLModel-backed store. By default it writes to `.local/cognieda_artifacts.sqlite3` unless `COGNIEDA_DB_URL` is set.

Implemented persistence surfaces:

- SQLModel tables in `src/db/models.py`
- database setup in `src/db/session.py`
- table creation in `src/db/init_db.py`
- repositories in `src/repositories/`
- SQLite foreign-key enforcement
- normalized association tables for lineage and artifact links

## Current Invariants

- `DatasetAsset` is unique by `project_id + name + version`.
- `DataProfileRepository`, `EvidenceRepository`, and `SessionFrameRepository` do not expose `update()`.
- Evidence-to-hypothesis links store typed outcomes.
- Dataset lineage supports multiple upstream assets.
- `SessionFrame` can persist stale context, dead ends, cached tool-result summaries, and invalidation rules.

## Target Gaps

The target architecture calls for a research knowledge graph, workflow store, provenance store, and evidence cache. The current implementation does not yet provide a graph store, `Task`, `Discovery`, `AnalysisFrame`, `ExecutionRun`, `PlannerOperation`, or `EvidenceCacheEntry`.
