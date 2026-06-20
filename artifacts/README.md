# Artifact Metadata Layout

This directory stores Git-tracked analytical metadata files that describe dataset state independently of the physical files under `data/`.

## Subdirectories

- `artifacts/dataset_assets/`: `DatasetAsset` JSON mirrors for concrete dataset versions
- `artifacts/data_profiles/`: `DataProfile` JSON snapshots tied to one dataset version and one profiling method

## Current Scope Clarification

- These Git-tracked files are intentionally separate from DVC-managed data so that code review can inspect lineage, version labels, upstream dependencies, and profiling metadata without pulling large files.
- The current scaffold mirrors only `DatasetAsset` and `DataProfile` here by default.
- The full first-class artifact set still includes `Project`, `Assumption`, `Hypothesis`, `Evidence`, `DecisionLog`, and `SessionFrame`, but those are currently persisted operationally through the local SQLModel store rather than as Git-tracked JSON files.
