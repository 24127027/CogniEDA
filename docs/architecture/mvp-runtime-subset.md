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

The bounded runtime represents that separation explicitly:

```text
Session = SessionFrame + ConversationHistory
```

`Session` is a non-FCO in-process lifetime aggregate. `ConversationHistory`
retains one complete ordered PydanticAI `ModelMessage` history, grouped only by
top-level `ConversationTurn` boundaries. A turn stores `turn_id` and
`messages`; it has no duplicated Human/Planner surface fields or segment
wrapper. CogniEDA does not revalidate PydanticAI's tool or retry protocol.
`SessionFrame` contains cumulative typed FCO IDs plus active Objective and
DataProfile selectors. Runtime `Application` separately selects bounded
complete conversation turns and a bounded `PlannerContextSelection` of
research-state references. The runtime `PlannerContextPreparer` then resolves
authoritative FCOs through the concrete SQLite gateway, expands Evidence
dependencies, and materializes one ephemeral `PlanningContext` before calling
`Planner.run`. Selected messages are copied into bounded effective
`message_history`; historical run-scoped instructions are removed from that
copy without changing retained history. The current authoritative
`PlanningContext` is supplied as new run-scoped instructions and the Human
request remains the user prompt. Planner receives no research-state read
dependency. Empirical answer context remains Evidence-only.
Resolved dependencies and context acquired later through an authorized role
seam are not automatically persisted into `SessionFrame`.

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

The M1-A boundary is **Implemented** as an immutable Task value. Lifecycle
change returns a validated replacement with the same `task_id` and instruction;
neither semantic field can be changed in place.

### DataProfile

The active dataset description must contain enough typed context for Planner
and Data Explorer. At minimum it describes `data_profile_id`, row count, column
count, and columns. Each column profile describes name, dtype, variable type,
distinct count, missing count, and summary. MVP variable type is `DISCRETE` or
`CONTINUOUS`.

M1-A continuous statistics are **Implemented** as finite, JSON-safe values.
Direct schema construction rejects non-finite statistics. Profiling excludes
non-finite source observations from continuous descriptive calculations and
uses `None` if a computed statistic is non-finite.

The bounded M3-A authority surface is **Implemented** with a separate non-FCO
`DataProfileDatasetBinding`. Initial candidate admission atomically persists
the immutable DataProfile plus its normalized physical dataset reference and a
SHA-256 digest of the exact loaded file bytes. Both path and digest define the
MVP physical dataset state: same content at another path does not inherit an
existing binding, and changed content at the same path is rejected before
Evidence admission. Admission does not activate the profile.

### Evidence

MVP Evidence is typed research state produced from successful real dataset
work. At minimum it links `evidence_id`, `task_id`, `data_profile_id`, content,
provenance, and artifact references.

This direct Task-to-Evidence MVP linkage is an executable-subset contract, not
the complete canonical scientific Evidence contract. It must not fabricate a
Hypothesis or set `hypothesis_id = task_id`. M1-A schema and repository guards,
plus the bounded M3-A application service, are **Implemented** to require the
referenced Task to be exactly `COMPLETED`; `PENDING`, `RUNNING`, and `FAILED`
work cannot produce admitted MVP Evidence. The later canonical
scientific cutover must introduce its real Hypothesis, EvidenceRequest,
ExecutionRun, AnalysisFrame, and admission lineage rather than aliasing their
identities.

### SessionFrame

The MVP frame is a cumulative typed reference manifest: ordered Objective,
Assumption, Task, DataProfile, and Evidence IDs plus optional active Objective
and DataProfile selectors. It does not copy materialized FCO payloads. Changing
an active selector preserves historical membership. Follow-up work rebuilds a
bounded `PlanningContext` from selected authoritative objects, so a Task status
change is visible without replacing its ID in the frame. Frame membership is
continuity metadata, not current-run selection, eligibility, or authority.

M1-A SessionFrame state is **Implemented** with ordered, read-only ID
collections, active-selector membership validation, and successor seams that
preserve history and reject duplicate IDs. The bounded selector considers the
active identities plus finite recent history. The application
`PlannerContextPreparer` can expand a selected Evidence reference to its
authoritative Task and DataProfile without adding those dependencies to the
frame. Evidence admission remains the owner of the underlying lineage
invariant.

## Role and authority boundaries

Planner remains the only human-facing agent. At the bounded M1-B library
boundary it consumes the materialized `PlanningContext` and effective native
message history prepared by runtime; it does not inspect the durable
`ConversationHistory` aggregate or build its initial context from
`SessionFrame`. It understands the latest request, establishes or changes the
active Objective while retaining prior Objective IDs, records planning-only
Assumptions, creates
bounded Tasks, selects a typed capability, invokes the injected dispatcher,
consumes `PlannerWorkOutcome`, returns a successor frame, and responds to the
human. This does not persist or retain the frame across process restarts. The
runtime `Application` does retain one coherent successor `SessionFrame` and
append-only `ConversationHistory` across in-process turns.
Restart-safe persistence and full M3-A-to-Planner Evidence composition remain
**Deferred**.

Planner does not read a dataframe, run pandas or analytical code, mutate a
dataset, or author authoritative Evidence directly. Dataset work belongs
exclusively to Data Explorer.

Data Explorer may read the active dataset, profile it, compute descriptive
statistics, perform bounded EDA, execute admitted analytical tools, and return
role-native observations and provenance material. It does not answer the
human, evaluate a scientific Hypothesis, author a Discovery, perform
governance, or admit durable state. Application/runtime authority owns
validation and admission where the MVP contract requires them.

