# Data Profiling And Cleaning

## Target Design

Data profiling and cleaning protect data-state validity.

Target rules:

- `DataProfile` is immutable.
- Raw data is never overwritten.
- Cleaning creates a new dataset version and a new `DataProfile`.
- Cleaning decisions are recorded in provenance.
- The accepted final `DataProfile` becomes analysis ground truth.
- Evidence and Discovery remain scoped to the `DataProfile` they used.

## Current Implementation

Implemented:

- `DatasetProfiler` builds a typed immutable `DataProfile` from a pandas dataframe or file path.
- Profiling validates that a dataframe has at least one column and unique column names.
- Profiling records row count, column count, column order, inferred logical dtypes, missingness, duplicate rows, categorical top values, numeric summaries, primary-key candidate, time-column candidates, and quality flags.
- `DataProfile` stores `dataset_path`, optional `dvc_hash`, optional `dvc_version_label`, optional source metadata, preprocessing history, artifacts, lifecycle state, and `accepted_as_ground_truth`.
- `DataProfileRepository` supports create, get, list, list-for-dataset-path, and latest-for-dataset-path.
- Repositories do not expose `DataProfileRepository.update()`.
- `DvcAdapter` defines the integration boundary and raises explicit not-implemented behavior until executable DVC support is added.

Not implemented:

- Executable DVC identity resolution.
- Cleaning execution service.
- User-reviewed cleaning decision loop.
- Automated derived dataset creation.
- Propagation rules when a `DataProfile` is superseded.

## Implementation Status

Partially implemented.

## Known Deviation

DVC identity is currently supplied by callers or left empty. The code does not run `dvc` commands, and `pyproject.toml` does not declare DVC as a runtime dependency.

## Development Guidance

Future cleaning work should:

- create a new dataset version instead of mutating existing data
- create a new `DataProfile`
- record row drops, column drops, filters, joins, imputations, and derived features in preprocessing history and provenance
- avoid presenting a cleaned dataset as accepted ground truth until user approval is represented
