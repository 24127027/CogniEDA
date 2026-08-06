# Data versioning

This supporting page states the target guardrails for local data work:

- keep source data immutable;
- record every transformation in explicit lineage;
- create a new dataset version and immutable DataProfile when data changes;
- bind downstream scientific state to the exact admitted DataProfile;
- keep tracked review mirrors separate from operational persistence.

## Implementation status

**Partially implemented.** DataProfile carries caller-supplied optional DVC
identity and preprocessing history. Executable DVC identity resolution and a
governed transformation workflow are **Unsupported**. See
[Current state](status/current-state.md) for the verified boundary.
