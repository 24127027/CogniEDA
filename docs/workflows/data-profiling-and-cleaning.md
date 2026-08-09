# Data profiling and cleaning

This supporting workflow applies the canonical data-state rules:

- DataProfile is immutable.
- Raw data is never overwritten by a governed transformation.
- Cleaning creates a new dataset version and a new DataProfile.
- Transformation decisions and lineage must remain explicit.
- Evidence and Discovery remain scoped to the DataProfile they used.

## Implementation status

**Partially implemented.** Deterministic local dataframe and supported-file
profiling can produce a typed DataProfile without removing duplicate rows,
all-null rows, or missing values and without mutating the input. DataProfile
repository persistence is **Verified on SQLite**. Executable DVC identity
resolution is **Unsupported**; cleaning execution, approval, successor dataset
creation, and complete validity propagation remain **Deferred**.

The exact current boundary is owned by [Current state](../status/current-state.md).
See [Validity propagation](../concepts/validity/validity-propagation.md) for the
target consequence model.
