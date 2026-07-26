# Task-to-Hypothesis Workflow

> **Implementation status:** **Partially implemented** and **Verified on
> SQLite** for the fresh execution-contract path. Natural-language planning
> branches and existing-Hypothesis reuse remain incomplete.

The canonical Planner owner is
[Planner boundary and operation model](../planner-boundary-and-operation-model.md);
the request-to-approval narrative is
[From user request to approved operation](../from-user-request-to-approved-operation.md).

## Implemented path

```text
approved PlannerOperation
  -> Task committed by commit_planner_operations
  -> prepare_execution validates active analytical terminal Task + active accepted DataProfile
  -> user approves exact execution contract
  -> commit_execution_contract
  -> Hypothesis(TESTING) + admitted ExecutionRun/outbox
```

Planner nodes stage durable `PlannerOperation` and `ExecutionApproval` workflow
records. Approved ordinary research-state operations are committed through
`src/application/orchestrator/planner_commit.py`. Execution approval is
revalidated against current Task and DataProfile state before
`commit_execution_contract` creates the single Hypothesis and stages execution
admission on the fresh path.

## Protected invariants

- Only an active terminal analytical `Task` with an analytical specification can
  enter execution preparation.
- The bound `DataProfile` must be active, accepted as ground truth, and match the
  Task.
- One terminal analytical Task has exactly one Hypothesis.
- Parent/organizing Tasks do not create Hypotheses or execute.
- A proposed Task cannot execute.
- Execution admission places the Hypothesis in `TESTING`; evidence admission
  later transitions it to `READY_FOR_EVALUATION`.

## Boundaries and limitations

`expand_plan` does not directly create a Hypothesis. The binding occurs only
after exact execution-contract approval. Planner nodes still open SQLModel
sessions and know repository/record types; this is documented non-blocking
application-boundary debt. The supported Planner commit path rejects generic
creation of `AnalysisFrame`, `Evidence`, and `Discovery`.

The current existing-Hypothesis branch proposes a generic Hypothesis-state
change that execution-bundle validation rejects because the transition service
owns that lifecycle. It fails closed but is not a supported reuse path.
