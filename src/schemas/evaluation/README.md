# Canonical Evaluation Schemas (`schemas.evaluation`)

## 1. Purpose

This package owns the canonical typed boundary for protected Hypothesis evaluation.

## 2. Authority

- `snapshots.py` owns immutable Hypothesis, DataProfile, AnalysisFrame, ExecutionRun, Evidence,
  parameter, result, and decision-rule snapshots.
- `bundle.py` owns `DiscoverySynthesisBundle`, the closed provenance manifest, and its vocabularies.
- `results.py` owns `DiscoveryProposal`, `EvaluationFailure`, proposal digesting, and bundle
  validation.

## 3. Forbidden responsibilities

Schemas do not import application/repository code, persist state, carry generic context,
re-export execution contracts, or define governance/Discovery-admission authority.

## 4. Inputs and outputs

Repository-authoritative domain values enter snapshot constructors. The package produces a frozen
protected bundle/manifest and the typed Analyst result union. Unknown fields fail validation.

## 5. Happy path

```text
typed snapshots -> DiscoverySynthesisBundle -> DiscoveryProposal | EvaluationFailure
```

## 6. Failure, retry, reclaim, and replay

Schema validation fails closed for unknown fields, noncanonical ordering, duplicate lineage, or
mismatched scope/evidence. Durable retry, reclaim, and replay belong to
`application.evaluation`.

## 7. Transaction owner

None. These are Pydantic contracts and pure validation/digest helpers.

## 8. Binding and fingerprints

The bundle digest covers every scientific input except its own digest field. The proposal digest
covers the exact proposal plus source bundle digest. Canonical JSON/hash behavior is owned by
`schemas.canonical`.

## 9. Tests

- `tests/schemas/evaluation/test_evaluation_contracts.py`
- `tests/application/evaluation/test_synthesis_bundle.py`
- `tests/application/evaluation/test_bundle_digest.py`

## 10. Limitations

These contracts do not supply a model provider, persistence, worker loop, or broader Graph Miner
context. `DiscoveryProposal` remains lifecycle-distinct from durable `Discovery`.