The bounded M3-A library surface separates three contracts:

```text
DataProfileCandidate or DataExplorerResult   non-authoritative specialist output
DataProfile plus dataset binding, Evidence   authoritative application state
PlannerWorkOutcome                           Planner-facing projection
```

Initial profiling may produce a task-free `DataProfileCandidate`. Filesystem
presence never admits or activates it; application authority performs the
separate atomic profile-and-binding admission. Profiling an already admitted
profile returns observation material instead of creating another candidate.
Evidence admission requires the authoritative binding and checks both the
requested and actually executed dataset identity against it.

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

One provider may expose multiple compatible capabilities. The bounded
PydanticAI data-capability adapter remains available as a tested internal seam,
but the M1-B Planner does not compose it as a model tool. Typed request
understanding proposes work, deterministic Planner code constructs and tracks
the canonical Task, and only then invokes `ExecutorDispatcher`. PydanticAI
remains an adapter, not part of the canonical architecture.

For `DATA_ANALYSIS`, role-neutral `ExecutorContext` carries only the explicit
absolute `dataset_path` and exact `data_profile_id`; the typed role-specific
`DataExplorerInput` carries the matching authoritative DataProfile projection.
Planner creates the Task and selects `DATA_ANALYSIS`;
Data Explorer owns translation of that bounded Task instruction into its
role-specific `DataAnalysisPlan` through a typed planning port. The plan
contains one allowlisted operation, exact column names, and only the bounded
parameters admitted for that operation. Neither Planner nor runtime constructs
the plan. M3-A supports:

```text
ROW_COUNT
COLUMN_SUMMARY
MISSINGNESS
VALUE_COUNTS
DESCRIPTIVE_STATISTICS
GROUP_SUMMARY
CORRELATION (PEARSON or SPEARMAN)
```

The Data Explorer model adapter may propose only this typed plan from the Task
instruction and supplied DataProfile/schema. Deterministic code validates the
proposal against the exact loaded dataset and computes the result. Invalid or
unsupported proposals fail with typed zero-observation results; there is no
fallback operation or fuzzy column repair. A model does not author numeric
output. Arbitrary generated Python is **Unsupported**, and there is no
environment or repository-root dataset fallback. `DataAnalysisPlan`,
`DataAnalysisOperation`, and `CorrelationMethod` are owned by Data Explorer;
the role-neutral `execution` package retains only shared dispatch contracts.

`DATA_TRANSFORMATION` must preserve immutable dataset-state semantics:

```text
current dataset state
  -> DATA_TRANSFORMATION
  -> new dataset state
  -> successor DataProfile
```

It must never mutate the active dataset in place. The current M3-A provider
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

S0 implements the minimum normalization seam over shared transport metadata.
M1-B consumption is **Implemented** at the bounded Planner library boundary:
the Planner verifies Task identity, preserves the normalized digest,
limitations, blockers, and permitted next actions, and applies a terminal Task
status. The outcome is not admitted as Evidence.

M3-A adds an application-owned admission seam after `DataExplorerResult`.
Admission verifies successful status, source role, Task identity and persisted
`COMPLETED` state, capability, authoritative DataProfile identity, authoritative
normalized path and content-digest binding, role-native plan/tool/provenance
agreement, one non-empty JSON-safe result, and bounded lineage. The Evidence
identity includes the verified dataset digest. It then commits one immutable
Evidence whose content is
the validated operation, parameters, and deterministic result. Exact replay
returns the same Evidence; conflicting reuse of a work reference fails closed.
The resulting application projection contains the real Evidence reference.

## Bounded M1-B Planner behavior

The active M1-B graph is:

```text
START
  -> understand_request
  -> apply_planning_state
  -> dispatch_work
  -> compose_response
  -> END
```

Request understanding uses a finite typed action contract for answering from
state, setting or refining the Objective, adding an Assumption, creating and
running bounded data work, summarizing state, or returning an unsupported
action. Natural language is the primary model-backed interface. The small
explicit command surface maps into the same typed actions and unknown commands
fail without state mutation or dispatch.

Deterministic orchestration persists Objective, Assumption, and Task values
through the application `PlannerStateMutationPort`, then records their IDs
through `SessionFrame` successor seams. The port contains only current
mutation and Task-lifecycle operations; context reads remain at the runtime
composition boundary. Semantic Objective refinement receives a new identity;
semantic Task change creates a new Task; lifecycle change updates the
authoritative Task while retaining its frame ID and instruction. Tracked data
work follows:

```text
PENDING -> RUNNING -> COMPLETED  on SUCCEEDED
PENDING -> RUNNING -> FAILED     on FAILED, BLOCKED, or dispatch failure
```

The M1-B Planner still reports direct dispatcher completion and does not author
or admit Evidence. Failed or blocked work surfaces controlled diagnostics.
The separate M3-A application service admits eligible successful work for
later composition; failed or blocked work cannot pass that service. Answers
that claim empirical support receive an evidence-only typed input from Evidence
resolved into the current `PlanningContext`; planning Assumptions and
conversation are excluded.

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
| M1-A | MVP research-state core: Objective, Assumption, Task, Evidence, DataProfile, and SessionFrame | **Implemented** |
| M1-B | MVP Planner behavior, including `PlannerWorkOutcome` consumption | **Implemented** at the bounded library behavior surface |
| M3-A | MVP Data Explorer plus Evidence and real tool execution | **Implemented** at the bounded library/data-authority surface |
| M5-A | single-session runtime composition | **Partially implemented** for in-process SessionFrame and ConversationHistory continuity; dataset execution context and Evidence admission composition remain **Deferred** |
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
