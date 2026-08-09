# Data versioning

This supporting page states the target guardrails for local data work:

- keep source data immutable;
- record every transformation in explicit lineage;
- create a new dataset version and immutable DataProfile when data changes;
- bind downstream scientific state to the exact admitted DataProfile;
- keep tracked review mirrors separate from operational persistence.

## Implementation status

**Partially implemented.** The active DataProfile is immutable and profiling
describes the supplied dataset without transformation. The infrastructure DVC
adapter fails closed because executable identity resolution is
**Unsupported**. Successor dataset creation, successor DataProfile lineage, and
a governed transformation workflow remain **Deferred**. See [Current
state](status/current-state.md) for the verified boundary.
