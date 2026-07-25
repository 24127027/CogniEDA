# Discovery Repositories (`repositories.discovery`)

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
