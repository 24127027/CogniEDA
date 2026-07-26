# Investigation lifecycle

This page follows one investigation from research intent to durable,
evidence-bound knowledge. It distinguishes the conceptual architecture from the
current product maturity: the guarded in-process scientific spine is
implemented, while several user-facing Planner, dataset, worker, and resume
surfaces remain partial or unsupported.

The running question is:

> Within the 2025 small-business subscription cohort, is longer first-response
> time associated with 90-day churn?

The execution-through-admission portion is expanded in
[Execution to Discovery](../scientific-lifecycle/execution-to-discovery.md). Its three
load-bearing mechanisms are owned by
[Scientific authority](../scientific-lifecycle/scientific-authority.md),
[Protected evaluation](../scientific-lifecycle/protected-evaluation.md), and
[Discovery governance and admission](../scientific-lifecycle/discovery-governance-and-admission.md).

## The whole path

```text
user research intent
  -> Objective
  -> Task proposal
  -> Task decomposition
  -> terminal analytical Task
  -> Hypothesis
  -> prepared execution
  -> AnalysisFrame and ExecutionRun provenance
  -> Evidence
  -> protected evaluation
  -> DiscoveryProposal or EvaluationFailure
  -> governance
  -> atomic Discovery admission
  -> SessionFrame update
  -> active retrieval
  -> later validity propagation
```

The path is a sequence of authority changes, not a conveyor belt that turns all
input into knowledge. At several points, the safe outcome is to stop without
creating a downstream object.

## 1. Research intent becomes an Objective

The user's question expresses immediate intent. The broader project Objective
might be:

> Identify actionable drivers of 90-day churn for the 2025 small-business
> subscription cohort.

The Objective gives the project a durable direction without pretending that its
statement is evidence. It can guide planning and retrieval while remaining
separate from every later analytical result.

**User control:** Objective creation and revision are governed decisions on the
supported Planner path.

**Durable state:** the Objective and, for updates, revision provenance.

**Current status:** Objective proposal and approved mutation paths are
**Implemented**. A complete project-open and project-close product workflow is
**Partially implemented**.

## 2. The Planner proposes Tasks rather than silently creating work

The Objective is too broad for one scientific claim. The Planner may propose a
parent Task such as “investigate churn drivers,” then propose analytical
children for response time, pricing changes, and onboarding behavior.

The proposal is durable workflow state before it becomes active work. The user
reviews the exact ordered operation batch. Approval commits the proposed Task
changes and a successor SessionFrame; rejection leaves no active Task created
from that proposal.

**User control:** approve, cancel, revise, or clarify the exact Task proposal.

**Scientific authority:** none. Task wording and motivation organize work; they
are not empirical premises.

**Durable state:** pending `PlannerOperation` records, their decision state, the
approved Tasks, and an updated context snapshot.

**Current status:** configured request understanding, `/manage_task`, bounded
decomposition, durable proposal approval, and commit are **Implemented** for
the covered paths. General suggestion, answerability, review, pause, and other
natural-language branches are **Partially implemented**.

## 3. Decomposition identifies one terminal analytical Task

One child becomes the scientific unit of work:

> Test the association between first-response time and 90-day churn for the
> accepted 2025 small-business DataProfile, using the approved variables,
> method, parameters, and decision rule.

This Task is terminal because it has no children. It is analytical because it
contains a complete analytical specification. A parent Task cannot execute and
cannot generate a Hypothesis or Discovery.

Discoveries retrieved during planning may motivate the Task, but an existing
Discovery still cannot enter the protected inference context for the new claim.
Assumptions may also help the Planner decide which Tasks are useful. They do not
become part of the test's Evidence.

**User control:** approve the exact decomposition and child Task contracts.

**Durable state:** child Tasks, dependency and motivation links, and the
successor SessionFrame.

## 4. An approved execution contract binds one Hypothesis

The Planner prepares an execution contract from the active terminal Task and
accepted DataProfile. It binds:

- the response-time and churn variables;
- the cohort scope;
- the validation method and parameters;
- the decision rule;
- the expected Evidence;
- a deterministic seed when required;
- the configured Data Explorer identity.

