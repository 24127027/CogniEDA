# Research-state model

CogniEDA gives durable identity only to concepts that must remain independently
addressable across an investigation. Durable identity is not the same as
scientific authority: a `Task` is durable workflow state, while a `Discovery`
is durable scientific knowledge.

The canonical First-Class Objects (FCOs) are exactly:

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

This set separates research intent, data state, planning constraint, workflow
state, test contract, observed result, evidence-bound claim, and active context.
Other durable records may be essential, but they remain provenance,
coordination, generated output, or optimization state rather than FCOs.

## The roles at a glance

| Research role | Canonical representation | Why it stays separate |
| --- | --- | --- |
| research intent | `Objective` | intent can change without rewriting results |
| data state | `DataProfile` | conclusions need an exact dataset-state identity |
| planning constraint | `Assumption` | provisional beliefs must not become inference premises |
| workflow state | `Task` | work status is not scientific knowledge |
| test contract | `Hypothesis` | one analytical claim needs one bounded validation contract |
| observed result | `Evidence` | observation must remain distinct from interpretation |
| evidence-bound claim | `Discovery` | durable knowledge needs scope and validity basis |
| active context | `SessionFrame` | continuity needs a governable projection, not raw chat |
| provenance | `AnalysisFrame`, `ExecutionRun` | data-view and attempt identity support Evidence |
| validity provenance | `ValidityEvent` | authorized authority changes remain traceable without becoming scientific claims |
| generated output | `GeneratedView` | presentation is useful but not scientific authority |
| optimization state | `EvidenceCacheEntry` | reuse must not become a scientific writer |

## Objective: durable research intent

An `Objective` represents the research outcome the project is trying to achieve.
In the running example, the Objective is broader than one statistical test:
understand actionable drivers of 90-day churn in the small-business cohort.

It needs durable identity because Tasks, frames, and later decisions need a
stable research direction even when its wording or lifecycle changes. It is not
a question string, a plan, a Task, or a conclusion.

On the supported governed Planner path, Objective creation and revision require
approved operations; revisions retain provenance. Current repositories also
provide narrow persistence surfaces used by bootstrap and tests. An Objective
may be active, paused, completed, or archived, but changing it does not rewrite
the Evidence or Discoveries already produced under its earlier state.

For future reasoning, the active Objective bounds what planning and retrieval
are trying to accomplish. It does not enter a protected Discovery as an
empirical premise.

**Implementation status:** Objective schema, persistence, approved Planner
operations, and revision provenance are **Implemented**. A complete product
workflow for project creation and closure is **Partially implemented**.

## DataProfile: immutable dataset state

A `DataProfile` represents one semantic profile of one dataset version:
identity, schema, baseline characteristics, quality signals, preprocessing
history, and acceptance state. In the running example it identifies the
specific retention dataset and cohort source used by the analysis.

It needs durable identity because a path such as `retention.csv` is not enough
to prove what data supported a claim. It is not the physical dataset, a
workspace, an analysis result, or a mutable “current data” record.

Profiling library functions can construct a profile and the repository can
persist a new one. The complete governed import, review, and acceptance product
workflow is not present. Scientific profile content is immutable. Authorized
validity propagation may change lifecycle metadata to invalidated or superseded
and may point to a replacement; it does not rewrite the recorded profile.

Future execution and protected evaluation require the bound profile to be
active and accepted as ground truth. When a profile loses validity, dependent
state can be invalidated and removed from active retrieval.

**Implementation status:** profiling and immutable profile persistence are
**Implemented**; validity propagation is **Verified on SQLite**; governed
dataset acceptance and executable versioning are **Partially implemented** or
**Deferred**.

## Assumption: planning-only provisional belief

An `Assumption` represents a provisional statement useful for planning. “Each
row represents one account-month” may help the team decide what to inspect
before testing churn.

It needs durable identity so the project can expose its source, scope,
confidence, status, contradiction signals, and replacement history. It is not
Evidence, a Hypothesis, or an inference premise. A testable claim that can be
investigated in the project should become a Task/Hypothesis candidate instead
of being admitted as an Assumption.

Planner operations and repository bootstrap paths can create Assumptions;
governed operations can change their lifecycle. After a Discovery is admitted,
another process may flag a contradiction for review, but it must not rewrite
either the Assumption or the Discovery automatically.

Assumptions may influence planning context. They are structurally absent from
the protected evaluation bundle and excluded from conclusion and Discovery
synthesis context.

**Implementation status:** typed Assumptions, persistence, planning projection,
and protected-evaluation quarantine are **Implemented**. General contradiction
review and product governance are **Partially implemented**.

## Task: durable workflow state

A `Task` represents proposed, active, paused, completed, failed, rejected, or
cancelled work. A parent Task can organize a question such as “understand churn
drivers,” while a terminal analytical child can test first-response time
against churn.

It needs durable identity because approvals, dependencies, decomposition,
motivation, execution, and review state must survive sessions. It is not
scientific knowledge and completion is not proof that its description is true.

