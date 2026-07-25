# Canonical Governance Schemas (`schemas.governance`)

## Purpose
`schemas.governance` defines canonical value objects and contracts for authenticated principal identity, governance authority grants, proposal authority bindings, and durable proposal governance decisions.

## Modules
- `authority.py`: `AuthenticatedPrincipal`, `GovernanceAuthority`, `ProposalAuthority`.
- `decision.py`: `GovernanceDecision`.

## Invariants
1. All models use Pydantic `extra="forbid"` and frozen immutable semantics.
2. Authority grants and decision contracts are bound to explicit workspace and session boundaries.
3. No default anonymous principal or unauthenticated decision contracts exist.
