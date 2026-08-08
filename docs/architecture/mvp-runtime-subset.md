# MVP runtime subset

## Purpose and status

This page owns the approved **MVP executable subset** of CogniEDA. It defines
the deliberately smaller vertical slice that the MVP milestones will compose.
It is a **Design target**, not a claim that the end-to-end MVP is implemented
on current `main`.

The MVP narrows what is executable first. It does not replace, remove, or
redefine the [canonical architecture](system-overview.md). Current support is
reported separately in [Current state](../status/current-state.md).

## Canonical architecture versus executable MVP

The canonical FCO set remains exactly:

```text
Objective
DataProfile
Assumption
Task
Hypothesis
Evidence
Discovery
SessionFrame
```

The canonical semantic Knowledge Graph remains exactly:

```text
Objective
Hypothesis
Evidence
Discovery
```

The canonical architecture continues to include the complete planning,
scientific-investigation, execution, governance, admission, validity, and
presentation sequence:

```text
Objective
  -> PlanRevision
  -> Task
  -> ScientificInvestigationRun
  -> Hypothesis
  -> InvestigationPlan / InvestigationProtocol
  -> EvidenceRequest
  -> ExecutionRun
  -> AnalysisFrame
  -> Evidence
  -> EvaluationBundle
  -> DiscoveryProposal
  -> GovernanceDecision
  -> Discovery
  -> GeneratedView
```

The MVP runtime subset is defined to execute only:

```text
Objective
Assumption
Task
DataProfile
Evidence
SessionFrame
Planner
Data Explorer
ExecutorDispatcher
```

`Hypothesis` and `Discovery` remain canonical FCOs. They are **Deferred** from
the executable MVP, not deleted from CogniEDA.

## Operating constraints

The MVP is intentionally constrained to:

```text
1 process
1 active session
1 Planner
1 Data Explorer
1 active dataset
1 active DataProfile
1 active Objective
```

These constraints do not supersede the canonical decision allowing multiple
Objectives per Workspace or the longer-term continuity model. They only bound
the first executable vertical slice.

## Minimum research-state thesis

The MVP must prove a typed research-state path rather than a chatbot-with-tools
path:

```text
User message
  -> Planner
  -> Task
  -> Capability
  -> ExecutorDispatcher
  -> Data Explorer
  -> dataset/tool execution
  -> Evidence
  -> SessionFrame
  -> Planner
  -> response
```

Every data-derived response must remain traceable through:

```text
data-derived response
  -> Evidence
  -> Task
  -> DataProfile
  -> dataset/tool execution
```

Chat history may support conversational continuity, but chat history is not
authoritative research state. Follow-up reasoning must use typed state retained
in the active `SessionFrame`, including prior Evidence, instead of reconstructing
research truth from the transcript.

## MVP object semantics

This section fixes minimum meaning for M1-A without freezing implementation
schemas.

### Objective

The minimum semantic payload is the Objective text, with internal identity as
needed. Exactly one Objective is active in an MVP session.

### Assumption

The minimum semantic payload is the Assumption text. An Assumption supports
planning only:

```text
Assumption != Evidence
```

The full testability and scientific-quarantine workflow is **Deferred**, but
the MVP must not use an Assumption as empirical support.

### Task

An MVP Task is a bounded EDA work unit with, at minimum, a `task_id` and
instruction. A simple `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED` lifecycle
may support the vertical slice. Semantic change must create a successor or new
Task identity; it must not silently rewrite existing work meaning.

### DataProfile

The active dataset description must contain enough typed context for Planner
and Data Explorer. At minimum it describes `data_profile_id`, row count, column
count, and columns. Each column profile describes name, dtype, variable type,
distinct count, missing count, and summary. MVP variable type is `DISCRETE` or
`CONTINUOUS`.

### Evidence

MVP Evidence is typed research state produced from successful real dataset
work. At minimum it links `evidence_id`, `task_id`, `data_profile_id`, content,
provenance, and artifact references.

This direct Task-to-Evidence MVP linkage is an executable-subset contract, not
the complete canonical scientific Evidence contract. It must not fabricate a
Hypothesis or set `hypothesis_id = task_id`. A failed execution creates no
Evidence. The later canonical scientific cutover must introduce its real
Hypothesis, EvidenceRequest, ExecutionRun, AnalysisFrame, and admission
lineage rather than aliasing their identities.

### SessionFrame

The MVP active context contains the Objective, Assumptions, Tasks, Evidence,
and active DataProfile. Evidence must remain typed and retained in the frame so
follow-up work does not depend on transcript reconstruction.

## Role and authority boundaries

Planner remains the only human-facing agent. For the MVP it will inspect the
active `SessionFrame`, understand Objective and Assumptions, inspect the active
DataProfile and prior Evidence, create bounded Tasks, select a capability,
invoke the dispatcher, consume `PlannerWorkOutcome`, coordinate authorized
state updates, and respond to the human.

Planner does not read a dataframe, run pandas or analytical code, mutate a
dataset, or author authoritative Evidence directly. Dataset work belongs
exclusively to Data Explorer.

Data Explorer may read the active dataset, profile it, compute descriptive
statistics, perform bounded EDA, execute admitted analytical tools, and return
role-native observations and provenance material. It does not answer the
human, evaluate a scientific Hypothesis, author a Discovery, perform
governance, or admit durable state. Application/runtime authority owns
validation and admission where the MVP contract requires them.

