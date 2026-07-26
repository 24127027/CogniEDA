# Planner boundary and operation model

CogniEDA's Planner coordinates intent, bounded context, typed proposals, user
approval, and delegation. It does not own scientific truth.

> **Implementation status:** Ordinary Task-operation staging, durable approval,
> session-bound resume, and atomic operation commit are **Implemented**.
> Execution-contract preparation and admission coordination are **Partially
> implemented**. Direct Planner session construction, repository coupling, and
> approval-record updates are **Known deviation**. Answer, suggestion, review,
> pause, and project-closure product paths are **Unsupported** or **Design
> target** as identified below.

The current structural verdict is:

> `NON-BLOCKING DOCUMENTED DEBT`

No reachable Planner path reviewed for this boundary directly authors
`Evidence` or `Discovery`, bypasses protected evaluation or governance, or
commits a partial terminal scientific lifecycle. The Planner is nevertheless
too close to persistence for a mature service topology.

## What the Planner owns

The Planner currently owns workflow coordination:

- classify a request and route it to a known Planner path;
- read bounded durable state needed to propose work;
- construct typed `PlannerOperation` records rather than mutate ordinary
  research state inside proposal nodes;
- persist approval proposals before exposing them to a caller;
- bind a user decision to the exact proposal and Planner session;
- revalidate approved inputs before execution admission;
- invoke `commit_planner_operations` for ordinary approved operations; and
- delegate execution-attempt state changes to the execution transition service.

It may read `Task`, `Objective`, `DataProfile`, `Hypothesis`, `Discovery`, and
`SessionFrame` state to coordinate those responsibilities. A read does not
grant ownership of the object or its lifecycle.

## What the Planner must not own

The Planner must not:

- treat an LLM response as a durable mutation;
- create `Evidence` or `Discovery`;
- become the protected evaluator, governance authority, or scientific
  materializer;
- use `Assumption` as a conclusion premise;
- move a terminal analytical Task to `COMPLETED` or a Hypothesis to `EVALUATED`
  through the generic operation path;
- admit an execution without an active terminal analytical Task, an accepted
  active `DataProfile`, and an exact approved contract;
- commit only part of a scientific lifecycle transition; or
- let ranking, a pin, or user approval manufacture scientific admissibility.

`src/application/orchestrator/planner_commit.py` rejects generic
`CREATE_ANALYSIS_FRAME`, `CREATE_EVIDENCE`, and `CREATE_DISCOVERY` operations.
It also rejects protected terminal Task and Hypothesis transitions. Scientific
authority remains with the application services described in
[scientific authority](scientific-authority.md) and
[persistence and transaction ownership](persistence-and-transaction-ownership.md).

## PlannerOperation is pending workflow state

`PlannerOperation` is not a First-Class Object and not scientific knowledge.
It is a durable proposal envelope containing:

- a stable operation identity;
- the Planner session identity;
- a typed operation and payload;
- the node that produced it;
- an approval state; and
- commit or failure metadata.

The ordinary lifecycle is:

```text
typed proposal
-> durable pending PlannerOperation set
-> exact user decision
-> approved or rejected set
-> canonical commit
-> committed set or fail closed
```

The proposal fingerprint covers the ordered operation identities, types,
payloads, and session identities. Resume loads exact durable operation IDs,
requires one matching session and pending state, and rejects duplicates,
unknown IDs, stale decisions, and a different ordered selection. A successful
commit or rejection is not a reusable approval.

This staging costs extra records, serialization, replay rules, and evolving
operation schemas. It is retained because a proposed mutation must be
inspectable and approvable before it becomes durable research state.

## Approval and resume boundaries

### Ordinary Planner operations

`request_user_input` persists the pending operations before publishing the
interaction. `process_decision` requires the decision proposal fingerprint and
the exact ordered operation IDs. Approval records `APPROVED`; cancellation,
revision, or clarification records `REJECTED`. The `commit` node calls
`commit_planner_operations`, which re-reads and applies only committable
session-bound operations in one transaction.

The direct approval-state update inside the Planner is a **Known deviation**.
It changes workflow metadata, not scientific truth, but belongs behind an
application facade when product coordination or additional approval types make
the boundary more complex.

### Execution approval

Execution uses a separate durable `ExecutionApproval` because the approved
contract binds Task and profile revisions, accepted-profile state, variables,
scope, method, parameters, and decision rule. Resume reconstructs the prepared
contract from the durable payload and verifies the same Planner session.

The current decision step commits `APPROVED` before the later admission
transaction. Admission then revalidates the durable Task, profile, fingerprint,
and approval, marks the approval `CONSUMED`, stages the Hypothesis and
execution-attempt operations, and invokes `commit_planner_operations` in the
same database session. Failure closes the session without a partial admission.

