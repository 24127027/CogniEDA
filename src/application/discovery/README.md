# Discovery Admission Bounded Context (`application.discovery`)

## 1. Purpose and current implementation

This package owns deterministic Discovery admission planning, admission reconciliation coordination, and the atomic Discovery admission cutover transaction.

## 2. Authority

- `AtomicDiscoveryAdmissionService` is the sole writer for durable `Discovery` FCO creation.
- `admission_plan.py` is the sole owner of deterministic admission identity, plan construction,
  and admission fingerprints. Governance verifies authority and records decisions; it does not
  construct admission plans.

### Modules

| Module | Responsibility |
| --- | --- |
| `admission_plan.py` | Pure deterministic admission plan builder (`build_discovery_admission_plan`). |
| `admission_service.py` | Atomic Discovery admission transaction (`AtomicDiscoveryAdmissionService`). |
| `admission_coordinator.py` | Reconciliation and batch coordinator (`DiscoveryAdmissionCoordinator`). |

## 3. Forbidden responsibilities

- Inventing, rewriting, or altering scientific claim wording or limitations.
- Validity propagation (owned by `application.validity`).
- Execution attempt admission or Evidence creation.
- Evaluator execution or governance decision recording.

## 4. Inputs and outputs

- Accepts an evaluation ID and authorized governance decision ID.
- Outputs `AtomicDiscoveryAdmissionResult` containing the admitted Discovery ID, decision ID, hypothesis ID, task ID, and conclusion SessionFrame ID.

## 5. Happy path

```text
PROPOSAL_READY EvaluationControl + APPROVED ProposalDecision
  -> build_discovery_admission_plan (admission_plan.py)
  -> enqueue_admission & claim_admission (admission_service.py)
  -> execute_claimed_admission (admission_service.py)
  -> Discovery + EvaluationControl COMMITTED + ProposalDecision consumed
     + Hypothesis EVALUATED + Task COMPLETED + conclusion SessionFrame
```

## 6. Failure, retry, replay, fencing, and recovery

- Replay with an identical committed binding returns `IDEMPOTENT`.
- Replay with changed security/scientific binding raises `DiscoveryAdmissionConflictError`.
- A live concurrent claimant loses the claim CAS; a later exact replay verifies and returns the
  committed chain.
- Atomic transaction rollbacks cleanly on any failure or injected fault.

## 7. Transaction owner

- `AtomicDiscoveryAdmissionService` is the sole transaction owner.

## 8. Exact proposal-copy rule

Scientific fields (`claim`, `epistemic_status`, ordered `evidence_ids`, `scope`, `uncertainty`,
`limitations`, and the complete `validity_basis`) are copied exactly from the protected proposal
without normalization, sorting, set conversion, summarization, or rewriting.

## 9. Write set

- Discovery insert
- Admission claim stage commit
- Governance decision consumed transition
- EvaluationControl `COMMITTED` transition
- Hypothesis `EVALUATED` transition
- Analytical Task `COMPLETED` transition
- Conclusion SessionFrame insert

## 10. Tests

- `tests/application/discovery/test_atomic_discovery_admission.py`
- `tests/application/discovery/test_discovery_admission_plan.py`

## 11. Limitations

The transaction implementation and race guarantees are SQLite-only. No CLI, API, or worker
bootstrap is checked in; deployment must supply authentication and Analyst/Data Explorer adapters.

## 12. Deferred S3 work

Broad artifact normalization, production surfaces, and distributed transaction support are
deferred.
