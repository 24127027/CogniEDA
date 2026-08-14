# Planner architecture

The Planner is CogniEDA's control plane and sole human-facing agent boundary.
It coordinates research work without acquiring scientific operationalization,
execution, governance, or durable-admission authority.

This page defines the target Planner architecture and identifies the bounded
two-phase lifecycle now implemented. The complete scientific workflow and
durable recovery model remain targets.

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

The Human approves the exact Plan and separate Task bundle presented at this
boundary. The current Application accepts exact UUID-bound approve, reject, or
revise decisions; broader policy modes remain **Deferred**.

## Grounded planning loop

The current `plan_or_answer` phase reasons from the Human request and complete
readable `PlannerContext`:

```text
human intent + PlannerContext
  -> answer from admitted Evidence or Discovery when sufficient
  -> propose an exact Objective, admitted Assumption basis, Tasks, and DAG
  -> continue the current approved Plan when it remains appropriate
  -> request Human clarification when direction is underdetermined
```

Executor tools are structurally omitted from `plan_or_answer`. Internal
candidate directions remain model reasoning rather than new domain objects or
Assumptions. If new work changes Plan semantics, the new immutable Plan returns
to Human review; continuing an unchanged active Plan does not.

The Planner must use only planning-eligible context. An `Assumption` may guide
this loop, but it remains a planning constraint and cannot be smuggled into
protected scientific evaluation.

## Plan and Task DAG

A `Plan` is a non-FCO immutable snapshot of one complete plan for one
Objective. Its content owns plan-version concerns such as:

- exactly one immutable `PlanTaskBinding` for each member Task;
- explicit dependency edges between member Tasks;
- binding-owned non-negative `order_rank` and finite `LOW`, `NORMAL`, or `HIGH`
  priority;
- a deterministic plan-content fingerprint.

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
workflow fact associated with the affected revision; the finite typed cause
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
Human review. The implemented `PlanValidator` and `PlanAdmissionService`
resolve exact persisted references and commit the approved Objective, Tasks,
Plan, and active selection on SQLite. Every Plan Assumption must already be
admitted with the same identity and content; Plan approval never admits one.

Approval is not activation. The plan visible to a user must be the same plan
fingerprint or exact version that application authority activates. A changed
proposal requires a new approval decision unless explicit policy permits the
specific change.

## Governed execution and replanning

Application authority exposes only the role-level specialist tools allowed for
the current active approved DAG. `execute` may call zero, one, or multiple
semantic tools, but must make authoritative progress or expose a controlled
blocker. It never answers or produces a `PlannerResult`; its fixed successor is
`plan_or_answer`, which sees authoritative Task and Evidence deltas and decides
whether to answer, continue, ask the Human, or propose a new Plan. Application
owns Task lifecycle transitions and validates identity, provenance, and
authority at every tool call.

Plan does not contain capability, role, provider, specialist, worker,
process, model, tool, or routing-hint identity. Execution internals may retain
capability-based provider resolution behind a specialist tool boundary, but
the Planner does not select an internal `Capability` while authoring the plan.
It does not choose a legacy executor or reinterpret the Task.

Capability absence, infeasibility, a blocked dependency, new limitations, a
correction request, additional Evidence needs, validity change, or a human
change in intent may later be recorded as actual workflow facts requiring
reconsideration. The replanning lifecycle creates a successor Plan or
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

**Partially implemented.** Application exact-materializes the current
SessionFrame, active approved Plan, and non-authoritative ConversationHistory
into one immutable `PlannerContext`; Planner never receives or returns
SessionFrame. Candidate Plan content owns the exact Objective and a subset of
exact already-admitted Assumptions. Tasks remain separate FCO values in the
Human-review bundle.

Planner directly owns one PydanticAI `Agent` created through the inward-facing
`AgentFactoryPort`. `PlannerDeps` contains `ExecutorDispatcherPort` and an
Application-owned execution-session service. The model sees only semantic tool
arguments; `Capability`, provider, registry, dispatcher, and physical route do
not enter Planner-visible schemas.

Exactly two LangGraph cognitive nodes are active: `plan_or_answer` and
`execute`. The graph starts at `plan_or_answer`; final answers and clarification
requests return to the Human, candidate Plans interrupt for exact Human review,
and `continue_execution=True` enters `execute` without another approval.
`execute` always returns to `plan_or_answer` and never produces a
`PlannerResult`. One optional-field `PlannerResult` is used only for
`plan_or_answer`; `PlannerOutput(result, messages, error)` is the
Application-facing lifecycle snapshot.

Rejection or revision adds an explicit native Human message and returns to
`plan_or_answer` without persistence. Approval atomically validates, persists,
adopts, and activates the exact bundle before resume, and the same message
sequence records that Human decision without treating message text as
authority.

The built-in Planner role and authority instruction remains source-owned.
Optional project guidance is loaded only from `.cognieda/planner.md` and is
inserted between that built-in baseline and the current operation instruction.
The instruction utility resolves the direct caller module's sibling
`instruction/` directory through the source layout convention. Repository-root
`AGENTS.md` content is not a Planner runtime instruction.

Current bounded Planner behavior may answer from admitted state, propose a
complete Plan/Task bundle, request clarification, or continue an existing
approved Plan. Assumption assessment and admission commands are **Deferred**;
model-generated possibilities never create Assumptions. Application owns
administrative and Plan-review commands. Planner may propose Tasks but cannot
make them authoritative or independently create Evidence or Discovery.

`PlannerOutput.messages` means every native PydanticAI message generated by the
current lifecycle across `plan_or_answer` and `execute`, including tool-call,
tool-return, and explicit Human approval/rejection/revision messages.
Application appends that complete set as one `ConversationTurn` only after
completion; an interrupt does not create a partial turn. History remains
non-authoritative and excluded from empirical support. Neither conversation nor
the current SessionFrame is durably restored after restart.

The immutable `Plan`, `PlanTaskBinding`, and `PlanDependency` V1 domain
contracts and side-effect-free application validation are **Implemented** with
exact persisted Objective, Assumption, and Task checks, structural
canonicalization, DAG guards, and deterministic routing-free fingerprinting.
Append-only snapshot persistence and active-plan selection are **Verified on
SQLite**. Application calls this boundary only after exact Human approval and
commits the approved Objective, Tasks, Plan, and active pointer atomically;
referenced Assumptions must already exist exactly. Active Task exposes all
three canonical kinds, while only approved eligible `DATA` Tasks have a real
semantic tool. At every call, `run_data_work` re-resolves the persisted active
Plan and current DAG eligibility, invokes Data Explorer through model-hidden
dispatcher plumbing, completes the Task and admits Evidence atomically on
SQLite, and returns that admitted Evidence. The successor `PlannerContext` is
updated directly; no mandatory full context reload occurs. Hypothesis Analyst
and Graph Miner tools remain absent because those runtimes are not executable.
Full scientific and graph Task DAG behavior,
GeneratedView coordination, durable SessionFrame composition, and the
end-to-end recovery model remain **Deferred** target design. The
[MVP-v2 definition](mvp-runtime-subset.md) explains the minimum complete
product and research capability.

Continue with [Executor and dispatch](executor-and-dispatch.md) or follow the
complete sequence in [End-to-end flow](end-to-end-flow.md).
