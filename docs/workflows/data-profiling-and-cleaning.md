# Data profiling and cleaning

This supporting workflow applies the canonical data-state rules:

- DataProfile is immutable.
- Raw data is never overwritten by a governed transformation.
- Cleaning creates a new dataset version and a new DataProfile.
- Transformation decisions and lineage must remain explicit.
- Evidence and Discovery remain scoped to the DataProfile they used.

## Implementation status

**Partially implemented.** **Verified on SQLite.** Deterministic local dataframe
and supported-file profiling can produce a typed DataProfile, and repository
persistence is exercised on SQLite. Executable DVC identity resolution,
cleaning execution, approval, derived-dataset creation, and complete validity
propagation are **Unsupported**.

The exact current boundary is owned by [Current state](../status/current-state.md).
See [Validity propagation](../concepts/validity/validity-propagation.md) for the
target consequence model.
