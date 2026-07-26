# Validity Repositories (`repositories.validity`)

Canonical transaction explanation:
[Atomic validity propagation](../../../docs/atomic-validity-propagation.md).

## Current implementation

This package owns stage-only persistence and dependency graph traversal for immutable `ValidityEventRecord`s.

### Exported classes

- `ValidityEventRepository`: Private `_stage_event_from_atomic_propagation` insertion, lookup by
  idempotency key / event ID, and deterministic lineage traversal (`discover_dependents`).
- `ValidityDependencyError`: Exception raised when durable lineage is incomplete or contradictory.

## Ownership boundary

Repositories in this package import no application service logic.
The repository does not commit and exposes no public event writer.