This seam is **Partially implemented**. If admission fails after approval, the
durable record can remain `APPROVED`; resume accepts that state, but the current
decision node accepts approval only from `PENDING`. A complete product recovery
flow for that stranded approved contract is not implemented.

## Execution-contract coordination

The intended fresh-contract path is:

1. `prepare_execution` verifies an active terminal analytical Task with no
   children, an accepted active profile, and no already-finalized Hypothesis.
2. `request_user_input` creates or reuses the exact durable pending approval.
3. `process_decision` binds the user's action to that contract.
4. `commit_execution_contract` repeats Task, profile, and fingerprint checks.
5. `build_execution_admission_operations` creates the typed run/outbox pair.
6. `commit_planner_operations` applies the complete bundle.
7. `ExecutionAttemptTransitionService` owns run, Hypothesis-testing, and outbox
   admission state.

Hypothesis repository guards also enforce the terminal analytical Task,
accepted profile, no-child, and one-Hypothesis boundaries. The result is
defense in depth; preparation alone is not authority.

One current reuse branch constructs `CHANGE_HYPOTHESIS_STATE` for an existing
nonterminal Hypothesis. Execution-bundle validation correctly rejects that
operation because the transition service owns the lifecycle change. The branch
therefore fails closed but cannot complete its advertised reuse path. This is a
functional **Known deviation**, not an alternate writer.

## Persistence-access classification

The full row-level inventory remains checkout evidence in the local audit. The
reader-facing classification is:

| Class | Meaning | Current conclusion |
| --- | --- | --- |
| A | legitimate read-only application access | Task, profile, frame, objective, Hypothesis, approval, and Discovery reads are bounded coordination inputs |
| B | temporary composition access | Planner constructs sessions, repositories, proposal persistence, approval updates, reconciliation, and commit coordination directly |
| C | direct durable mutation bypass | none found on a reachable supported path |
| D | stale or dead path | stale decision-route labels and incomplete resume-routing seams exist |
| E | scaffold-only or unsupported path | answer, suggestion, review, pause, Assumption-management entry, and project-closure behavior remain incomplete |

Class B is accepted only while it preserves delegation and fail-closed
transactions. A future direct scientific writer would be Class C and a blocking
architecture defect, not acceptable Planner debt.

## Incomplete Planner paths

Graph reachability is not implementation proof:

- `check_answerability` and `answer_question` do not produce a supported answer;
- `propose_questions` does not construct a complete research-direction
  proposal;
- result and conflict review retain explicit TODO behavior;
- `pause` supplies only the graph interrupt boundary, not durable product
  coordination;
- natural-language Assumption management is not a complete public workflow;
- recognized profile, cleaning, registration, and closure commands can route to
  an invalid-request outcome; and
- project closure and final user-facing synthesis are not implemented.

These paths must not be presented as **Implemented** merely because their node
names are registered or reachable.

## Why facade extraction is deferred

Direct repository reads and local session construction keep the in-process
implementation small and make transaction boundaries visible. They also create
tight repository coupling, database-heavy node tests, repeated composition,
and future extraction cost.

An application facade is a **Deferred** redesign, not a prerequisite for the
current documentation stage. Extract it when a direct write bypass appears, a
second Planner implementation is introduced, multiple services or databases
need the same orchestration, approval types multiply, nodes must be reused, or
unit isolation becomes materially difficult.

Any facade must preserve typed proposals, exact session-bound approval,
commit-time revalidation, canonical scientific transaction owners, atomic
effects, and fail-closed behavior. It must not merely hide a bypass behind a
different class.

## Related canonical concepts

- [From user request to approved operation](from-user-request-to-approved-operation.md)
- [Retrieval strategy and scaling](retrieval-strategy-and-scaling.md)
- [SessionFrame scaling and resume boundary](session-frame-scaling-and-resume-boundary.md)
- [Governance and Discovery admission](governance-and-discovery-admission.md)
- [Runtime and composition boundary](runtime-and-composition-boundary.md)

## Implementation orientation

Planner topology and nodes are in `src/agents/planner/graph.py` and
`src/agents/planner/nodes.py`. Operation schemas are in
`src/agents/planner/types.py`. Durable operation application is in
`src/application/orchestrator/planner_commit.py`. Execution admission is in
`src/application/execution/admission.py`, with lifecycle ownership under
`src/application/execution/`. Focused behavior is exercised in
`tests/agents/planner/`, `tests/application/orchestrator/`,
`tests/application/execution/`, and `tests/architecture/`.
