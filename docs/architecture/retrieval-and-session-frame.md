# Retrieval Engine & SessionFrame Active Context

> **Status**: `[Implemented]` / `[Verified on SQLite]`

CogniEDA implements active retrieval context filtering anchored to user-governed `SessionFrame` state.

---

## 1. `SessionFrame` Role

`SessionFrame` (`src/schemas/research/session_frame.py`) tracks active user context:
- `active_objective_id`: Current active research objective.
- `focal_task_id`: Currently selected focus task.
- `active_data_profile_id`: Ground-truth dataset profile in scope.
- `working_hypotheses`: Currently active hypotheses under evaluation.

---

## 2. Retrieval Filtering Rules

1. **Active Context Exclusion**: Invalidated `Discovery`, `Evidence`, or `Hypothesis` objects are strictly excluded from active retrieval.
2. **Assumption Isolation**: `Assumption` objects are returned during Planning retrieval, but excluded from Conclusion retrieval.
3. **Completed Hypothesis Bounding**: Completed hypotheses without valid claims are excluded from future planning synthesis.

---

## 3. Graph Miner & Future Retrieval Extensions

> [!NOTE]
> Advanced vector retrieval, semantic graph indexing, and Graph Miner capabilities are **deferred** until future product packages. Active retrieval currently operates via direct relational queries over SQLite.
