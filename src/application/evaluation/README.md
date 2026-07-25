# Protected Evaluation Application Context (`application.evaluation`)

## 1. Purpose
`application.evaluation` owns the application-level evaluation workflow prior to governance decision recording and Discovery admission. It constructs protected synthesis bundles, manages evaluation attempt state transitions, fences stale attempts, and invokes the Hypothesis Analyst.

## 2. Why the package exists
Package S2-A decomposed protected evaluation out of the flat `application.orchestrator` package into a dedicated bounded context. Evaluation is distinct from execution, Evidence admission, governance decision authority, and atomic Discovery admission.

## 3. Owned authority
- Constructing immutable `DiscoverySynthesisBundle` and closed `BundleProvenanceManifest` objects from durable repository authority (`bundle_builder.py`).
- Managing durable `EvaluationControlRecord` state transitions, CAS claims, fencing epochs, and retries (`transition_service.py`).
- Coordinating Hypothesis Analyst invocation and publishing exact `DiscoveryProposal` or `EvaluationFailure` outputs without mutating scientific claim wording (`runner.py`).

## 4. Forbidden responsibilities
- Calling execution or Data Explorer tools.
- Admitting Evidence or creating `AnalysisFrame`s.
- Inventing scientific claims or modifying Analyst wording.
- Issuing governance authority grants or recording user proposal decisions.
- Admitting `Discovery` records into persistence (owned by `AtomicDiscoveryAdmissionService`).
- Mutating `Hypothesis` or `Task` lifecycle state (owned by `AtomicDiscoveryAdmissionService`).
- Including `Assumption`s, generic context bags, raw chat, or prior Discoveries in protected bundles.

## 5. Canonical input and output
- **Input**: A `READY_FOR_EVALUATION` `Hypothesis` ID plus its active admitted `Evidence` set and `AnalysisFrame` lineage.
- **Output**: A persisted `EvaluationControlRecord` in `PROPOSAL_READY` state (binding an exact `DiscoveryProposal` and bundle digest) or a failed attempt in `RETRYABLE_FAILED` / `NON_RETRYABLE_FAILED` state.

## 6. Happy path
```text
READY_FOR_EVALUATION Hypothesis + active Evidence
  -> build_synthesis_bundle (bundle_builder.py)
  -> enqueue_evaluation (transition_service.py) -> PENDING control
  -> claim_evaluation -> CLAIMED control (epoch N)
  -> evaluate_synthesis_bundle (Hypothesis Analyst)
  -> publish_proposal -> PROPOSAL_READY control + proposal_digest
```

## 7. Failure, retry, reclaim, and replay
- **Technical/Model failure**: Recorded as `RETRYABLE_FAILED` or `NON_RETRYABLE_FAILED` in `EvaluationControlRecord`.
- **Retry**: `retry_evaluation` validates current bundle identity and resets state to `PENDING` with an incremented attempt number.
- **Stale bundle / fence loss**: If underlying evidence or lineage changes during evaluation, CAS publication fails and transitions control to `INVALIDATED`.
- **Replay**: Re-publishing an identical proposal under the same claim is idempotent.

## 8. Transaction owner
`EvaluationTransitionService` is the sole writer for `EvaluationControlRecord` lifecycle state transitions.

## 9. Exact proposal binding
The published proposal is stored exactly as returned by Hypothesis Analyst (`serialized_proposal`) and bound to the source bundle by `proposal_digest = canonical_sha256({"source_bundle_digest": bundle.input_digest, "proposal": proposal})`.

## 10. Tests proving the boundary
- `tests/application/evaluation/test_synthesis_bundle.py`
- `tests/application/evaluation/test_hypothesis_analyst_execution.py`
- `tests/application/evaluation/test_bundle_digest.py`
- `tests/repositories/evaluation/test_evaluation_control_repository.py`

## 11. Current limitations
- Fencing and CAS transitions are verified for SQLite persistence boundaries.
- Model invocation requires explicit PydanticAI provider configuration.
- No supported CLI, service API, or background daemon loop is checked in.

## 12. Deferred S2-B/S3 work
- Atomic Discovery admission remains under `application.orchestrator.atomic_discovery_admission` until S2-B.
- Broad repository normalization is deferred to S3.