Preparing the contract does not authorize execution. The user must approve its
exact fingerprint. At commit, the application revalidates the Task, DataProfile,
contract, session binding, and approval state. On the supported fresh-admission
path it then creates the one Hypothesis allowed for that Task and admits an
execution attempt. An attempted reuse of an existing nonterminal Hypothesis
currently fails closed at lifecycle ownership and remains a **Known deviation**.

**User control:** approve or cancel the exact execution contract. Changed
content needs a new approval.

**Scientific authority:** the Hypothesis defines the test contract but does not
claim an outcome.

**Durable state:** execution approval, Hypothesis, ExecutionRun, and dispatch
outbox.

**Current status:** this approval-gated in-process path is **Implemented** and
its persistence behavior is **Verified on SQLite**. It is a
**Known deviation** that the Planner currently authors the operational
contract; the preferred long-term design gives scientific operationalization
to the Hypothesis Analyst.

## 5. Data Explorer observes; provenance records what happened

A worker-like caller claims the durable outbox with an owner and fencing epoch.
The application reconstructs the prepared contract from durable Task,
Hypothesis, DataProfile, run, and outbox state. It invokes exactly one configured
Data Explorer adapter.

The Data Explorer can return:

- an `AnalysisFrameObservation` describing the data view;
- an `EvidenceObservation` describing the observed result;
- execution details and bounded diagnostics;

or a typed technical failure.

It cannot evaluate the Hypothesis, author Discovery wording, record a
governance decision, or persist research state.

`ExecutionRun` records which attempt ran. `AnalysisFrame` records the exact data
view. Both are provenance, not FCOs and not conclusions.

**Scientific authority:** Data Explorer has observation authority only.

**Durable state:** the authoritative result inbox and attempt status. A
technical failure is durable execution history but creates no Evidence.

**Current status:** contracts, registry, dispatch, receipt, retry, and recovery
are **Implemented**. A concrete production Data Explorer and worker process are
**Unsupported**.

## 6. Evidence admission materializes the observation atomically

For a technically successful result, the recovery finalizer validates:

- Task, Hypothesis, and DataProfile lineage;
- the approved method and parameters;
- attempt identity, lease epoch, and result digest;
- the authoritative inbox and outbox;
- deterministic AnalysisFrame and Evidence identities.

One transaction then creates the AnalysisFrame and immutable Evidence, advances
the ExecutionRun to evidence admitted, advances the Hypothesis to ready for
evaluation, and consumes the inbox.

Evidence admission deliberately stops there. The Task remains active. No
Discovery exists.

**Scientific authority:** the application materializes exactly what the
observation contract permits; it does not interpret the result.

**Durable state:** AnalysisFrame, Evidence, updated ExecutionRun and Hypothesis,
and consumed inbox state.

**Current status:** **Implemented** and **Verified on SQLite**, including exact
replay, conflict quarantine, fencing, and rollback.

## 7. Protected evaluation changes observation into a proposal

The application reconstructs a closed `DiscoverySynthesisBundle` from durable
repositories. It includes:

- the Hypothesis contract;
- safe metadata for the active accepted DataProfile;
- AnalysisFrame and ExecutionRun provenance;
- the complete active Evidence set;
- method parameters, decision rule, limitations, invalidators, and digests.

It has no field for Assumptions, Tasks, prior Discoveries, SessionFrames, user
decisions, chat history, GeneratedViews, caches, raw data, files, or generic
context. The Hypothesis Analyst receives only that bundle, with no tools and no
message history.

The Analyst returns one of two lifecycle-distinct results:

- `DiscoveryProposal`: a structured scientific proposal;
- `EvaluationFailure`: a typed reason the evaluation could not produce a valid
  proposal.

An EvaluationFailure is not an inconclusive scientific result. It represents a
technical or contract failure and produces no Discovery.

**Scientific authority:** Hypothesis Analyst alone authors proposal wording.
It has no decision or persistence authority.

**Durable state:** evaluation control, bundle identity, and either the exact
proposal or the typed failure.

