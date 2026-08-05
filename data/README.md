# Data Layout

CogniEDA keeps repository-local physical datasets under `data/`. Current
durable repository records use the configured SQLModel store, verified on
SQLite. Directory presence does not establish governed ingestion, and no
graph-database integration or composed runtime is currently supported.

## Directory Conventions

- `data/raw/`: immutable source snapshots.
- `data/derived/`: reproducible outputs derived from source data.
- `data/samples/`: small Git-tracked fixtures intended for tests and smoke checks.

Each profiled dataset version should be represented semantically by a `DataProfile` record with `dataset_path` and, when available, DVC or equivalent version identity.

## Current Compatibility Note

The existing root-level sample data files remain in place because tests and smoke checks may reference them directly. New sample fixtures should prefer `data/samples/`.
