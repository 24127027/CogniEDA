# Evaluation Control Repository (`repositories.evaluation`)

## 1. Purpose

This package owns query/staging access for non-FCO `EvaluationControlRecord` rows.

## 2. Authority

`EvaluationControlRepository` provides primary/evaluation-key/bundle/hypothesis queries and a
private staging hook used only by `EvaluationTransitionService`.

## 3. Forbidden responsibilities

The repository does not validate bundles, claim/retry/publish controls, commit transactions, call
the Analyst, or expose a public lifecycle writer.

## 4. Inputs and outputs

Inputs are durable UUID/digest identities and query limits. Outputs are database records or ordered
record lists.

## 5. Happy path

```text
EvaluationTransitionService -> private stage/query -> service-owned commit
```

## 6. Failure, retry, reclaim, and replay

The repository only returns persistence state. CAS failure, retry, reclaim, replay, and conflict
classification belong to `EvaluationTransitionService`.

## 7. Transaction owner

`EvaluationTransitionService` owns evaluation transactions; atomic Discovery admission and
validity propagation retain their explicitly separate terminal/invalidation writes.

## 8. Binding and fingerprints

Queries preserve exact evaluation key, bundle digest, hypothesis, and active-state identities.
Fingerprint construction remains in canonical evaluation schema/application owners.

## 9. Tests

- `tests/repositories/evaluation/test_evaluation_control_repository.py`
- `tests/application/evaluation/test_bundle_digest.py`

## 10. Limitations

Concurrency and partial-index behavior are SQLite-verified. This repository is not a standalone
service API.
