# DataProfile Mirrors

> **Role:** Filesystem technical reference. **Canonical concept owner:**
> [Research-state objects and roles](../../docs/concepts/research-state/objects-and-roles.md).
> **Contributor entry:** [Contributor documentation](../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../docs/current-state.md).

This directory is a reviewable mirror/template surface for `DataProfile` records.

Runtime truth is the workspace-local SQLite persistence layer. Files here should
not be treated as a second source of truth unless an explicit import/export
workflow is added.

Each mirror should align with
`src/schemas/research/data_profile.py::DataProfile` and store dataset-version
identity directly:

- `dataset_path`
- optional `dvc_hash`
- optional `dvc_version_label`
- optional source metadata
- schema and baseline summaries
- preprocessing history
- lifecycle state
- `accepted_as_ground_truth`

`DataProfile` records are immutable. Cleaning or preprocessing that changes data should create a new dataset version and a new `DataProfile`.