Supported Planner paths draft operations, persist the exact proposal, and ask
the user to approve or reject it before commit. Only an active terminal
analytical Task with an accepted profile and complete analytical specification
can enter the execution path. Evidence admission does not complete the Task;
atomic Discovery admission completes the terminal Task together with the
Discovery chain. Validity loss later adds review reasons without pretending the
historical workflow never occurred.

Tasks influence future planning, prioritization, and retrieval. They are
excluded from protected Discovery synthesis because workflow intent is not an
observed premise.

**Implementation status:** Task persistence, guarded Planner proposals,
decomposition, execution eligibility, and terminal completion are
**Implemented** on the covered paths. Broader natural-language planning and
review branches are **Partially implemented**.

## Hypothesis: one bounded test contract

A `Hypothesis` represents the atomic test contract produced for one terminal
analytical Task. It binds a statement, profile, variables, scope, validation
method, and expected Evidence.

It needs durable identity so execution attempts, Evidence, evaluation, and the
eventual Discovery all refer to the same contract. It is not an Assumption, an
executor request alone, a result, or a conclusion.

On the current supported fresh-admission path, the approved execution contract
creates the single Hypothesis for the Task and admits an execution attempt.
The branch that attempts to reuse an existing nonterminal Hypothesis currently
fails closed at lifecycle ownership and is a **Known deviation**. Evidence
admission advances the fresh Hypothesis to ready for evaluation. Atomic
Discovery admission alone moves it to evaluated; authorized validity
propagation can move a pre-Discovery Hypothesis back to awaiting additional
Evidence or attach review state after validity loss.

The protected evaluator uses the Hypothesis as its evaluand. It must not expand
the scope, change the method, or substitute another Evidence set.

**Implementation status:** guarded creation, execution binding, protected
evaluation, lifecycle transitions, and cardinality are **Implemented** on the
current path. It is a **Known deviation** that the Planner currently authors
the operational analytical contract; the preferred long-term boundary assigns
operationalization to the Hypothesis Analyst.

## Evidence: immutable observed analytical result

`Evidence` represents what an approved analytical execution observed. It binds
the result summary, method, parameters, limitations, artifacts, `AnalysisFrame`,
`ExecutionRun`, Hypothesis, and DataProfile.

It needs durable identity because evaluation and validity must cite exact
observations rather than a paraphrase. It is not an interpretation, a
Discovery, a report, or proof that a Hypothesis is true.

The Data Explorer returns observation-only values and has no persistence
authority. The Evidence admission transaction validates durable lineage,
materializes the `AnalysisFrame` and immutable Evidence, advances the execution
and Hypothesis, and consumes the authoritative result receipt. Generic
repository creation is sealed. Authorized validity propagation may update
lifecycle metadata or link a replacement; scientific content remains
unchanged.

Only active Evidence with canonical lineage enters protected evaluation.
Superseded or invalidated Evidence remains historical but is excluded from
active scientific context.

**Implementation status:** observation contracts and atomic Evidence admission
are **Implemented** and **Verified on SQLite**. A concrete production Data
Explorer is **Unsupported**.

## Discovery: durable evidence-bound claim

A `Discovery` represents a scoped claim justified by one Hypothesis and its
active Evidence. It carries an epistemic status, structured claim, scope,
uncertainty, validity basis, limitations, and invalidators.

It needs durable identity because future answers, planning, conflict review, and
validity propagation must cite the exact admitted claim. It is not an Evidence
record, free-form summary, parent-Task answer, Analyst draft, or user decision.

The Hypothesis Analyst may author a `DiscoveryProposal`, but cannot persist it.
Governance may approve, reject, or cancel the exact proposal, but cannot create
the claim. Atomic Discovery admission reloads the current authority and copies
the approved proposal into the durable Discovery without application-authored
scientific rewriting. That same transaction completes the terminal Task and
Hypothesis, commits control and claim state, consumes the decision, and creates
a conclusion SessionFrame.

Discoveries may be retrieved for planning or answers only when lifecycle and
scope policy allow. They are excluded from the synthesis context for a new
Discovery. Invalidation changes active eligibility while preserving historical
trace.

**Implementation status:** protected proposal creation, governance, exact-copy
admission, and validity interaction are **Implemented** and
**Verified on SQLite**.

For the authority rationale and transaction boundary, see
[Scientific authority](scientific-authority.md) and
[Governance and Discovery admission](governance-and-discovery-admission.md).

## SessionFrame: user-governed active-context projection

A `SessionFrame` represents a compact, user-governed projection for active
work, a checkpoint, or a handoff. It can summarize the Objective and selected
profiles, Tasks, Assumptions, Hypotheses, Evidence, Discoveries, user
decisions, pins, exclusions, warnings, stale context, and dead ends.

It needs durable identity because another operation or session must know which
snapshot it is resuming, what preceded it, and whether it has been superseded.
It is not raw chat, the full project history, a retrieval index, a conclusion
bundle, or scientific knowledge. Persisted frame content is append-oriented:
user-directed context changes create an appended or successor projection rather
than rewriting the selected content of an earlier frame. Lifecycle metadata can
still mark an older frame superseded.

