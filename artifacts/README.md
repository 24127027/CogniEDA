# Artifact Metadata Layout

This directory stores Git-tracked analytical metadata files that describe dataset state independently of the physical files under `data/`.

## Subdirectories

- `artifacts/dataset_assets/`: `DatasetAsset` JSON mirrors for concrete dataset versions
- `artifacts/data_profiles/`: `DataProfile` JSON snapshots tied to one dataset version and one profiling method

## Current Scope Clarification

- These Git-tracked files are intentionally separate from DVC-managed data so that code review can inspect lineage, version labels, upstream dependencies, and profiling metadata without pulling large files.
- The current scaffold mirrors only `DatasetAsset` and `DataProfile` here by default.
- Current SQLModel persistence also includes scaffold artifacts such as `Project`, `Assumption`, `Hypothesis`, `Evidence`, `DecisionLog`, and `SessionFrame`.
- The target FCO set is narrower: `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`. Do not treat `Project`, `DatasetAsset`, or `DecisionLog` as target FCOs.
