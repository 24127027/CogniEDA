# Discovery Application Package (`src/application/discovery/`)

> Canonical Documentation: [ADR-004: Atomic Discovery Admission](../../docs/decisions/ADR-004-atomic-discovery-admission.md) | [Evidence to Discovery Workflow](../../docs/workflows/evidence-to-discovery.md)

## Purpose
Owns atomic materialization and fenced claim validation for `Discovery` objects.

## Owned Responsibilities
- `AtomicDiscoveryAdmissionService` (`admission_service.py`).
- Atomic transaction materializing `DiscoveryRecord` from an authorized `DiscoveryProposal`.
- Verifying exact proposal copy rule and fencing claim consumption.
- Transitioning `EvaluationControlRecord` to `COMMITTED` and `ProposalDecisionRecord` to `consumed=1`.

## Forbidden Responsibilities
- Authoring scientific proposals (owned by Hypothesis Analyst).
- Making user governance decisions (owned by `application.governance`).
- Public `DiscoveryRepository.create()` calls.

## Canonical Inputs / Outputs
- Input: `DiscoveryAdmissionRequestPayload` (containing decision ID, evaluation ID, proposal digest, claim token).
- Output: `AtomicDiscoveryAdmissionResult` (containing committed `Discovery`, `DiscoveryAdmissionClaimRecord`).

## Transaction Authority
Sole transaction owner for `Discovery` creation and `EvaluationControlRecord.COMMITTED` state transitions.

## Tests
- `tests/application/discovery/test_atomic_discovery_admission.py`
