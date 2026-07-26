# Task-to-Hypothesis Workflow

> **Role:** Technical reference. **Canonical concept owner:**
> [Planner operations and approvals](../operations/planner-and-approvals.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Implementation status:** **Partially implemented** and **Verified on
> SQLite** for the fresh execution-contract path. Natural-language planning
> branches and existing-Hypothesis reuse remain incomplete.

The canonical Planner owner is
[Planner operations and approvals](../operations/planner-and-approvals.md);
the request-to-approval narrative is
[Operation approval workflows](../operations/operation-approval-workflows.md).

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
- One eligible terminal analytical Task has at most one Hypothesis.
- Parent/organizing Tasks create neither Hypotheses nor Discoveries and do not
  execute.
- A proposed Task cannot execute.
- Execution admission places the Hypothesis in `TESTING`; evidence admission
  later transitions it to `READY_FOR_EVALUATION`.

“At most one” is a cardinality rule, not a guarantee that every Task reaches
scientific admission. A cancelled or technically failed execution creates no
Discovery. Evaluation failure creates no proposal, and governance rejection or
cancellation creates no Discovery. A supported, contradicted, inconclusive, or
insufficient-evidence proposal may create the one allowed Discovery only after
authorization and atomic admission.

## Boundaries and limitations

`expand_plan` does not directly create a Hypothesis. The binding occurs only
after exact execution-contract approval. Planner nodes still open SQLModel
sessions and know repository/record types; this is documented non-blocking
application-boundary debt. The supported Planner commit path rejects generic
creation of `AnalysisFrame`, `Evidence`, and `Discovery`.

The current existing-Hypothesis branch proposes a generic Hypothesis-state
change that execution-bundle validation rejects because the transition service
owns that lifecycle. It fails closed but is not a supported reuse path.
