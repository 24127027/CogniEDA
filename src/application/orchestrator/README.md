# Remaining Application Orchestrator (`application.orchestrator`)

## 1. Purpose and current implementation

This transitional package contains the remaining atomic Discovery admission and validity-propagation services. Package S1-B moved execution coordination to `application.execution` and Evidence admission to `application.evidence`. Package S2-A moved protected evaluation to `application.evaluation` and governance decision authority to `application.governance`.

## 2. Authority

The package retains two distinct authorities:

- `AtomicDiscoveryAdmissionService` is the sole Discovery writer.
- `AtomicValidityPropagationService` is the sole validity writer.

### Remaining modules

| Module | Current responsibility |
| --- | --- |
| `planner_commit.py` | Apply approved operations; special-case atomic execution/scientific bundles. |
| `atomic_discovery_admission.py` | Sole writer for Discovery, decision consumption, evaluation commit, Hypothesis/Task terminal transitions, and conclusion SessionFrame. |
| `discovery_admission_coordinator.py` | Coordinates governance decision check and atomic Discovery admission. |
| `validity_propagation_service.py` | Sole writer for validity propagation and dependent invalidation/review state. |
| `review_propagation.py` | Propagates review markers across motivated tasks. |

## 3. Forbidden responsibilities

- Execution attempt admission, dispatch, receipt, cancellation, retry, or recovery.
- AnalysisFrame or Evidence creation.
- Canonical execution/Data Explorer schema ownership.
- Protected bundle construction (owned by `application.evaluation`).
- Evaluation attempt transitions or evaluator runner (owned by `application.evaluation`).
- Governance authority issuance or decision recording (owned by `application.governance`).
- Rewriting Hypothesis Analyst claim wording during Discovery admission.

## 4. Inputs and outputs

- Atomic Discovery admission accepts an evaluation ID and authorized decision ID, outputting one Discovery plus its lifecycle and conclusion-frame companions.
- Validity propagation accepts a typed authorized command and outputs one atomic transition result.

## 5. Happy path

```text
READY_FOR_EVALUATION Hypothesis + admitted Evidence
  -> protected evaluation (application.evaluation)
  -> durable DiscoveryProposal
  -> authenticated governance decision (application.governance)
  -> AtomicDiscoveryAdmissionService (application.orchestrator)
  -> Discovery + terminal lifecycle + conclusion SessionFrame
  -> optional authorized AtomicValidityPropagationService command (application.orchestrator)
```

## 6. Failure and recovery

Discovery-admission claims use durable control records and fencing. Invalid,
expired, mismatched, or replayed authority fails closed. Recovery coordinators may resume eligible
claims but do not become Discovery or validity transaction owners.

## 7. Transaction owners

- `AtomicDiscoveryAdmissionService` owns the single Discovery admission commit.
- `AtomicValidityPropagationService` owns the single validity propagation commit.

## 8. Retry, replay, and fencing

Discovery admission binds exact proposal/bundle digests and durable claim epochs.
Identical governed replays are idempotent; changed payloads or lost authority do not become retries.
Validity propagation uses command/authority fingerprints and compare-and-swap transitions.

## 9. Tests

- `tests/application/orchestrator/test_atomic_discovery_admission.py`
- `tests/application/orchestrator/test_validity_propagation.py`

## 10. Limitations

The implemented transaction and recovery guarantees are SQLite-only. Deployment must provide
authentication and model adapters. No supported CLI, service API, or background worker is checked
in.

## 11. Moved in S2-A

- Synthesis bundle construction -> `application.evaluation.bundle_builder`
- Evaluator runner -> `application.evaluation.runner`
- Evaluation transition service -> `application.evaluation.transition_service`
- Governance authority & decision service -> `application.governance`

## 12. Deferred S2-B/S3 work

Remaining Discovery admission and validity modules will be decomposed into dedicated bounded contexts in subsequent packages (S2-B/S3).