**Current status:** protected evaluation is **Implemented**. A deployment must
supply the model provider; no default production adapter is included.

## 8. Scientific outcomes keep their limited meaning

The same lineage can yield four proposal outcomes:

### Supported

The Evidence meets the approved decision rule in the direction of the
Hypothesis. The proposal states the supported association only within the
tested cohort, method, and uncertainty.

### Contradicted

The Evidence supports an outcome that conflicts with the Hypothesis as stated.
The Discovery records that contradiction; it does not erase the Hypothesis or
rewrite prior Assumptions.

### Inconclusive

The observed result does not permit a stable directional interpretation under
the contract. The proposal records the inconclusive outcome and its
limitations.

### Insufficient evidence

The Evidence is not sufficient to establish the proposed relationship under
the stated decision rule. In the running example, the correct wording is:

> Available Evidence is insufficient to establish an association between
> first-response time and 90-day churn within the 2025 small-business cohort
> using the approved method and decision rule.

It is not:

> There is no relationship between response time and churn.

All four are legitimate knowledge outcomes when they are expressed with their
scope and validity basis. None bypasses governance.

## 9. Governance authorizes the exact proposal

An authenticated principal receives an expiring authority bound to the
workspace, session, purpose, and operation. Governance reconstructs the current
proposal and protected bundle, then records one exact outcome:

- approved;
- rejected;
- cancelled.

There is no “modify and admit” shortcut. Changing scientific wording requires a
new valid proposal and a new decision.

**User control:** the user approves, rejects, or cancels the exact proposal.

**Scientific authority:** governance decides whether the proposal may be
admitted. It does not author or materialize the claim.

**Durable state:** immutable authority and decision records bound to the exact
proposal and principal.

**Current status:** governance services are **Implemented** and
**Verified on SQLite**. A production authentication implementation is
**Unsupported** and must be supplied by deployment composition.

## 10. Atomic admission creates the Discovery chain

Approval still does not create scientific truth. Atomic Discovery admission
reloads the current Evaluation, decision, authority, Hypothesis, terminal Task,
DataProfile, AnalysisFrames, ExecutionRuns, and active Evidence. Under the
SQLite writer lock, it rebuilds the protected bundle and verifies that nothing
material changed.

One transaction then:

1. copies the proposal's scientific content exactly into a new Discovery;
2. creates a deterministic conclusion SessionFrame;
3. moves the Hypothesis to evaluated;
4. completes the terminal analytical Task;
5. commits the evaluation and admission claim;
6. consumes the exact proposal decision.

If any step fails, the transaction rolls back. Exact replay returns the
committed chain; changed content conflicts.

**Scientific authority:** the application materializes exactly. It does not
rewrite the claim.

**Durable state:** Discovery, conclusion SessionFrame, terminal lifecycle
transitions, committed admission claim, and consumed decision.

**Current status:** **Implemented** and **Verified on SQLite**.

## 11. SessionFrame exposes user-governed active context without becoming authority

The conclusion frame points to the admitted Discovery and supporting Evidence,
records the Objective snapshot and warnings, and contains no active
Assumptions. Later planning or answering can select an active frame and build a
mode-specific projection.

This does not mean the SessionFrame authored the conclusion. Protected
evaluation used the repository-built bundle directly. The frame exists for
continuity, inspection, pinning, exclusion, and handoff. User-directed context
changes create an appended successor snapshot rather than rewriting the
selected content of the earlier frame. The frame and its pins are not
scientific premises; selected objects remain governed by their own epistemic
types.

**User control:** users can govern proposals and can express pins or exclusions
in frame state. A complete interactive frame-governance and resume experience
is not yet present.

**Current status:** append/read snapshots, conclusion frames, and typed
projections are **Implemented**; the user-facing experience is
**Partially implemented**.

See [SessionFrame and active context](../context/session-frame.md) for
snapshot, pin, exclusion, and authority semantics.

## 12. Active retrieval uses validity before relevance

The new Discovery may be retrieved for planning when its lifecycle is active.
Structural relations, explicit pins and exclusions, DataProfile compatibility,
and bounded lexical relevance affect ranking. Current answer policy exists, but
the Planner answer path remains **Partially implemented**.

