# Governance Application Context (`application.governance`)

## 1. Purpose
`application.governance` owns authenticated decision authority issuance, proposal authority extraction, durable proposal decision recording, and deterministic governance fingerprint calculations.

## 2. Why the package exists
Package S2-A decomposed governance decision authority out of `application.orchestrator` into an explicit bounded context. Governance binds an exact `DiscoveryProposal` to independently issued, durable user decision authority before Discovery admission.

## 3. Owned authority
- Resolving authenticated principal context (`AuthenticatedPrincipalResolver`).
- Issuing bounded, fixed-purpose, expiring governance authority grants (`GovernanceAuthorityIssuer`).
- Verifying proposal authority, principal bindings, proposal digests, and authority fingerprints (`decision_service.py`).
- Persisting durable `ProposalDecisionRecord` entries (`decision_service.py`).
- Calculating pure deterministic governance fingerprints (`fingerprints.py`).
- Constructing detached `DiscoveryAdmissionPlan` objects for future admission cutover.

## 4. Forbidden responsibilities
- Evaluating Hypotheses or calling Hypothesis Analyst.
- Inventing scientific claims or modifying proposal text.
- Admitting `Discovery` records into persistence (owned by `AtomicDiscoveryAdmissionService`).
- Marking `EvaluationControlRecord` as `COMMITTED` (owned by `AtomicDiscoveryAdmissionService`).
- Transitioning `Hypothesis` or `Task` lifecycle state.
- Appending `SessionFrame` records.
- Creating default anonymous principals or fake production authority.

## 5. Canonical input and output
- **Input**: `authentication_context_id`, `evaluation_id`, `authority_id`, and explicit `GovernanceDecisionOutcome` (e.g. `APPROVED`).
- **Output**: A persisted `ProposalDecisionRecord` bound to the exact proposal digest, evaluation key, actor, workspace, session, and decision fingerprint.

## 6. Happy path
```text
Authenticated principal context
  -> issue_user_authority (GovernanceAuthorityIssuer) -> GovernanceAuthorityRecord
  -> record_governance_decision (DiscoveryAdmissionGovernanceService)
  -> verify_authorization + verify proposal/bundle digest
  -> persist ProposalDecisionRecord (unconsumed)
```

## 7. Failure, retry, reclaim, and replay
- **Expired/Invalid authority**: Fails closed with `ProposalAuthorizationError`.
- **Mismatch (principal/session/proposal/evaluation)**: Fails closed with `ProposalAuthorizationError`.
- **Same-decision replay**: Re-submitting the exact same decision with the same authority is idempotent.
- **Conflicting decision**: Submitting a different decision for the same proposal raises `ProposalDecisionConflictError`.

## 8. Transaction owner
`DiscoveryAdmissionGovernanceService` is the sole writer for `ProposalDecisionRecord` entries during decision submission.

## 9. Exact decision binding
Each decision record binds `evaluation_id`, `evaluation_key`, `hypothesis_id`, `task_id`, `proposal_digest`, `bundle_digest`, `evidence_set_digest`, `actor`, `authority_id`, `workspace_id`, and `session_id`, protected by an immutable `decision_fingerprint`.

## 10. Tests proving the boundary
- `tests/application/governance/test_proposal_authorization.py`
- `tests/repositories/governance/test_proposal_decision_races.py`

## 11. Current limitations
- Production deployment must supply an explicit `AuthenticatedPrincipalResolver`.
- No supported CLI, service API, or background daemon loop is checked in.
- Persistence guarantees are verified for SQLite boundaries.

## 12. Deferred S2-B/S3 work
- Atomic Discovery admission remains under `application.orchestrator.atomic_discovery_admission` until S2-B.
- Full repository normalization is deferred to S3.
