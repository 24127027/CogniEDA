# Durable Application Orchestrator

## Current implementation

This package temporarily contains the remaining governance, Discovery admission, evaluation runner, and validity propagation services.

Following **Package S1-B**, execution and Evidence admission responsibilities have been decomposed into dedicated bounded contexts:

- **`src/application/execution/`**: Owns execution attempt admission, transition service, dispatch, result receiving, cancellation, and reconciliation.
- **`src/application/evidence/`**: Owns Evidence admission plan validation and the atomic AnalysisFrame + Evidence admission write transaction.
- **`src/schemas/execution/`**: Owns canonical execution contracts, observations, and Data Explorer schemas.

### Remaining orchestrator modules

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

There are no `application_orchestrator.py`, `request_pipeline.py` or `response_pipeline.py` files.

## Decomposed responsibilities (Moved in S1-B)

- Execution attempt admission -> `application.execution.admission`
- Execution attempt state transitions -> `application.execution.transition_service`
- Executor dispatch -> `application.execution.dispatch`
- Executor receipt intake -> `application.execution.receiver`
- Cancellation and retry -> `application.execution.cancellation`
- Attempt reconciliation & recovery -> `application.execution.recovery`
- Evidence admission plan & validation -> `application.evidence.admission_plan`
- Atomic Evidence admission transaction -> `application.evidence.admission_service`
- Canonical execution schemas -> `schemas.execution`

## Future allocation

Remaining governance, Discovery admission, evaluation, and validity modules will be decomposed into dedicated bounded contexts in subsequent packages (S2/S3).
