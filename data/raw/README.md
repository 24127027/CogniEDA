# Raw Data

> **Role:** Filesystem technical reference. **Canonical concept owner:**
> [Research-state objects and roles](../../docs/concepts/research-state/objects-and-roles.md).
> **Contributor entry:** [Contributor documentation](../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../docs/current-state.md).

Place immutable source snapshots here.

Do not overwrite raw files in place. A new source snapshot should create a new dataset version and a new `DataProfile`.

Executable DVC integration is not implemented yet. When added, DVC metadata should feed `DataProfile.dvc_hash` or an equivalent version identity.
