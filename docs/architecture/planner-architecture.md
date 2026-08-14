# Planner architecture

The Planner is CogniEDA's control plane and sole human-facing agent boundary.
It coordinates research work without acquiring scientific operationalization,
execution, governance, or durable-admission authority.

This page defines the target Planner architecture. The bounded current library
implements only the transitional behavior described below; canonical planning remains a
target.

CogniEDA separates a deterministic governed research-state kernel from an
agentic cognitive plane. The kernel owns authority, persistence, provenance,
eligibility, validity constraints, and lifecycle transitions. Agents own
reasoning, operationalization within their role, allowed tool selection, and
iterative work decisions. Governance defines what is allowed; it does not
precompile the reasoning workflow.

## Planner responsibility

The Planner owns:

- coordination of Objective-scoped work;
- bounded planning consultations;
- complete `Plan` proposals;
- Task DAG construction and presentation;
- reasoning over governed specialist and tool interactions;
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

The Human approves the exact Plan candidate presented at this boundary.
Approval policy modes and their runtime behavior are **Deferred**; they are not
part of the implemented validator or repository foundation.

## Grounded planning loop

Planning may require bounded consultation before a credible plan can be
proposed:

```text
human intent
  -> Planner frames planning need
  -> optional Data Explorer or Graph Miner consultation
  -> typed consultation result
  -> Planner refines scope and Task DAG
  -> Plan proposal
```

Data Explorer may report dataset shape, availability, diagnostics, or blockers.
Graph Miner may report existing object references, paths, gaps,
contradictions, validity, or dependencies. Consultation output informs
planning; it is not Evidence and does not become a durable Task unless an
independently governed deliverable is needed.

The Planner must use only planning-eligible context. An `Assumption` may guide
this loop, but it remains a planning constraint and cannot be smuggled into
protected scientific evaluation.

## Plan and Task DAG

A `Plan` is a non-FCO immutable aggregate containing the exact Objective under
which one complete research plan was constructed, the exact admitted Human
Assumptions that materially influenced planning, and one Task DAG. Its content
owns coordination concerns such as:

- exactly one immutable `PlanTaskBinding` for each member Task;
- explicit dependency edges between member Tasks;
- binding-owned non-negative `order_rank` and finite `LOW`, `NORMAL`, or `HIGH`
  priority;
- a deterministic plan-content fingerprint.

The fingerprint covers the version-bound Objective and Assumption
representations, Task membership, rank, priority, and dependency edges. It
excludes Task runtime status and all execution-routing, approval, activation,
timestamp, conversation, model, and DataProfile-selection state. Assumptions
remain planning basis only and cannot support protected evaluation.

Membership is derived from the binding Task identities; a parallel `task_ids`
collection is not a second source of truth. Order rank and priority are
coordination semantics. Changing either one
changes Plan content and its fingerprint without, by itself, creating a
successor Task.

Plan and `PlanTaskBinding` contain no exact DataProfile identity,
dataset reference, column binding, row filter, cohort, population, or variable
binding. Planner describes intended data scope only in the Task instruction.
Each responsible specialist or controller receives the complete authoritative
DataProfile context available for the work and selects the concrete applicable
profile and scope within its own authority. The exact DataProfile actually used
is recorded later in execution or scientific provenance, not in the
Plan fingerprint.

Proposal, approval, activation, plan-execution completion, interruption, and
replanning are workflow-lifecycle concerns around that immutable content. They
are not configurable condition or trigger policy authored inside a
`Plan`. An actual cause that later requires reconsideration is a
workflow fact associated with the affected Plan; the finite typed cause
taxonomy and successor lifecycle are deferred to their owning workflow
milestone.

Scientific stopping conditions remain part of Hypothesis Analyst-owned
`InvestigationProtocol`. Bounded execution stopping conditions remain part of
the applicable role-native work order, including `DataWorkOrder`.

A `Task` is the durable semantic work unit. Its canonical kinds are `DATA`,
`SCIENTIFIC`, and `GRAPH`; these are semantic and epistemic classes, not
provider routes. Execution strategy, assignment, dependencies, parentage,
order, priority, Plan identity, approval, and activation are not part
of Task identity. Changing binding coordination does not change what the Task
means; changing semantic work requires a successor Task.

Not every user prompt becomes a Task. The Planner may answer a general/direct
question with no project work, or synthesize an answer from retained
authoritative project state, without creating executable work.