## Capability and dispatch model

`Capability` identifies an executable ability exposed by a specialist. The
current S0 data capabilities are:

```text
DATA_ANALYSIS
DATA_PROFILING
DATA_TRANSFORMATION
```

Planner selects the capability. `ExecutorDispatcher` owns capability-to-provider
routing through an explicit registry:

```text
Planner
  -> capability invocation
  -> ExecutorDispatcher
  -> ExecutorRegistry
  -> provider
```

A request carries the capability, not a redundant `executor_id`. Registry
composition is intentionally:

```text
Capability
  -> provider factory
  -> reusable provider instance
```

One provider may expose multiple compatible capabilities. The current
PydanticAI integration exposes capability invocation to the model as tools,
while `ExecutorDispatcher` remains the architectural dispatch boundary.
PydanticAI is an adapter, not part of the canonical architecture.

`DATA_TRANSFORMATION` must preserve immutable dataset-state semantics:

```text
current dataset state
  -> DATA_TRANSFORMATION
  -> new dataset state
  -> successor DataProfile
```

It must never mutate the active dataset in place. The current S0 provider
correctly returns a typed blocker because successor dataset and DataProfile
creation are not implemented.

## Result boundary

Specialists retain role-native results, for example `DataExplorerResult`,
`HypothesisAnalystResult`, and `GraphInquiryResult`. A generic semantic
mega-result with optional fields from every specialist is not an approved
contract.

Application coordination projects the Planner-facing subset into
`PlannerWorkOutcome`. Its conceptual fields are source role, Task identifier,
work identifier, status, semantic summary, authoritative references,
limitations, blockers, permitted next actions, and result digest.

This is an architectural target. Current S0 implements a minimum normalization
seam over shared transport metadata; semantic projection and Planner
consumption remain **Deferred**.

## Explicit MVP non-goals

The following canonical or operational capabilities are **Deferred** from the
MVP runtime:

- Hypothesis Analyst and Hypothesis runtime;
- Discovery and Graph Miner runtime;
- PlanRevision and a Task DAG;
- InvestigationPlan, InvestigationProtocol, and EvidenceRequest;
- the canonical AnalysisFrame and ExecutionRun authority model;
- GovernanceDecision, Discovery admission, and validity propagation;
- human-in-the-loop approval flows;
- restart-safe coordination and multi-session continuity;
- multi-Objective concurrency and semantic Knowledge Graph retrieval;
- streaming, distributed queues, and DVC.

UI implementation is outside the backend MVP scope. Deferred components remain
part of the canonical architecture and must not be described as removed.

## Milestone ownership

| Milestone | Ownership | Status relative to this page |
| --- | --- | --- |
| S0 | executor capability stabilization | **Implemented** at the bounded S0 library surface |
| D0 | MVP and canonical documentation reconciliation | **Implemented** by this documentation boundary |
| M1-A | MVP research-state core: Objective, Assumption, Task, Evidence, DataProfile, and SessionFrame | **Deferred** |
| M1-B | MVP Planner behavior, including `PlannerWorkOutcome` consumption | **Deferred** |
| M3-A | MVP Data Explorer plus Evidence and real tool execution | **Deferred** |
| M5-A | single-session runtime composition | **Deferred** |
| MVP-I | vertical integration | **Deferred** |
| MVP-V | final MVP verification | **Deferred** |

Post-MVP ownership is:

| Milestone | Ownership | Status |
| --- | --- | --- |
| M1-C | full canonical planning cutover: PlanRevision, Task DAG, canonical routing, activation, and approval semantics | **Deferred** |
| M2 | scientific authority: Hypothesis Analyst, Hypothesis, ScientificInvestigationRun, InvestigationPlan, InvestigationProtocol, and evaluation | **Deferred** |
| M3-B | canonical execution and Evidence authority: EvidenceRequest, DataWorkOrder, ExecutionRun, AnalysisFrame, and Evidence admission | **Deferred** |
| M4 | governance, Discovery, and validity: EvaluationBundle, DiscoveryProposal, GovernanceDecision, Discovery admission, and validity propagation | **Deferred** |
| M5-B | durable runtime and recovery: restart, resume, claims, leases, idempotency, and multi-Objective durable coordination | **Deferred** |

Graph Miner remains **Deferred** until an explicit runtime-provider milestone
is scheduled. Hypothesis Analyst, Graph Miner, governance, and Discovery do not
belong to M5-A.

## MVP Definition of Done

The backend MVP is complete only when this path is demonstrated:

```text
dataset loaded
  -> DataProfile generated
  -> SessionFrame initialized
  -> user prompt
  -> Planner
  -> Task
  -> Capability
  -> ExecutorDispatcher
  -> Data Explorer
  -> real dataset tool
  -> Evidence
  -> SessionFrame
  -> PlannerWorkOutcome
  -> Planner response
  -> follow-up uses the same typed state
```

Verification must prove real dataset access by Data Explorer, real tool
execution, Evidence linkage to Task and DataProfile, retained provenance,
typed-state reuse on follow-up, no transcript reconstruction as research-state
authority, no fabricated Evidence after failure, and runtime-configurable model
configuration.
