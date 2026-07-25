# Task to Hypothesis Workflow

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This guide documents planning decomposition, task creation, and 1:1 hypothesis binding.

---

## 1. Workflow Summary

```text
Objective
└──> Planner Node (expand_plan)
     └──> Task Creation (TaskRecord)
          └──> Analytical Focus Check
               └──> 1:1 Hypothesis Binding (HypothesisRecord)
```

---

## 2. Step-by-Step Specification

1. **Preconditions**: Active `Objective` and valid `DataProfile` bound in `SessionFrame`.
2. **Inputs**: Research question or natural language planning prompt.
3. **Responsible Components**: Planner Nodes (`src/agents/planner/nodes.py`), Task Commit Service (`src/repositories/research/task.py`).
4. **Durable Writes**: Staged `PlannerOperationRecord`s committed atomically into `tasks` and `hypotheses` tables.
5. **Invariants**:
   - Only **terminal analytical tasks** generate `Hypothesis` objects.
   - One terminal analytical task generates **exactly one** `Hypothesis`.
   - Parent tasks do not generate hypotheses.
6. **Resulting State**: `TaskRecord` (`status='READY'`) and `HypothesisRecord` (`status='PROPOSED'`).
