# Artifact Mirrors

> **Role:** Filesystem technical reference. **Canonical concept owner:**
> [Research-state model](../docs/research-state-model.md).
> **Contributor entry:** [Contributor documentation](../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../docs/current-state.md).

This directory contains reviewable metadata mirror templates. Runtime truth is
the workspace-local SQLite persistence layer, not these files.

Current mirror surface:

- `artifacts/data_profiles/`: `DataProfile` JSON mirror templates for profiled dataset versions.

DataProfile mirrors store dataset identity directly. There is no separate dataset artifact in the research ontology.
