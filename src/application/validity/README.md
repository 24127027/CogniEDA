# Validity Propagation Bounded Context (`application.validity`)

## 1. Purpose and current implementation

This package owns deterministic validity propagation planning and the atomic validity propagation transaction.

## 2. Authority

- `AtomicValidityPropagationService` is the sole validity writer.
- `propagation_plan.py` is the single owner of event/source policy, authority scoping, and the
  public read-only plan entry point. `AtomicValidityPropagationService.plan_propagation` performs
  the exact authority and repository reconstruction used by both planning and execution.

### Modules

| Module | Responsibility |
| --- | --- |
| `propagation_plan.py` | Event/source policy, authority scoping, and public read-only plan entry point (`build_validity_propagation_plan`). |
| `propagation_service.py` | Repository-backed deterministic plan reconstruction and the atomic validity propagation transaction (`AtomicValidityPropagationService`). |

## 3. Forbidden responsibilities

- Deleting historical scientific records or mutating durable Evidence statements.
- Rewriting original Discovery claims or Evidence observations.
- Using Assumptions as invalidation premises for Discovery validity.
- Authoring scientific claims or evaluating hypotheses.

## 4. Inputs and outputs

- Accepts a versioned `ValidityPropagationCommand` bound to exact source state/fingerprint,
  reason, event operation, durable authority, workspace/session, idempotency key, and optional
  replacement.
- User-governed commands require the exact authenticated principal; trusted-internal commands
  require an allow-listed durable producer.
- Outputs `ValidityPropagationResult` containing committed or replayed transition counts across evidence, evaluation, admission claims, discoveries, hypotheses, tasks, and session frames.

## 5. Happy path

```text
Authorized source invalidation/supersession command
  -> build_validity_propagation_plan (propagation_plan.py)
  -> execute_propagation (propagation_service.py)
  -> atomic source state update + dependent target transitions + ValidityEvent append
```

## 6. Failure, retry, replay, fencing, and recovery

- Replay with identical command and request fingerprint returns exact committed result.
- Replay with a changed command conflicts; stale source/target fingerprints raise
  `StaleValidityPropagationError`.
- Rollbacks atomically on any failure or injected fault.

## 7. Transaction owner

- `AtomicValidityPropagationService` is the sole transaction owner.

## 8. Dependent invalidation & active retrieval exclusion

Dependent Evidence, EvaluationControl, admission claims, and Discoveries are marked
`INVALIDATED`/`SUPERSEDED`; Hypotheses/Tasks receive review state, and affected SessionFrames
become stale/superseded. Invalidated objects are excluded from active retrieval while remaining
historically traceable. Assumptions are not propagation dependencies.

## 9. Write set

- Source record validity/lifecycle update
- Dependent Evidence lifecycle update
- Dependent EvaluationControl state update
- Dependent DiscoveryAdmissionClaim state update
- Dependent Discovery lifecycle update
- Dependent Hypothesis status update
- Dependent SessionFrame staleness update
- Immutable `ValidityEventRecord` insert

## 10. Tests

- `tests/application/validity/test_validity_propagation.py`

## 11. Limitations

Implementation guarantees are SQLite-only. Provenance-corruption commands are supported only for
AnalysisFrame and ExecutionRun sources. No event bus, CLI, API, or background worker is checked in.

## 12. Deferred S3 work

Automated invalidation trigger networks, distributed transactions, and event-bus dispatchers are
deferred.
