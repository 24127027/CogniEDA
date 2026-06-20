# Data Layout

CogniEDA keeps physical datasets under `data/` and tracks durable analytical metadata separately under `artifacts/`.

## Directory conventions

- `data/raw/`: immutable source snapshots. Add real datasets here and track them with DVC.
- `data/derived/`: reversible or reproducible outputs derived from raw datasets.
- `data/samples/`: small Git-tracked fixtures intended for tests and smoke checks.

## Current compatibility note

The existing `data/sample_customers.csv` and `data/sample_customers.parquet` files remain in place because current tests and smoke checks already reference them directly. New sample fixtures should prefer `data/samples/`.
