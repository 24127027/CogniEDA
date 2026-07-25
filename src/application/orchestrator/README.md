# Remaining Application Orchestrator (`application.orchestrator`)

## 1. Purpose and current implementation

This transitional package contains the remaining protected evaluation, governance, Discovery
admission, and validity-propagation services. Package S1-B moved execution coordination to
`application.execution`, Evidence admission to `application.evidence`, and canonical execution
contracts to `schemas.execution`.

## 2. Authority

The package retains three distinct authorities:

- `AtomicDiscoveryAdmissionService` is the sole Discovery writer.
- `AtomicValidityPropagationService` is the sole validity writer.
- The protected evaluation control/governance services bind an exact Hypothesis Analyst proposal
  to durable user authority before Discovery admission.

### Remaining modules

| Module | Current responsibility |
| --- | --- |
| `planner_commit.py` | Apply approved operations; special-case atomic execution/scientific bundles. |
| `evaluator_runner.py` | Claim a protected bundle evaluation and publish only a typed proposal or failure. |
| `discovery_admission_governance.py` | Bind an exact proposal to independently issued, durable decision authority. |
| `atomic_discovery_admission.py` | Sole writer for Discovery, decision consumption, evaluation commit, Hypothesis/Task terminal transitions, and conclusion SessionFrame. |
| `discovery_admission_coordinator.py` | Coordinates governance decision check and atomic Discovery admission. |
| `evaluation_transition_service.py` | Manages evaluation attempt state transitions and CAS claims. |
| `synthesis_bundle.py` | Reconstructs protected DiscoverySynthesisBundle for Hypothesis Analyst evaluation. |
| `validity_propagation_service.py` | Sole writer for validity propagation and dependent invalidation/review state. |
| `review_propagation.py` | Propagates review markers across motivated tasks. |

## 3. Forbidden responsibilities

- Execution attempt admission, dispatch, receipt, cancellation, retry, or recovery.
- AnalysisFrame or Evidence creation.
- Canonical execution/Data Explorer schema ownership.
- Rewriting Hypothesis Analyst claim wording during Discovery admission.

## 4. Inputs and outputs

- Protected evaluation accepts a repository-built `DiscoverySynthesisBundle` and persists a typed
  `DiscoveryProposal` or `EvaluationFailure`.
- Governance accepts authenticated principal context and an exact proposal decision.
- Atomic Discovery admission outputs one Discovery plus its lifecycle and conclusion-frame
  companions.
- Validity propagation accepts a typed authorized command and outputs one atomic transition result.

## 5. Happy path

```text
READY_FOR_EVALUATION Hypothesis + admitted Evidence
  -> protected evaluation
  -> durable DiscoveryProposal
  -> authenticated governance decision
  -> AtomicDiscoveryAdmissionService
  -> Discovery + terminal lifecycle + conclusion SessionFrame
  -> optional authorized AtomicValidityPropagationService command
```

## 6. Failure and recovery

Evaluation and Discovery-admission claims use durable control records and fencing. Invalid,
expired, mismatched, or replayed authority fails closed. Recovery coordinators may resume eligible
claims but do not become Discovery or validity transaction owners.

## 7. Transaction owners

- `AtomicDiscoveryAdmissionService` owns the single Discovery admission commit.
- `AtomicValidityPropagationService` owns the single validity propagation commit.
- Evaluation transition services own only evaluation-control transitions.

## 8. Retry, replay, and fencing

Evaluation and Discovery admission bind exact proposal/bundle digests and durable claim epochs.
Identical governed replays are idempotent; changed payloads or lost authority do not become retries.
Validity propagation uses command/authority fingerprints and compare-and-swap transitions.

## 9. Tests

- `tests/application/orchestrator/test_hypothesis_analyst_execution.py`
- `tests/application/orchestrator/test_atomic_discovery_admission.py`
- `tests/application/orchestrator/test_validity_propagation.py`
- `tests/repositories/test_execution_scientific_commit_races.py`
- `tests/e2e/test_research_lineage.py`

## 10. Limitations

The implemented transaction and recovery guarantees are SQLite-only. Deployment must provide
authentication and model adapters. No supported CLI, service API, or background worker is checked
in.

## 11. Moved in S1-B

- Execution attempt admission -> `application.execution.admission`
- Execution identity and receipt hashing -> `application.execution.identity`
- Execution attempt state transitions -> `application.execution.transition_service`
- Executor dispatch -> `application.execution.dispatch`
- Executor receipt intake -> `application.execution.receiver`
- Cancellation and retry -> `application.execution.cancellation`
- Attempt reconciliation & recovery -> `application.execution.recovery`
- Evidence admission plan & validation -> `application.evidence.admission_plan`
- Atomic Evidence admission transaction -> `application.evidence.admission_service`
- Canonical execution schemas -> `schemas.execution`

There are no `application_orchestrator.py`, `request_pipeline.py`, or `response_pipeline.py` files.

## 12. Deferred S2/S3 work

Remaining governance, Discovery admission, evaluation, and validity modules will be decomposed into dedicated bounded contexts in subsequent packages (S2/S3).
