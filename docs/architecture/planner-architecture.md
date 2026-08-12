# Planner architecture

The Planner is CogniEDA's control plane and sole human-facing agent boundary.
It coordinates research work without acquiring scientific operationalization,
execution, governance, or durable-admission authority.

This page defines the target Planner architecture. The bounded current library
implements only the transitional behavior described below; canonical planning remains a
target.

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

A `PlanRevision` is a non-FCO immutable snapshot of one complete plan for one
Objective. Its content owns plan-version concerns such as:

- exactly one immutable `PlanTaskBinding` for each member Task;
- explicit dependency edges between member Tasks;
- binding-owned required capability;
- binding-owned non-negative `order_rank` and finite `LOW`, `NORMAL`, or `HIGH`
  priority;
- a deterministic plan-content fingerprint.

Membership is derived from the binding Task identities; a parallel `task_ids`
collection is not a second source of truth. Required capability, order rank,
and priority are coordination semantics. Changing any of them
changes PlanRevision content and its fingerprint without, by itself, creating a
successor Task.

PlanRevision and `PlanTaskBinding` contain no exact DataProfile identity,
dataset reference, column binding, row filter, cohort, population, or variable
binding. Planner describes intended data scope only in the Task instruction.
Each responsible specialist or controller receives the complete authoritative
DataProfile context available for the work and selects the concrete applicable
profile and scope within its own authority. The exact DataProfile actually used
is recorded later in execution or scientific provenance, not in the
PlanRevision fingerprint.

Proposal, approval, activation, plan-execution completion, interruption, and
replanning are workflow-lifecycle concerns around that immutable content. They
are not configurable condition or trigger policy authored inside a
`PlanRevision`. An actual cause that later requires reconsideration is a
workflow fact associated with the affected revision; the finite typed cause
taxonomy and successor lifecycle are deferred to their owning workflow
milestone.

Scientific stopping conditions remain part of Hypothesis Analyst-owned
`InvestigationProtocol`. Bounded execution stopping conditions remain part of
the applicable role-native work order, including `DataWorkOrder`.

A `Task` is the durable semantic work unit. Its canonical kinds are `DATA`,
`SCIENTIFIC`, `GRAPH`, and `SYNTHESIS`. Required capability, assignment,
dependencies, parentage, order, priority, PlanRevision identity, approval, and
activation are not part of Task identity. Changing binding coordination does
not change what the Task means; changing semantic work requires a successor
Task.

The Planner constructs a DAG rather than a bag of instructions. It must expose
dependencies, blocked prerequisites, terminal leaves, and capability
requirements before activation. The dependency DAG determines eligibility.
`order_rank` is only a scheduling preference among otherwise compatible work,
permits ties for concurrent or independent Tasks, and never overrides a
dependency. Equal-rank bindings use canonical Task-ID ordering only as a
deterministic serialization tie-breaker; that tie-breaker creates no dependency
or execution-order meaning. Priority is coordination metadata only, defaults to
`NORMAL`, and never overrides dependencies, validity, authority, or Task
meaning. Proposed Tasks cannot execute.

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

| Task kind | Binding capability |
| --- | --- |
| `DATA` | exactly one of `DATA_ANALYSIS`, `DATA_PROFILING`, or `DATA_TRANSFORMATION` |
| `SCIENTIFIC` | `HYPOTHESIS_TESTING` |
| `GRAPH` | `GRAPH_MINING` |
| `SYNTHESIS` | `None`; no executable capability or provider path exists in V1 |

The Planner declares the required capability in the `PlanTaskBinding`;
`ExecutorRegistry` resolves an eligible runtime provider for dispatcher-backed
work. `Capability` is owned by the execution/dispatch layer. PlanRevision does
not duplicate role, provider, worker, process, or model identity. Kind and
capability compatibility is validated structurally. Planner coordinates and
may invoke the dispatcher, but it does not perform executor-native Task work.
If the capability is absent, the Planner receives a typed unavailable or
blocked outcome. It does not choose a legacy executor, reinterpret the Task,
infer a capability or provider, or route by semantic guess.

Capability absence, infeasibility, a blocked dependency, new limitations, a
correction request, additional Evidence needs, validity change, or a human
change in intent may later be recorded as actual workflow facts requiring
reconsideration. The replanning lifecycle creates a successor PlanRevision or
returns to the grounded planning loop; it does not mutate the historical
revision. A finite typed cause taxonomy and runtime response are deferred.

## SessionFrame and GeneratedView coordination

The Planner coordinates `SessionFrame` membership and the active Objective and
DataProfile selectors. Application authority validates and persists those
structured references. It resolves every retained SessionFrame member into the
Planner input context and may add authorized supplemental context. It may not
filter, rank away, or truncate retained membership. Type, validity, lifecycle,
lineage, scope, and authority constrain how Planner may use a visible object;
SessionFrame membership never grants inclusion in a protected
`EvaluationBundle`.

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

**Partially implemented.** Application now exact-materializes the current
SessionFrame into an immutable `PlanningContext`, calls Planner without passing
the frame, and applies explicit `created_objective`, `created_assumption`, and
terminal `created_task` results to its own successor frame. Planner graph state
contains per-run control and typed result fields only; Planner neither mutates
nor returns SessionFrame.

Current bounded Planner behavior can understand a
finite set of requests, establish or refine an Objective, retain planning-only
Assumptions, create and track bounded data Tasks, route work through the
dispatcher, consume identity-checked outcomes, and draft empirical answers
from admitted Evidence while excluding Assumptions. Planner does not admit
Evidence.

The current in-process runtime also preserves native model-message history
across Planner runs so a follow-up can be understood in conversational context.
That history remains separate from the materialized research state and is
excluded from empirical answer support. Neither conversation nor the current
SessionFrame is durably restored after restart.

The immutable `PlanRevision`, `PlanTaskBinding`, and `PlanDependency` V1 domain
contracts, exact SQLite persistence, and application-owned proposal admission
are **Implemented** with authoritative Objective and Task validation,
structural canonicalization, DAG guards, deterministic fingerprinting, atomic
snapshot writes, and fail-closed replay/collision handling. Planner does not
author or consume them, and no approval, activation, active-plan selection, or
replanning runtime exists. Active Task exposes all
four canonical kinds, but only bounded `DATA` work is executable. Full Task DAG
runtime behavior, GeneratedView coordination, durable SessionFrame composition,
and the end-to-end recovery model remain **Deferred** target design. The
[MVP-v2 definition](mvp-runtime-subset.md) explains the minimum complete
product and research capability.

Continue with [Executor and dispatch](executor-and-dispatch.md) or follow the
complete sequence in [End-to-end flow](end-to-end-flow.md).
