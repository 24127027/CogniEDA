# Data Versioning Workflow

## Current Implementation

The current repository uses a split responsibility model:

- Git stores code, schemas, docs, and reviewable metadata templates under `artifacts/`.
- The SQLModel store persists runtime scaffold artifacts.
- `data/raw/`, `data/derived/`, and `data/samples/` provide filesystem locations for dataset files.
- `DatasetAsset` currently stores dataset source, location, version, role, kind, and lineage.
- `DataProfile` currently stores a profile snapshot for a `DatasetAsset`.

## Target Architecture

The final FCO design says `DataProfile` is the data-state FCO. It should store dataset/version identity directly, including DVC hash or equivalent version identity. Raw dataset versions are not target FCOs.

## DVC Status

The workflow below mentions DVC because it is part of the target data-versioning intent. DVC is not declared in `pyproject.toml`, and no DVC integration code was found in the current repo.

## Recommended Manual Workflow

1. Copy immutable source data into `data/raw/`.
2. If DVC is installed in your environment, track large raw files with `dvc add`.
3. Create or persist a current `DatasetAsset` record for scaffold compatibility.
4. Profile the dataset with the profiling utilities.
5. Persist the resulting `DataProfile`.
6. For derived data, write outputs under `data/derived/`, preserve upstream lineage, and create a fresh `DataProfile`.

## Guardrails

- Never overwrite raw data in place.
- Do not treat a `DataProfile` as a mutable rolling status object.
- Cleaning or preprocessing should create a new dataset version and a new `DataProfile`.
- Keep Git-tracked metadata mirrors separate from runtime database state.
- Do not claim DVC is automated by the repo until code or tooling is added.