Invalidated or deprecated Discoveries are excluded even when pinned. A flagged
or cross-profile Discovery may be relevant for review but cannot silently
motivate new work. Cross-profile state is currently ranked as warned
context-only material rather than removed before ranking, and independent
operation-scope filtering is a **Known deviation**.

**Durable state:** retrieval itself creates none.

**Current status:** bounded relational candidate selection and deterministic
lexical scoring are **Implemented**. Graph Miner and a persistent
semantic/vector index are **Deferred**.

See [Context type safety and retrieval](../context/context-type-safety.md)
for the source-grounded pipeline and invariant classifications.

## 13. Validity propagation keeps history but removes authority

Suppose the team later learns that the AnalysisFrame used an incorrect 2025
small-business cohort filter. An authorized validity command identifies the
source, expected state, immutable-core fingerprint, reason, scope, and
idempotency key.

The validity service discovers dependents and atomically records the source
transition, dependent effects, and immutable ValidityEvent. The Evidence and
Discovery remain historical, but the Discovery is no longer eligible for
active retrieval. Affected SessionFrames become superseded, and related Tasks
receive review signals.

Before Discovery admission, source loss can return a ready Hypothesis to
awaiting additional Evidence. After admission, validity loss does not rewrite
the old claim as if it had never existed.

**User control:** user-governed validity commands require the exact
authenticated principal and authority; trusted internal producers are narrowly
allow-listed.

**Current status:** the supported event matrix is **Implemented** and
**Verified on SQLite**. Production authority issuance and cross-database or
distributed propagation are **Unsupported**.

The full temporal-authority rationale and transaction mechanics are
[Validity over time](../validity/validity-over-time.md) and
[Atomic validity propagation](../validity/validity-propagation.md).

## Where assumptions are allowed

| Stage | Assumptions allowed? | Reason |
| --- | --- | --- |
| Task planning and decomposition | yes | provisional beliefs can help decide what to investigate |
| execution contract | no inference authority | the contract must bind explicit variables, scope, method, and data |
| Data Explorer input | no | observation must not be steered by planning beliefs |
| Evidence | no | Evidence records observed output |
| protected evaluation | no | the closed bundle structurally excludes Assumptions |
| Discovery admission | no | the exact proposal must be justified by active Evidence |
| post-Discovery review | comparison only | contradiction can be flagged without rewriting either object |

## Authority handoff

| Boundary | Authority | Explicitly forbidden |
| --- | --- | --- |
| Planner | propose and stage governed workflow | Evidence or Discovery creation |
| user approval | authorize exact Task or execution proposal | change the proposal invisibly |
| Data Explorer | observe approved analysis | evaluate or persist |
| Evidence admission | materialize validated observation | author a claim |
| Hypothesis Analyst | evaluate protected Evidence and author proposal | decide or persist |
| governance | approve, reject, or cancel exact proposal | rewrite or materialize |
| Discovery admission | verify and copy exactly in one transaction | invent scientific wording |
| validity service | remove active authority through governed propagation | delete historical truth |

## Why parent Tasks end in GeneratedViews

The parent “investigate churn drivers” Task may have several child Discoveries.
No single Hypothesis or Evidence set justifies a combined parent claim. The
parent answer therefore belongs in a `GeneratedView`: a current presentation
assembled from valid child Discoveries.

The view may need regeneration after invalidation and cannot be cited as a
Discovery. This is the price of preserving the lineage of each underlying
claim. `GeneratedView` and the complete Planner answer path remain a
**Design target** / **Partially implemented** area; current source does not
provide a complete user-facing generated-view workflow.

The reconstruction and parent-answer boundary is owned by
[Context continuity and resume](../context/continuity-and-resume.md).

### Implementation orientation

The current path is distributed across `src/agents/planner/`,
`src/agents/executor/`, `src/application/`, `src/memory/`, and their canonical
schemas and repositories. The end-to-end behavioral proof is under
`tests/e2e/`, with focused authority and transaction tests under
`tests/application/`.
