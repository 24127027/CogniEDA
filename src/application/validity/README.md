# Validity Application Package (`src/application/validity/`)

> Canonical Documentation: [ADR-005: Atomic Validity Propagation](../../docs/decisions/ADR-005-atomic-validity-propagation.md) | [Validity Propagation Workflow](../../docs/workflows/validity-propagation.md)

## Purpose
Owns invalidation event issuance and atomic state propagation across dependent research state objects.

## Owned Responsibilities
- `AtomicValidityPropagationService` (`propagation_service.py`).
- Atomic transaction persisting `ValidityEventRecord`.
- Updating dependent target entities (`AnalysisFrameRecord`, `HypothesisRecord`, `DiscoveryAdmissionClaimRecord`) to `INVALIDATED`.
- Triggering retrieval index exclusion for invalidated entities.

## Forbidden Responsibilities
- Direct FCO deletion.
- Mutating historical evidence content.

## Canonical Inputs / Outputs
- Input: `ValidityPropagationRequest` (source fingerprint, target ID, authority token, reason).
- Output: `ValidityPropagationResult` (persisted event ID, list of affected target IDs).

## Transaction Authority
Sole transaction owner for `ValidityEventRecord` insertion and `INVALIDATED` validity state updates.

## Tests
- `tests/application/validity/test_validity_propagation.py`
