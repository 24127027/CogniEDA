# Planning and scientific state

Planning decides what governed work should be considered. Scientific state
records what was committed for investigation, what was observed, and what an
admitted claim may say. CogniEDA keeps these responsibilities separate so
planning material cannot silently become scientific support.

This page retains ownership of that planning-versus-science distinction. The
[scientific lifecycle](../scientific-lifecycle/index.md) owns the detailed
scientific sequence, contracts, outcomes, and governance.

## Objective establishes scope

An `Objective` is the root research scope. It bounds planning, scientific work,
retrieval, and governance. A Workspace may contain multiple Objectives, but a
Task or Hypothesis belongs to one Objective-scoped lineage rather than being
silently shared across Objectives.

## Assumptions guide planning only

An `Assumption` is a Human-authored provisional planning constraint. Planner
never invents, infers, paraphrases, improves, or strengthens one. It is not
Evidence and cannot serve as an inference premise in protected evaluation.
Every Human-proposed Assumption first crosses a reasonable-testability gate.

Keeping an Assumption explicit is still useful: it records the belief or
constraint that shaped planning, makes uncertainty visible, and lets later
Evidence trigger review. Quarantine preserves that context without rewarding
an untested belief with evidential authority. If the Human statement is not
reasonably testable within the project, data, or research workflow, its exact
text may remain a planning constraint. If it is reasonably testable, it does
not enter Assumption state and routes toward scientific investigation.

After Discovery admission, comparison may flag an Assumption for review. The
flag is not an automatic rewrite or deletion of either object.

## Task is work; PlanRevision is a plan

A `Task` is a durable semantic work unit of exactly one canonical kind:

```text
DATA
SCIENTIFIC
GRAPH
```

| Kind | Reader-facing purpose |
| --- | --- |
| `DATA` | explore, profile, or create an authorized successor data state through Data Explorer |
| `SCIENTIFIC` | govern one scientific investigation through Hypothesis Analyst |
| `GRAPH` | ask a bounded read-only question about semantic research-state relationships |

A Task is an independently managed deliverable. A short planning consultation
with Data Explorer or Graph Miner is not automatically a Task; it becomes one
only when the plan needs a governed work unit with its own identity and
lifecycle. A direct question that needs no project work, or that can already be
answered from retained authoritative state, does not become a Task. Planner
response synthesis is Planner behavior, not executable Task work.

`PlanRevision` is the non-FCO version of an entire proposed or approved Task
DAG. Exactly one immutable `PlanTaskBinding` represents each member Task and
owns non-negative `order_rank` and finite `LOW`, `NORMAL`, or `HIGH` priority.
Membership is
derived from binding Task identities, while dependencies remain explicit
edges. Those coordination concerns do not define Task identity.

The dependency DAG determines eligibility. `order_rank` expresses preference
among otherwise compatible work, permits ties, and never overrides a
dependency. Priority defaults to `NORMAL` and is scheduling metadata only; it
does not establish epistemic importance, authority, or Task meaning. Required
execution route, rank, priority, dependencies, parentage,
PlanRevision identity, approval, and activation are absent from Task semantic
identity.

Capability is execution-internal runtime plumbing, not approved plan content.
PlanRevision contains no provider, specialist, worker, tool, or routing hint.
Application authority determines eligibility and the governed action space;
Planner reasons about specialist interactions within that allowed space.
Provider or worker changes therefore do not change plan content or its
fingerprint. Planner coordinates but is not a Task executor.
There is no Planner or synthesis capability, provider, role, or compatibility
branch.

PlanRevision and its bindings contain no exact DataProfile identity or concrete
data selection. Planner describes intended data scope only in the Task
instruction. The responsible specialist or controller receives all
authoritative DataProfile context available for the work and selects the
applicable profile and concrete scope within its role-native authority. Exact
profiles actually used remain mandatory downstream execution or scientific
provenance and do not enter the PlanRevision fingerprint.

Its immutable plan content contains neither configurable stopping conditions
nor replan-trigger policy. Plan completion, interruption, approval and
activation state, and replanning belong to workflow lifecycle around the
revision. An actual cause that later requires reconsideration is a workflow
fact associated with the affected revision, not content that mutates the
historical plan. Scientific stopping remains `InvestigationProtocol`-owned;
bounded execution stopping remains work-order-owned.

A change to Task meaning requires a successor Task. A change to the approved
plan creates an authorized successor PlanRevision or returns to grounded
planning; it does not silently edit the active plan.

## Planner coordinates but does not operationalize science

Planner owns Objective and PlanRevision coordination, Task proposals, routing,
replanning, approval interaction, SessionFrame coordination, and GeneratedView
coordination. It does not author the scientific Hypothesis, InvestigationPlan,
InvestigationProtocol, Evidence obligations, decision rule, or protected final
evaluation.

A candidate PlanRevision crosses side-effect-free application validation before
the Planner presents it. Human approval authorizes only that exact candidate;
application authority must validate it again before later persistence and
activation. Validation alone is not admission and an unapproved candidate is
not durable authoritative PlanRevision state. See [Scientific authority](../scientific-lifecycle/scientific-authority.md)
for the complete authority split.

## Eligibility for scientific investigation

Only an eligible feasible leaf `SCIENTIFIC` Task can source exactly one
Hypothesis. Parent, proposed, unapproved, and infeasible Tasks source none. The
canonical owner of eligibility, feasibility outcomes, investigation records,
and scientific contracts is [Scientific authority](../scientific-lifecycle/scientific-authority.md).

## Observation, Evidence, and provenance

Data Explorer has exclusive dataset access but no final scientific-evaluation
or Evidence-admission authority. The canonical EvidenceRequest, DataWorkOrder,
ExecutionRun, AnalysisFrame, observation-candidate, and Evidence-admission
sequence is defined in [Evidence and AnalysisFrames](../scientific-lifecycle/evidence-and-analysis-frames.md).

## Protected evaluation and outcomes

Protected evaluation uses a closed `EvaluationBundle` and excludes
Assumptions, prior Discoveries as inference premises, conversation, generated
summaries, rejected Tasks, failed reasoning, unverified GeneratedViews, and
unrelated cross-Objective state. Its complete input and outcome rules are
owned by [Protected evaluation](../scientific-lifecycle/protected-evaluation.md).

## Discovery is conditional, not automatic

A Hypothesis produces at most one Discovery, and many valid investigations
produce none. DiscoveryProposal, governance, correction and additional-
Evidence loops, typed non-completion, and authoritative admission are owned by
[Discovery governance](../scientific-lifecycle/discovery-governance.md).

## Implementation status

**Partially implemented.** The active Task semantic core is Objective-scoped
and uses the canonical three-kind taxonomy. The immutable PlanRevision V1
domain and side-effect-free application validator are **Implemented** with
binding membership, routing compatibility, DAG validation, structural
fingerprinting, and authoritative Objective/Task checks. The append-only
repository foundation is **Verified on SQLite**, and no application caller
persists an unapproved proposal. Transient Planner authoring, exact in-process
Human approval, atomic approval-boundary persistence, first activation, active
selection, and sequential dependency-aware DATA execution are **Implemented**.
The current DATA-only runtime reports that reasonably testable Human claims
require scientific investigation but cannot execute them. Durable
approval/recovery, active-revision replacement, replanning, canonical
scientific execution, and the complete lifecycle linked above remain
**Deferred**.
