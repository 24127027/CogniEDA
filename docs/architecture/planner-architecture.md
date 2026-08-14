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
owns only:

- canonical Task IDs as the direct and only membership representation;
- explicit dependency edges between member Tasks;
- a deterministic plan-content fingerprint.

The fingerprint covers exact Objective and Assumption representations,
canonical Task IDs, and canonical dependency edges. It
excludes Task runtime status and all execution-routing, approval, activation,
timestamp, conversation, model, and DataProfile-selection state. Assumptions
remain planning basis only and cannot support protected evaluation.

`task_ids` is the single membership source of truth. Changing membership or a
dependency changes Plan content and its fingerprint without, by itself,
creating a successor Task.

Plan contains no exact DataProfile identity,
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
provider routes. Execution strategy, assignment, dependencies, parentage, Plan
identity, approval, and activation are not part of Task identity. Changing
Plan coordination does not change what the Task means; changing semantic work
requires a successor Task.

Not every user prompt becomes a Task. The Planner may answer a general/direct
question with no project work, or synthesize an answer from retained
authoritative project state, without creating executable work.

The Planner constructs a DAG rather than a bag of instructions. It must expose
dependencies, blocked prerequisites, and terminal leaves before activation.
The dependency DAG determines structural eligibility. Independent Tasks are
intentionally unordered; canonical Task-ID sorting makes serialization and
helper output deterministic but creates no dependency or execution-order
meaning. Execution order among eligible Tasks is a later Planner reasoning
concern. Proposed Tasks cannot execute.

## Proposal, approval, and activation

The planning sequence is:

1. The Planner constructs transient canonical Objective, Task, and
   `Plan` objects, including the complete Task DAG. Domain construction
   performs structural validation but creates no durable authority.
2. The Planner presents those exact pending canonical objects to the Human.
3. The Human responds through the ordinary conversation; Planner interprets
   whether that response authorizes, changes, questions, or abandons the
   candidate.
4. Only after clear Planner-interpreted authorization, application authority
   performs commit-boundary validation and atomically persists, adopts, and
   activates the exact candidate that preceded that Human response.

There is no mandatory separate application preflight or admission stage before
Human review. The implemented `PlanValidator` is a side-effect-free
boundary for requiring exact persisted Objective and Assumption content,
resolving exact Task membership, and verifying a canonical candidate without
side effects. Conversational authorization and the commit transaction are
implemented at the bounded SQLite application surface. The Human prompt is
retained in native conversation history, Planner produces the semantic
`continue_execution` conclusion, and conversation text alone is not direct
Application authority.

Authorization is not activation. The Plan visible to a user must be the same
exact Plan that application authority activates. A changed proposal remains a
new transient candidate and requires a later Human response before admission.

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

**Partially implemented.** The Phase 2 cognitive core directly owns one typed
PydanticAI Agent and performs one `plan_or_answer` invocation per
`Planner.run`. The model produces one `PlannerResult`: an immediate response, a
necessary Human clarification request, a transient candidate `Plan` with its
exact Task bundle, or a signal that a supplied active Plan should continue.
`PlannerOutput` is the separate runtime envelope for that result, current-run
native model messages, and any controlled error. No LangGraph workflow or
Planner-side tool is active in this phase.

Application exact-materializes the current SessionFrame Objective,
Assumptions, Tasks, Evidence, Discoveries, and DataProfile into immutable
`PlannerContext`. It resolves the objective-scoped active Plan for the frame's
exact current Objective and materializes that Plan without model inference. It
also exposes the exact prior pending Plan and Task bundle in separate fields;
those pending Tasks never enter the authoritative `tasks` field.
Native conversation history is supplied as model history but is
non-authoritative and is not duplicated into current-run `PlannerOutput.messages`.
Evidence and Discovery may support an answer. Assumptions may guide planning
but cannot support an empirical answer or be created by Planner.

Candidate validation rejects Tasks without a Plan, any Task bundle that does
not exactly match Plan membership and Objective scope, unknown Assumption IDs,
or changed content under an admitted Assumption ID. A candidate may reuse the
current Objective or contain a newly proposed Objective, but Application does
retain that exact bundle transiently. Typed approval atomically admits its
exact Objective and Tasks when needed, persists the Plan, and selects it active
for that Objective only after Planner interprets a later Human prompt as clear
authorization. Returning the same candidate preserves it, returning a new
candidate replaces it, and returning no candidate without continuation clears
it. The `continue_execution` signal requires a supplied pending or active Plan
and performs no execution. A pending Plan present before the invocation takes
precedence and is admitted exactly; a candidate returned by the same invocation
cannot be admitted. Capability, provider, executor, worker, and execution
routing are absent from the model-visible Planner contracts.

The immutable Phase 1 `Plan` and `PlanDependency` domain
contracts and side-effect-free application validation are **Implemented** with
exact persisted Objective and Assumption content checks, persisted Task
resolution, structural canonicalization, DAG guards, and deterministic
fingerprinting. Append-only exact snapshot persistence and fail-closed
identity/fingerprint reconstruction are **Verified on SQLite** as
infrastructure for the approval boundary. `PlanDependency` is one canonical
outgoing-adjacency group per prerequisite, while SQLite persistence remains
normalized as atomic edges. Validation alone does not persist a candidate.
Planner-interpreted Human authorization, atomic exact-bundle admission, and
objective-scoped active selection are **Verified on SQLite**. Pending candidate
and conversation recovery, Task DAG execution, and replanning runtime are
**Deferred**. Active
Task exposes all three canonical kinds, but only the
separate bounded `DATA` execution subsystem is executable; Planner does not
dispatch it in Phase 2. GeneratedView coordination, durable SessionFrame
composition, and the end-to-end recovery model remain **Deferred** target
design. The
[MVP-v2 definition](mvp-runtime-subset.md) explains the minimum complete
product and research capability.

Continue with [Executor and dispatch](executor-and-dispatch.md) or follow the
complete sequence in [End-to-end flow](end-to-end-flow.md).