Repositories append frames; approved Planner operations may create successor
snapshots; atomic Discovery admission creates a deterministic conclusion frame;
and validity propagation can supersede affected frames. The project does not
yet provide a complete user-facing frame editor, item-governance workflow, or
workspace-open resume bootstrap.

A frame may contribute selected typed objects through a mode-specific
projection. Planning may include active Assumptions and workflow state. Answer
context may include active Discoveries. The frame itself is not scientific
authority, and selected objects retain the rules of their own epistemic types.
Protected synthesis excludes the frame, arbitrary pins, Assumptions, Tasks,
existing Discoveries, user decisions, stale state, dead ends, and caches as
inference premises; the implemented protected evaluator reconstructs its closed
bundle from authoritative repositories.

**Implementation status:** snapshots, append/read behavior, typed projections,
conclusion frames, and validity supersession are **Implemented**. The complete
user-governed experience is **Partially implemented**.

SessionFrame purpose and user governance are owned by
[SessionFrame and active context](session-frame-and-active-context.md). Its
distinction from scientific evaluation remains owned by
[Protected evaluation context](protected-evaluation-context.md).

## Important non-FCO records and artifacts

Non-FCO does not mean unimportant. It means the record serves another layer and
must not be promoted into durable scientific knowledge.

### Workspace

`Workspace` is a filesystem and runtime boundary. It scopes local data,
artifacts, configuration, and persistence. It is not a research object and no
Workspace FCO is currently defined.

### Question

A Question is user input. The Planner may answer it from valid Discoveries or
turn it into proposed Tasks. Retaining the raw question does not give it
scientific authority.

### AnalysisFrame

`AnalysisFrame` is provenance for the exact data view used by an analysis. It
supports Evidence lineage but does not make a claim.

### ExecutionRun

`ExecutionRun` is attempt and workflow provenance: status, lease, fencing,
method identity, retries, and links. A failed run creates no Evidence.

### PlannerOperation

`PlannerOperation` is a durable pending mutation proposal. It allows Planner
nodes to propose and the commit boundary to materialize approved workflow
changes atomically. It is not the resulting FCO.

### GeneratedView

`GeneratedView` is a runtime answer, report, table, plot, or parent-task
synthesis derived from current valid state. It is not a Discovery and may need
regeneration. The complete generated-view product path is a **Design target**.

### EvidenceCacheEntry

`EvidenceCacheEntry` is optimization state for safe reuse. It must be keyed by
validity and must never author a Discovery. Persistent Evidence Cache is
**Deferred**.

### ValidityEvent

`ValidityEvent` is immutable governance and provenance for an authorized
invalidation or supersession transaction. It explains what changed and which
dependent effects committed. It does not replace the affected FCOs or become a
scientific claim.

Other approval, inbox, outbox, evaluation-control, decision, admission-claim,
and revision records likewise retain workflow, authority, or provenance roles.

## Cardinality rules and their purpose

```text
one terminal analytical Task
  <= one Hypothesis

one Hypothesis
  <= one Discovery

parent Task
  -> no Hypothesis
  -> no Discovery
```

“At most one” is intentional. A Task may never be approved or executed. An
execution may fail. Evaluation may produce a technical `EvaluationFailure`.
The user may reject or cancel a proposal. Those paths must not manufacture a
Hypothesis or Discovery just to satisfy a count.

When the chain does succeed, one terminal analytical Task binds to one
Hypothesis, and one Hypothesis can produce only one Discovery. Database
constraints and application guards prevent duplicates.

These rules stop several forms of ambiguity:

- two Hypotheses cannot silently claim to be the contract for one terminal
  Task;
- retries cannot create competing Discoveries for one Hypothesis;
- a parent Task cannot turn a multi-analysis summary into a claim with no
  single Evidence basis;
- supported, contradicted, inconclusive, and insufficient-evidence outcomes all
  use the same bounded lineage.

The cost is finer Task decomposition and generated parent-level views. That
cost makes the scientific unit of work explicit.

## Mutation and history

CogniEDA distinguishes immutable scientific content from lifecycle metadata.
Changing data or an observed result produces a new `DataProfile` or `Evidence`;
the old record is superseded or invalidated through an authorized path. A
Discovery's admitted scientific content is not edited to fit the new state.

Historical invalid or superseded records remain queryable for audit and
provenance. Active retrieval excludes them. This is how the system can answer
both “what did we conclude then?” and “what may we rely on now?” without making
either answer overwrite the other.

The complete lifecycle distinction is owned by
[Validity over time](validity-over-time.md).

The rationale for typed research state, the exact FCO boundary, bounded
cardinality, and historical retention is summarized in
[Design decisions and tradeoffs](design-decisions-and-tradeoffs.md) and
preserved in
[ADR-001: First-Class research state](decisions/ADR-001-first-class-research-state.md).

### Implementation orientation

The FCO schemas live under `src/schemas/research/`,
`src/schemas/evidence/`, and `src/schemas/discovery/`. Persistence constraints
are under `src/db/models/`; guarded writers are under `src/application/`; and
context projections are under `src/memory/`.
