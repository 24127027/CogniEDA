# Operation approval workflows

This workflow follows two currently supported Planner coordination paths:
ordinary Task management and a new execution contract. In both, a model may
propose, but durable mutation requires typed state, an exact user decision,
repository-current revalidation, and a canonical transaction owner.

> **Implementation status:** Configured request understanding, Task-operation
> proposal approval, durable resume, and the fresh execution-contract admission
> path are **Implemented** or **Partially implemented** as identified below.
> Answer, research-direction suggestion, result review, conflict review,
> complete pause/resume, and project closure are **Unsupported** or **Design
> target**.

The common shape is:

```text
raw user request
-> intent classification
-> bounded context and read access
-> typed proposal
-> durable PlannerOperation or execution approval
-> exact user decision
-> repository-current revalidation
-> canonical transaction owner
-> commit or fail closed
```

## Example 1: approve an ordinary Task proposal

Suppose the user asks:

> Break the churn investigation into an analytical Task that tests whether
> support delay is associated with renewal within the accepted customer
> profile.

### 1. Understand and route

`understand_request` converts raw text into a configured structured intent.
`route_intent` selects Task planning rather than treating the text itself as a
mutation. Unsupported or incomplete intents must not be inferred to work merely
because a node name exists.

### 2. Read bounded planning context

The Planner reads the named SessionFrame, active Objective and `DataProfile`,
and relevant parent Task state. Retrieval applies lifecycle policy, structural
relationships, pins, exclusions, profile compatibility, lexical ranking, and a
visible result budget.

These reads support planning only. They do not change durable state and do not
turn a retrieved Discovery into a scientific premise. Assumptions may guide
planning but remain excluded from protected conclusion context.

### 3. Produce typed operations

Task-management nodes produce `PlannerOperation` values such as a Task create
or state-change proposal. Each operation has its own identity, Planner session,
typed payload, producing node, and approval state.

The proposal may include a motivating Discovery identity. That identity is not
trusted merely because retrieval returned it; commit repeats the current
lifecycle, nonempty-scope, and exact-profile checks.

### 4. Persist before asking

`request_user_input` persists the operation set before exposing its approval
interaction. It computes a fingerprint over the exact ordered identities,
types, payloads, and sessions.

If the process stops, the caller can resume by exact operation IDs and session.
Unknown, duplicate, wrong-session, rejected, committed, or otherwise nonpending
operations fail closed.

### 5. Bind the exact decision

The user can approve, cancel, revise, or clarify. Approval requires the proposal
fingerprint and the exact ordered selection. A different proposal ID, subset,
order, or session is not equivalent consent.

Approval sets the durable operation records to `APPROVED`. Other actions set
them to `REJECTED`; they do not leave a reusable authorization.

### 6. Delegate commit

The `commit` node invokes `commit_planner_operations`. The application
transaction owner:

- loads only the session-bound committable set;
- validates operation payload and lifecycle rules;
- revalidates a selected motivating Discovery against repository-current
  lifecycle, scope, and active profile;
- applies the complete ordinary write set;
- marks operations committed; and
- commits once or rolls back.

The Planner node coordinates that owner. It is not the scientific transaction
owner and does not author `Evidence` or `Discovery`.

### 7. Result

If all checks still hold, the Task and operation metadata commit atomically. If
the profile, Discovery, approval, session, payload, or lifecycle changed, the
operation fails closed and no partial Task mutation becomes authoritative.

## Example 2: approve a fresh execution contract

Now suppose an active terminal analytical Task has an accepted active profile,
no children, one explicit analytical specification, and no existing
Hypothesis. The user asks to execute it.

### 1. Prepare the bounded contract

`select_task` and `prepare_execution` read the exact Task, children, profile,
and Hypothesis state. Preparation verifies the current execution prerequisites
and constructs:

- a proposed Hypothesis contract;
- variables and scope;
- validation method and parameters;
- decision rule and evidence expectation;
- executor identity; and
- a contract fingerprint bound to the Task and profile revisions.

