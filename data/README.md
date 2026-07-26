# Data Layout

> **Role:** Filesystem technical reference. **Canonical concept owner:**
> [Research-state objects and roles](../docs/concepts/research-state/objects-and-roles.md).
> **Contributor entry:** [Contributor documentation](../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../docs/current-state.md).

CogniEDA keeps physical datasets under `data/`. Durable research state is stored
in the workspace-local SQLite persistence layer.

## Directory Conventions

- `data/raw/`: immutable source snapshots.
- `data/derived/`: reproducible outputs derived from source data.
- `data/samples/`: small Git-tracked fixtures intended for tests and smoke checks.

Each profiled dataset version should be represented semantically by a `DataProfile` record with `dataset_path` and, when available, DVC or equivalent version identity.

## Current Compatibility Note

The existing root-level sample data files remain in place because tests and smoke checks may reference them directly. New sample fixtures should prefer `data/samples/`.
