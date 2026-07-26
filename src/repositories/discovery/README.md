# Discovery Repositories (`repositories.discovery`)

> **Role:** Package technical reference. **Canonical concept owner:**
> [Discovery governance and admission](../../../docs/concepts/scientific-lifecycle/discovery-governance-and-admission.md).
> **Contributor entry:** [Contributor documentation](../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../docs/current-state.md).

## Current implementation

This package owns persistence access for Discovery admission claims and durable `Discovery` FCO records.

### Exported classes

- `DiscoveryAdmissionClaimRepository`: Read access plus private
  `_stage_*_from_atomic_admission` hooks for `DiscoveryAdmissionClaimRecord`s.
- `DiscoveryRepository`: Query and read access for `Discovery` records. Public creation is disabled (`create()` raises `RuntimeError`); staging is allowed only via `_stage_create_from_atomic_admission` called by `AtomicDiscoveryAdmissionService`.

## Ownership boundary

Repositories in this package import no application service logic.
They do not commit. Mutable claim hooks are private and can participate only in the
`AtomicDiscoveryAdmissionService` transaction boundary.
