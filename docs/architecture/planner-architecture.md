# Planner architecture

The Planner is CogniEDA's control plane and sole human-facing agent boundary.
It coordinates research work without acquiring scientific operationalization,
execution, governance, or durable-admission authority.

This page defines the target Planner architecture. Current main implements
only part of this design.

## Planner responsibility

The Planner owns:

- coordination of Objective-scoped work;
- bounded planning consultations;
- complete `PlanRevision` proposals;
- Task DAG construction and presentation;
- routing by required capability;
- approval coordination;
- replanning and successor-plan proposals;
- `SessionFrame` coordination;
- `GeneratedView` coordination;
- restart and resume orchestration;
- high-level synthesis of normalized work outcomes.

The Planner proposes changes. Application authority validates and admits them.
The Planner never writes semantic graph, workflow, scientific, or provenance
state directly.

## Human interaction boundary

All user interaction passes through:

```text
Human <-> Planner
```

The Planner translates human intent into bounded proposals, explains approval
choices, presents limitations and blockers, and asks for correction or
clarification when needed. Specialists return typed results to application
coordination; they do not send messages or approval requests to the human.

Approval uses `ALWAYS_ASK`, `POLICY_GUARDED`, or `ALWAYS_ACCEPT` at this boundary
only. The default is policy-guarded, and an initial plan requires approval
unless explicit policy authorizes activation without an interactive decision.

## Grounded planning loop

Planning may require bounded consultation before a credible plan can be
proposed:

```text
human intent
  -> Planner frames planning need
  -> optional Data Explorer or Graph Miner consultation
  -> typed consultation result
  -> Planner refines scope and Task DAG
  -> PlanRevision proposal
```

Data Explorer may report dataset shape, availability, diagnostics, or blockers.
Graph Miner may report existing object references, paths, gaps,
contradictions, validity, or dependencies. Consultation output informs
planning; it is not Evidence and does not become a durable Task unless an
independently governed deliverable is needed.

The Planner must use only planning-eligible context. An `Assumption` may guide
this loop, but it remains a planning constraint and cannot be smuggled into
protected scientific evaluation.

## PlanRevision and Task DAG

A `PlanRevision` is a non-FCO version of a complete proposed or approved plan.
It owns plan-version concerns such as:

- Task membership and dependency edges;
- required capability for each Task;
- executor assignment in `PlanTaskBinding` or equivalent plan-version state;
- applicable DataProfile references;
- ordering, priority, presentation, and scheduling metadata;
- stopping conditions and replan triggers;
- approval state and plan fingerprint.

A `Task` is the durable semantic work unit. Its canonical kinds are `DATA`,
`SCIENTIFIC`, `GRAPH`, and `SYNTHESIS`. Assignment is not part of Task identity.
Changing an executor does not change what the Task means; changing semantic
work requires a successor Task.

The Planner constructs a DAG rather than a bag of instructions. It must expose
dependencies, blocked prerequisites, terminal leaves, and capability
requirements before activation. Proposed Tasks cannot execute.

## Proposal, approval, and activation

The planning sequence is:

1. The Planner drafts a complete `PlanRevision` proposal and its Task DAG.
2. Application authority validates the proposal contract without activating
   it.
3. The Planner presents the proposal through the configured approval mode.
4. Human or policy authority approves, rejects, holds, or requests revision.
5. Application authority verifies the exact approved proposal and atomically
   activates the PlanRevision and eligible Task state.

Approval is not activation. The plan visible to a user must be the same plan
fingerprint or exact version that application authority activates. A changed
proposal requires a new approval decision unless explicit policy permits the
specific change.

## Routing and replanning

| Task kind | Required role or coordination path |
| --- | --- |
| `DATA` | Data Explorer through a direct `DataWorkOrder` |
| `SCIENTIFIC` | Hypothesis Analyst controls investigation and requests observations from Data Explorer |
| `GRAPH` | Graph Miner through a `GraphInquiryRequest` |
| `SYNTHESIS` | Planner coordinates a GeneratedView from eligible normalized outcomes and admitted state |

The Planner declares the required capability; the dispatcher resolves an
eligible executor from the capability registry. If the capability is absent,
the Planner receives a typed unavailable or blocked outcome. It does not choose
a legacy executor, reinterpret the Task, or route by semantic guess.

Replanning may be triggered by capability absence, infeasibility, a blocked
dependency, new limitations, a correction request, additional Evidence needs,
validity change, or a human change in intent. Replanning creates a successor
PlanRevision or returns to the grounded planning loop. It does not edit an
approved plan in place.

## SessionFrame and GeneratedView coordination

The Planner coordinates a `SessionFrame` as the governed active context for a
specific purpose, Objective, and scope. It requests inclusion and exclusion of
eligible state; application authority validates and persists the frame.
SessionFrame construction must respect context type safety, validity, and
Objective boundaries.

The Planner may also coordinate a `GeneratedView` for an answer, table, report,
or synthesis. A view references its sources and carries limitations and
validity warnings. It never becomes Evidence, Discovery, or an authority
record merely because it is user-facing.

## Recovery and resume

Planner recovery is state reconstruction, not transcript replay. On restart,
the Planner must be able to recover:

- the active Objective and PlanRevision;
- exact pending proposal and approval identities;
- Task lifecycle and dependency state;
- admitted execution and normalized outcome references;
- current blockers and permitted next actions;
- the applicable SessionFrame and validity warnings.

Duplicate decisions and replayed messages must be idempotent. A resumed
approval must apply only to the proposal version originally presented. Lost or
ambiguous identity fails closed and returns a typed recovery blocker.

## Scientific non-authority

The Planner must not define or revise:

- a Hypothesis statement;
- scientific method or statistical test;
- method parameters;
- decision rule;
- random seed;
- variable bindings;
- `InvestigationPlan`;
- `InvestigationProtocol` or protocol revision;
- Evidence obligations;
- protected final scientific evaluation;
- `DiscoveryProposal` scientific content.

The Planner may route a correction request or report a scientific blocker. The
Hypothesis Analyst or appropriate scientific authority must author any revised
scientific proposal.

## Implementation status

**Partially implemented.** Current main implements typed request
classification, bounded Task proposal and decomposition paths, durable
PlannerOperation approval records, decision resume checks, and atomic commit
for a bounded set of Planner operations. 

Recent MVP progress (2026-08-08):
- Planner now accepts `PlannerDeps` dependency injection (terminal printer, and will include executor dispatcher).
- Tool calling is validated: Planner can successfully invoke built-in tools via pydantic_ai tool registration.
- Built-in tools are registered through `AvailableBuiltinTools` enum and passed to `PlannerModel`.
- Dependency protocols enable tools to access shared services (`HasExecutorDispatcher`, `HasTerminalPrinter`).

Several graph nodes, including answer, suggestion, Task selection, execution preparation with full executor dispatch, and execution review, remain stubs.

Canonical `PlanRevision` and plan-binding records are not implemented, and the
current runtime Task-kind vocabulary does not yet implement `DATA`,
`SCIENTIFIC`, `GRAPH`, and `SYNTHESIS`. The full approval-policy model,
capability-safe execution integration, SessionFrame and GeneratedView
coordination, and end-to-end recovery model remain target design. Executor dispatch integration through tools is the next priority.

Continue with [Executor and dispatch](executor-and-dispatch.md) or follow the
complete sequence in [End-to-end flow](end-to-end-flow.md).
