# Orchestrator Application Package

Canonical references:
[Persistence and transaction ownership](../../../docs/persistence-and-transaction-ownership.md),
[Planner boundary and operation model](../../../docs/planner-boundary-and-operation-model.md),
[Bounded Contexts](../../../docs/architecture/bounded-contexts.md), and
[Task to Hypothesis](../../../docs/workflows/task-to-hypothesis.md).

`commit_planner_operations` commits approved Planner operations for Objective,
Task, Assumption, Hypothesis, and ordinary SessionFrame state. Execution
admission is delegated to `ExecutionAttemptTransitionService`.

The generic commit path rejects AnalysisFrame, Evidence, and Discovery creation
and cannot write terminal Task/Hypothesis scientific states. Planner nodes still
know SQLModel sessions and repositories; a narrower application facade is
documented non-blocking debt.

The current verdict and extraction triggers are maintained by the Planner
canonical owner above; this package README retains only contributor-level
source orientation.

This package coordinates Planner-operation commits. It is not the runtime
composition root and does not own the scientific cutovers delegated to their
application services.

Primary verification: Planner tests under `tests/agents/planner` and
`tests/application/orchestrator`.
