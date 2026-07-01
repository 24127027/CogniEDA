# Data Profiling And Cleaning

## Target Design

Data profiling and cleaning protect data-state validity.

Target rules:

- `DataProfile` is immutable.
- Raw data is never overwritten.
- Cleaning creates a new dataset version and a new `DataProfile`.
- Cleaning decisions are recorded in provenance.
- The accepted final `DataProfile` becomes analysis ground truth.
- Evidence and Discovery must remain scoped to the `DataProfile` they used.

## Current Implementation

Implemented:

- `DatasetProfiler` builds a typed `DataProfile` from a pandas dataframe or file path.
- Profiling validates that a dataframe has at least one column and unique column names.
- Profiling records row count, column count, column order, inferred logical dtypes, missingness, duplicate rows, categorical top values, numeric summaries, primary-key candidate, time-column candidates, and quality flags.
- `DataProfileRepository` supports create, get, list, list-for-dataset, and latest-for-dataset.
- Tests assert semantic dtype profiling and repository round trips.
- Repositories do not expose `DataProfileRepository.update()`.

Partially implemented:

- `DatasetAsset` records raw/derived dataset role, source, location, version, upstream datasets, and lineage steps.
- `docs/data_versioning.md` describes a Git/DVC metadata split, but DVC is not declared in `pyproject.toml` and no DVC integration code was found.

Not implemented:

- Cleaning execution service.
- User-reviewed cleaning decision loop.
- New dataset version creation automation.
- `DataProfile.accepted_as_ground_truth`.
- Target `dvc_hash`, `dvc_version_label`, `profile_artifacts`, and `preprocessing_history` fields on `DataProfile`.
- Propagation rules when a `DataProfile` is superseded.

## Implementation Status

Partially implemented.

## Known Deviation

The current code models dataset version identity through `DatasetAsset` plus `DataProfile.dataset_id`. The target design says `DataProfile` itself is the data-state FCO and stores dataset/version identity directly.

## Development Guidance

Future cleaning work should:

- create a new dataset version instead of mutating existing data
- create a new `DataProfile`
- preserve lineage from derived data to source data
- record row drops, column drops, filters, joins, imputations, and derived features
- avoid presenting a cleaned dataset as accepted ground truth until user approval is represented
