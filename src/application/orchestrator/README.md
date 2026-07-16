# Durable Execution Orchestrator

## Current implementation

This package does not contain a generic request orchestrator. It implements the durable execution-attempt and scientific-finalization path:

| Module | Current responsibility |
| --- | --- |
| `execution_contracts.py` | Validate/revalidate prepared planner execution contracts. |
| `execution_admission.py` | Build the typed PlannerOperation admission bundle. |
| `planner_commit.py` | Apply approved operations; special-case atomic execution/scientific bundles. |
| `transition_service.py` | Sole owner of attempt admission, CAS, lease, fencing, cancellation and recovery writes. |
| `dispatcher.py` | Claim pending outbox attempts and call an injected executor. |
| `receiver.py` | Canonicalize/digest results and persist them through the transition owner. |
| `finalizer.py` | Claim fenced finalization and commit scientific artifacts plus attempt/inbox transitions. |
| `scientific_processing.py` | Validate one deterministic-test result and draft AnalysisFrame/Evidence/Discovery/lifecycle/SessionFrame operations. |
| `reconciler.py` | Retry pending inbox finalization and handle expired leases. |
| `cancellation.py` | Thin cancellation, release and retry APIs over the transition service. |

There are no `application_orchestrator.py`, `request_pipeline.py` or `response_pipeline.py` files.

## Known deviations

- `authorize_new_attempt()` currently cannot complete a retry and conflicts with the one-Task/one-Hypothesis invariant.
- An outbox-only execution bundle can be marked committed without inserting an outbox row.
- No process/worker bootstrap invokes dispatcher/reconciler loops.
- External executor side effects remain at-least-once.
- Scientific processing supports one narrow deterministic-test contract, not a generic analytical engine.
