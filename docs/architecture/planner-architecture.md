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
Assumptions that materially influenced planning, full exact Task definitions,
and one Task DAG. Its content owns only:

- canonical full Tasks as the direct and only writable membership representation;
- explicit dependency edges between member Tasks;
- a deterministic plan-content fingerprint.

The fingerprint covers exact Objective and Assumption representations,
canonical status-free Task semantic definitions, and canonical dependency edges. It
excludes Task runtime status and all execution-routing, approval, activation,
timestamp, conversation, model, and DataProfile-selection state. Assumptions
remain planning basis only and cannot support protected evaluation.

`tasks` is the single writable membership source of truth; `task_ids` is
derived exactly from canonical Task order. Changing Task meaning changes Plan
content and its fingerprint; changing only mutable Task execution status does
not. Changing membership or a dependency changes Plan content without, by
itself, creating a successor Task.

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
Human review. The implemented `PlanValidator` is a side-effect-free boundary
for requiring exact persisted Objective and Assumption content, resolving exact
Task membership, and verifying a canonical candidate without side effects. The
atomic commit transaction and objective-scoped active Plan selection are
**Verified on SQLite**. The in-process Planner LangGraph lifecycle retains the
exact candidate outside authoritative research state, resumes natural-language
Human review, and calls `PlanAdmissionService` only when a typed
   `continue_execution` result authorizes that retained Plan. Application
authority still performs all commit-boundary validation, persistence, and
activation.

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

**Partially implemented.** The Planner directly owns one typed PydanticAI Agent
and its compiled LangGraph `StateGraph` with exactly `plan_or_answer`,
`await_human`, and `admit_candidate` lifecycle nodes. `Planner.handle_message()`
hides graph invocation, interrupt/resume, checkpointer, and thread mechanics
from Application. The graph does not add an execution node or a Planner-side
tool.

`PlannerState` owns only the latest Human input, one self-contained transient
candidate Plan, the active thread's native model-message history, and a typed turn outcome. It does
not own `PlannerContext`. Graph construction directly binds the Planner's
cognitive invocation, the fresh-context port, and the deterministic
Plan-admission port to node callables; there is no callback-only graph context
object.

`graph.py` declares the static topology: `START -> plan_or_answer`,
`await_human -> plan_or_answer`, and `admit_candidate -> END`.
`plan_or_answer` alone selects dynamic destinations because its semantic result
may require Human input, exact candidate admission, or completion. No routing-only
field or checkpointed `PlannerResult` is added. `Planner.handle_message()`
rejects empty Human input as a controlled outcome before initial invocation or
interrupt resume, so the successful `await_human` route remains static.

`PlannerContextProvider` reads the workspace-scoped current SessionFrame from
`SessionFrameRepository` on every invocation and exact-materializes its Objective,
Assumptions, Hypotheses, Evidence, Discoveries, and DataProfile into immutable
`PlannerContext`. It resolves the objective-scoped active Plan for the frame's
exact current Objective and materializes that Plan without model inference.
`PlannerContext` contains neither candidate Plan state nor conversation
history. A `PlannerContextProvider` materializes it fresh for every Planner
invocation. The active LangGraph thread checkpoints native messages and supplies
them separately as PydanticAI `message_history`, while the latest Human text
remains the current user prompt. Only `result.new_messages()` from the current
run are appended. `ConversationHistory` remains a typed non-authoritative
session-memory component, but this phase does not synchronize or durably persist
it alongside graph state. A future unified `SessionMemory` is intended to
compose `SessionFrame` and `ConversationHistory`; it must not derive research
authority from conversation.
The deterministic serialized `PlannerContext` is supplied fresh through the
current-run instruction channel, explicitly bounded as data/state and declared
to supersede historical research-state references. Replaceable authority is
therefore not appended to the conversational Human-message stream.
Evidence and Discovery may support an answer. Assumptions may guide planning
but cannot support an empirical answer or be created by Planner.
Task definitions for active Plan members are not put back into research state;
a coordination-specific Task projection remains **Deferred** to Task selection
and execution.

Plan validation rejects duplicate Task identities, cross-Objective Tasks,
invalid dependency endpoints, duplicate dependency groups, and cycles.
Model/context validation rejects unknown Assumption IDs or changed content under
an admitted Assumption ID. A candidate may reuse the current Objective or
contain a newly proposed Objective. LangGraph retains the self-contained exact
Plan across Human turns; a later Planner result may retain,
replace, or explicitly discard it. A typed `continue_execution` result while a
candidate is pending routes to `PlanAdmissionService`, whose success clears the
candidate and whose controlled failure retains it for correction. Human review
uses LangGraph interrupt/resume state rather than keywords, regexes, or an
application-owned approval parser. Capability, provider, executor, worker, and
execution routing are absent from the model-visible Planner contracts.

If no candidate is pending, `continue_execution` still requires an active Plan.
Planner returns a visible controlled outcome that execution is not implemented
and performs no dispatch. Application maps that typed outcome to EventBus
presentation events; EventBus does not own lifecycle state. Application owns no
persistence repository, Planner history, or `ConversationHistory` lifecycle.
Planner-owned `InMemorySaver`, its smallest required trusted process-local typed
serializer, and one Planner thread UUID preserve isolated in-process threads
only. Restart recovery, durable `ConversationHistory`, unified `SessionMemory`,
and durable conversation/candidate checkpoints remain **Deferred**.

PR #53 is a structural precedent only for Planner-owned `agent.py`, `graph.py`,
`nodes.py`, and `state.py` placement. Its checkpointed `PlannerContext`, typed
`PlanReviewAction`/`PlanReviewDecision` review API, conversation-in-context
model, and `execute` node are superseded and are not restored.

The immutable Phase 1 `Plan` and `PlanDependency` domain
contracts and side-effect-free application validation are **Implemented** with
exact persisted Objective and Assumption content checks, persisted Task
resolution, structural canonicalization, DAG guards, and deterministic
fingerprinting. Append-only exact snapshot persistence and fail-closed
identity/fingerprint reconstruction, including full Task reconstruction, are
**Verified on SQLite** as
infrastructure for the approval boundary. `PlanDependency` is one canonical
outgoing-adjacency group per prerequisite, while SQLite persistence remains
normalized as atomic edges. Validation alone does not persist a candidate.
Atomic exact-bundle admission and objective-scoped active selection are
**Verified on SQLite** through the runtime's application-authority service.
Task DAG selection/execution, plan completion, successor/replanning
orchestration, and durable lifecycle recovery are **Deferred**. Active Task
exposes all three canonical kinds, but only the
separate bounded `DATA` execution subsystem is executable; Planner does not
dispatch it in Phase 2. GeneratedView coordination, durable SessionFrame
composition, and the end-to-end recovery model remain **Deferred** target
design. The
[MVP-v2 definition](mvp-runtime-subset.md) explains the minimum complete
product and research capability.

Continue with [Executor and dispatch](executor-and-dispatch.md) or follow the
complete sequence in [End-to-end flow](end-to-end-flow.md).
