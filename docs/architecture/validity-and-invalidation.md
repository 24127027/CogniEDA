# Validity Engine & Invalidation Propagation

> **Status**: `[Implemented]` / `[Verified on SQLite]`

CogniEDA enforces scientific validity through deterministic source fingerprinting, immutable validity events, and atomic dependent-state invalidation.

---

## 1. Source Fingerprints & Invalidation Triggers

Invalidation occurs when an upstream premise or computation becomes invalid or superseded:

| Source Type | Cause for Invalidation | Invalidation Effect |
| :--- | :--- | :--- |
| **DataProfile** | Data cleaning, filtering, re-ingestion | Invalidation of all dependent `AnalysisFrame`, `Evidence`, `Hypothesis`, and `Discovery` records |
| **Execution Method** | Parameter change, code bug, algorithm revision | Invalidation of dependent `ExecutionRun`, `Evidence`, and downstream claims |
| **User Invalidation** | Explicit rejection of an analytical step | Invalidation of target `Hypothesis` and dependent discoveries |

---

## 2. Invalidation vs. Flagging

- **Invalidation**: An immutable event (`ValidityEventRecord`) issued by `AtomicValidityPropagationService`. It changes target validity state to `INVALIDATED` and excludes the target from active retrieval and conclusion contexts.
- **Flagging**: A review signal created when a new `Discovery` contradicts an active `Assumption`. Flagging does **not** mutate truth or invalidate objects; it notifies the user for review.
- **Assumption Replacement**: Updating an `Assumption` does **not** invalidate prior `Discovery` objects, because discoveries depend on empirical `Evidence`, not assumptions.

---

## 3. Atomic Propagation Semantics

- **Owner**: `AtomicValidityPropagationService` (`src/application/validity/propagation_service.py`).
- **Atomic Transaction**:
  1. Verifies authority token and source fingerprint.
  2. Persists immutable `ValidityEventRecord`.
  3. Updates dependent target states (`INVALIDATED`).
  4. Triggers retrieval index exclusion so invalidated objects are hidden from active contexts while remaining accessible in historical audit queries.