Preparation is not admission. It is a proposal subject to exact user approval
and revalidation.

### 2. Persist the execution approval

`request_user_input` creates or reuses a pending `ExecutionApproval` for the
Planner session, Task, profile, execution reference, prepared payload, and
contract fingerprint. The approval is durable independently of the in-memory
graph checkpoint.

### 3. Bind the user's action

`process_decision` requires the exact approval identity and fingerprint. A
nonapprove action cancels the durable record. Approval changes a pending record
to `APPROVED`; a consumed or otherwise nonpending approval cannot authorize
another attempt.

### 4. Revalidate at admission

`commit_execution_contract` re-reads the durable approval, Task, and profile.
It requires:

- the same Planner session;
- `APPROVED` approval state;
- the exact contract fingerprint, Task, and profile;
- an active terminal analytical Task;
- an accepted active profile; and
- unchanged execution specification inputs.

Repository and application guards repeat the no-child, one-Hypothesis, profile,
and lifecycle checks.

### 5. Delegate the atomic write set

For the fresh path, the Planner coordinates a create-Hypothesis operation and
the execution run/outbox operations produced by
`build_execution_admission_operations`. It marks the approval consumed in the
same session and invokes `commit_planner_operations`.

Execution admission is routed through `ExecutionAttemptTransitionService`,
which owns the Hypothesis-testing transition and run/outbox admission. The
complete write set commits once or rolls back. Dispatch happens only after
durable admission.

### 6. Result and recovery limit

On success, exactly one Hypothesis and one admitted execution attempt exist for
the bounded contract, and the approval cannot be replayed as a second attempt.
On stale input or transaction failure, admission fails closed.

This path is **Partially implemented** as a product workflow. An admission
failure can leave an approval durably `APPROVED` without a supported decision
retry, and an existing-Hypothesis reuse branch is rejected by the correct
transition-owner guard. Those failures do not create partial scientific state,
but their recovery experience is incomplete.

## What these examples do not prove

They do not establish:

- a complete answer path;
- automatic research-direction suggestions;
- user-facing result or conflict review;
- durable LangGraph process checkpointing;
- project closure or parent-level final synthesis;
- a production CLI, API, worker, or daemon; or
- a concrete production Data Explorer.

Graph topology, typed schemas, and tests can expose seams for those features
without making the complete behavior **Implemented**.

## Authority summary

| Stage | Authority |
| --- | --- |
| raw text and model output | proposal input only |
| bounded Planner reads | planning context only |
| `PlannerOperation` or `ExecutionApproval` | durable pending workflow state |
| exact user decision | authorization for the exact proposal, not scientific truth |
| commit revalidation | repository-current eligibility and staleness check |
| `commit_planner_operations` | ordinary operation and execution-bundle transaction coordination |
| execution transition service | execution-attempt lifecycle owner |
| protected Analyst and governance | later scientific proposal and decision authority |
| scientific admission services | later exact materialization of Evidence and Discovery |

## Related canonical concepts

- [Planner operations and approvals](planner-and-approvals.md)
- [Retrieval strategy](../concepts/context/retrieval-strategy.md)
- [Discovery governance and admission](../concepts/scientific-lifecycle/discovery-governance-and-admission.md)
- [Execution to Discovery](../concepts/scientific-lifecycle/execution-to-discovery.md)
- [Persistence and transactions](persistence-and-transactions.md)

## Implementation orientation

Planner routing, proposal, approval, revalidation, and commit nodes are in
`src/agents/planner/nodes.py`, with graph topology in
`src/agents/planner/graph.py`. Durable operation commit is in
`src/application/orchestrator/planner_commit.py`; execution admission helpers
are in `src/application/execution/admission.py`; execution lifecycle ownership
is under `src/application/execution/`. Focused behavior is exercised in
`tests/agents/planner/`, `tests/application/orchestrator/`,
`tests/application/execution/`, and `tests/e2e/`.
