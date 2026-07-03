# Data Versioning Workflow

## Current Implementation

The repository uses a split responsibility model:

- Git stores code, schemas, docs, and reviewable DataProfile mirror templates under `artifacts/`.
- The workspace-local SQLModel store persists runtime research state.
- `data/raw/`, `data/derived/`, and `data/samples/` provide filesystem locations for dataset files.
- `DataProfile` stores dataset path, optional DVC identity, source metadata, profile summaries, preprocessing history, lifecycle state, and ground-truth acceptance.
- `DvcAdapter` defines the integration boundary and raises explicit not-implemented behavior.

## Workflow

1. Copy immutable source data into `data/raw/`.
2. Resolve dataset-version identity outside the current code path, or leave DVC fields empty until executable integration is implemented.
3. Profile the dataset with the profiling utilities.
4. Persist the resulting immutable `DataProfile`.
5. For derived data, write outputs under `data/derived/`, preserve preprocessing history, and create a fresh `DataProfile`.

## Guardrails

- Never overwrite raw data in place.
- Do not treat a `DataProfile` as a mutable rolling status object.
- Cleaning or preprocessing should create a new dataset version and a new `DataProfile`.
- Keep Git-tracked metadata mirrors separate from runtime database state.
- Do not claim executable DVC support until the adapter is implemented and dependencies are declared.
