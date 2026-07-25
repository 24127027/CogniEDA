# Orchestrator Application Package (`src/application/orchestrator/`)

> Canonical Documentation: [Bounded Contexts](../../docs/architecture/bounded-contexts.md) | [Task to Hypothesis Workflow](../../docs/workflows/task-to-hypothesis.md)

## Purpose
Owns planner commit transaction coordination and approval-gated task/hypothesis persistence.

## Owned Responsibilities
- `commit_planner_operations` service.
- Atomically persisting approved `PlannerOperation` batches into `tasks`, `hypotheses`, and `objectives`.

## Forbidden Responsibilities
- Direct execution run management (owned by `application.execution`).
- Direct evidence admission (owned by `application.evidence`).
- Direct discovery admission (owned by `application.discovery`).

## Canonical Inputs / Outputs
- Input: Approved `PlannerOperation` list, session ID.
- Output: `CommitPlannerOperationsResult`.

## Transaction Authority
Transaction owner for committing staged planner operations.

## Tests
- `tests/agents/planner/test_planner_operations.py`
