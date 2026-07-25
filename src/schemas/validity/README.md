# Validity Schemas (`schemas.validity`)

## Current implementation

This package owns canonical typed contracts for validity propagation commands, target transitions, plans, and result envelopes.

### Exported contracts

- `ValidityPropagationCommand`: Versioned request contract binding authority ID, exact source
  state/fingerprint, event/reason, scope, idempotency key, and optional replacement guard.
- `ValidityTargetTransition`: Closed write specification for one affected dependent object.
- `ValidityPropagationPlan`: Detached complete write set description.
- `ValidityPropagationResult`: Execution result envelope for atomic validity propagation.
- `ValidityTargetType`: Discriminator type for valid propagation targets.

## Ownership boundary

All models in this package are deep-frozen (`frozen=True`) with `extra="forbid"`. They import no application or repository logic.
The current serialized contract version is `validity-propagation/v1`.
