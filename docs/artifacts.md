# Artifact notes

This supporting page describes repository surfaces, not a second object model.

- `artifacts/data_profiles/` contains tracked templates or review mirrors; it
  is not the operational source of truth.
- `data/` provides filesystem locations for local datasets; directory presence
  is not a governed ingestion workflow.
- Runtime research-state persistence uses the configured SQLModel store.

Use the [object catalog](reference/object-catalog.md) for canonical
classification and [Current state](status/current-state.md) for verified
persistence support.
