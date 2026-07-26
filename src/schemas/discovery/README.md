# Discovery Schemas (`schemas.discovery`)

> **Role:** Package technical reference. **Canonical concept owner:**
> [Governance and Discovery admission](../../../docs/governance-and-discovery-admission.md).
> **Contributor entry:** [Contributor documentation](../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../docs/current-state.md).

## Current implementation

This package owns canonical schemas for Discovery admission planning and transaction result envelopes.

### Exported contracts

- `DiscoveryClaimSnapshot`: Immutable exact scientific claim payload snapshot.
- `ValidityBasisSnapshot`: Immutable exact validity basis snapshot.
- `FutureAtomicWriteSet`: Complete current atomic write-operation manifest. The historical class
  and serialized field names are retained to avoid changing the S2-A contract shape.
- `DiscoveryAdmissionPlan`: Detached deterministic admission plan.
- `AtomicDiscoveryAdmissionResult`: Result envelope for atomic Discovery admission transactions.
- `DiscoveryAdmissionLease`: Fenced lease authority for one admission attempt.

## Ownership boundary

All models in this package are deep-frozen (`frozen=True`) with `extra="forbid"`. They import no application or repository logic.