The Planner constructs a DAG rather than a bag of instructions. It must expose
dependencies, blocked prerequisites, and terminal leaves before activation.
The dependency DAG determines eligibility.
`order_rank` is only a scheduling preference among otherwise compatible work,
permits ties for concurrent or independent Tasks, and never overrides a
dependency. Equal-rank bindings use canonical Task-ID ordering only as a
deterministic serialization tie-breaker; that tie-breaker creates no dependency
or execution-order meaning. Priority is coordination metadata only, defaults to
`NORMAL`, and never overrides dependencies, validity, authority, or Task
meaning. Proposed Tasks cannot execute.

## Proposal, approval, and activation

The planning sequence is:

1. The Planner constructs transient canonical Objective, Task, and
   `Plan` objects, including the complete Task DAG. Domain construction
   performs structural validation but creates no durable authority.
2. The Planner presents those exact pending canonical objects to the Human.
3. The Human approves, rejects, holds, or requests revision.
4. Only after approval, application authority performs commit-boundary
   validation and atomically persists, adopts, and activates the exact approved
   objects.

There is no mandatory separate application preflight or admission stage before
Human review. The implemented `PlanValidator` is a side-effect-free
boundary for requiring exact persisted Objective and Assumption content,
resolving exact Task membership, and verifying a canonical candidate without
side effects; approval and the commit transaction are
**Deferred**.

Approval is not activation. The plan visible to a user must be the same plan
fingerprint or exact version that application authority activates. A changed
proposal requires a new approval decision unless explicit policy permits the
specific change.

## Governed execution and replanning

Application authority selects an eligible Task from the active approved DAG
and exposes only the role-level specialist tools allowed for the execution
context. The Planner receives that Task as its current goal and reasons about
whether to call zero, one, or multiple allowed tools, whether more work is
needed, and when to stop or report a blocker. The application owns Task
lifecycle transitions and validates identity, provenance, and authority at
every boundary.

Plan does not contain capability, role, provider, specialist, worker,
process, model, tool, or routing-hint identity. Execution internals may retain
capability-based provider resolution behind a specialist tool boundary, but
the Planner does not select an internal `Capability` while authoring the plan.
It does not choose a legacy executor or reinterpret the Task.

Capability absence, infeasibility, a blocked dependency, new limitations, a
correction request, additional Evidence needs, validity change, or a human
change in intent may later be recorded as actual workflow facts requiring
reconsideration. The replanning lifecycle creates a successor Plan or returns
to the grounded planning loop; it does not mutate the historical Plan. A finite
typed cause taxonomy and runtime response are deferred.

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
record merely because it is user-facing. This response synthesis is Planner
behavior, not a Task kind or executor path.

## Recovery and resume

Planner recovery is state reconstruction, not transcript replay. On restart,
the Planner must be able to recover:

- the active Objective and Plan;
- exact pending proposal and approval identities;
- Task lifecycle and dependency state;
- admitted execution and normalized outcome references;
- current blockers and permitted next actions;
- the applicable SessionFrame and validity warnings.

Duplicate decisions and replayed messages must be idempotent. A resumed
approval must apply only to the exact objects originally presented. Lost or
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

The immutable `Plan`, `PlanTaskBinding`, and `PlanDependency` V1 domain
contracts and side-effect-free application validation are **Implemented** with
exact persisted Objective and Assumption content checks, persisted Task
resolution, structural canonicalization, DAG guards, and deterministic
fingerprinting. Append-only exact snapshot persistence and fail-closed
identity/fingerprint reconstruction are **Verified on SQLite** as
infrastructure for the later approval boundary. Validation does not persist a
candidate, and no application caller currently persists a Plan.
Planner does not author or consume Plan, and approval, exact
post-approval revalidation, activation, active Plan selection, and replanning
runtime are **Deferred**. Active Task exposes all three canonical kinds, but
only bounded `DATA` work is executable. Full Task DAG runtime behavior,
GeneratedView coordination, durable SessionFrame composition, and the
end-to-end recovery model remain **Deferred** target design. The
[MVP-v2 definition](mvp-runtime-subset.md) explains the minimum complete
product and research capability.

Continue with [Executor and dispatch](executor-and-dispatch.md) or follow the
complete sequence in [End-to-end flow](end-to-end-flow.md).
