# CogniEDA dependency-driven roadmap

> **Implementation status:** The Package 7 product-integration milestones are
> **Design target**. Later capability areas are explicitly **Design target**,
> **Deferred**, or **Unsupported** as stated below. This roadmap is neither an
> implementation history nor a commitment to speculative features.

The roadmap converts the current guarded in-process library into one coherent
product slice without weakening its authority, transaction, lifecycle, or
validity boundaries. [CogniEDA current state](current-state.md) owns what exists
today; the [capability and maturity map](capability-and-maturity-map.md) owns the
reader-facing comparison.

## Dependency rule

Work advances only when the next milestone can use the canonical owners already
present in source:

```text
protected in-process scientific foundation
  -> Package 7A: trusted identity, Analyst, and coherent configuration
  -> Package 7B: real observation-only Data Explorer
  -> Package 7C: restart-safe coordination and scoped continuity
  -> Package 7D: one persistent user-facing product slice
  -> later capabilities only at explicit scale or product triggers
```

Package 7A and Package 7B may be prepared independently where their interfaces
do not overlap. Package 7C depends on the concrete failure and recovery
semantics established by both. Package 7D depends on all three and must prove
their integration through the existing transaction owners.

## Protected foundation

The following boundaries are **Implemented**, with load-bearing durable
behavior **Verified on SQLite**:

- exactly eight FCOs and explicit non-FCO classifications;
- at-most-one Task-to-Hypothesis and Hypothesis-to-Discovery cardinality;
- parent Tasks producing neither Hypotheses nor Discoveries;
- observation-only Data Explorer output;
- atomic AnalysisFrame and Evidence admission;
- protected evaluation with Assumption and prior-Discovery exclusion;
- principal-bound authorization of an exact persisted proposal;
- exact proposal-copy and atomic Discovery admission;
- atomic validity propagation with historical retention and active exclusion;
- canonical application transaction owners and fail-closed unsupported paths.

Every roadmap milestone must preserve these boundaries. Product integration is
not permission to introduce a second scientific writer.

## Package 7 prerequisite classification

The classification describes why a prerequisite blocks the intended milestone,
not how inconvenient the current implementation is.

| Prerequisite | Classification | Owning milestone | Why it blocks that milestone |
| --- | --- | --- | --- |
| trusted local principal resolution | Product blocker | Package 7A | exact authority exists, but no deployment user can be resolved |
| production Hypothesis Analyst provider | Product blocker | Package 7A | protected evaluation has a model seam but no deployable provider policy |
| coherent model, tool, skill, and MCP configuration | Configuration blocker | Package 7A | checked-in model-backed configuration fails on undefined MCP references and absent tracked skills |
| fail-closed deployment startup | Operational blocker | Package 7A | a host must reject missing identity, provider, secrets, or capability definitions before work begins |
| explicit deployment-factory contract | Documentation dependency | Package 7A | the current loader only requires a callable returning the runtime; the host requirements are not yet a supported contract |
| concrete production Data Explorer | Product blocker | Package 7B | no real supported adapter can produce observations |
| real dataset and artifact access policy | Product blocker | Package 7B | protocol seams do not define supported input paths, output artifacts, or resource limits |
| observation and failure integration with registry/dispatcher | Structural blocker | Package 7B | the adapter must preserve observation-only authority and canonical Evidence admission |
| durable reconciliation loop | Operational blocker | Package 7C | reconciliation functions exist but no process owns repeated recovery |
| stranded `APPROVED` execution-approval handling | Structural blocker | Package 7C | retry after later admission failure lacks an explicit lawful transition |
| existing-Hypothesis retry or reuse policy | Structural blocker | Package 7C | the intended reuse path currently fails closed at lifecycle ownership |
| scoped SessionFrame selection and succession | Structural blocker | Package 7C | multiple sessions or Objectives cannot identify the correct current frame |
| process-local LangGraph checkpointing during adapter preparation | Acceptable local limitation | Packages 7A–7B | adapter work does not require arbitrary graph progress to survive restart |
| restart-safe reconstruction of included Planner interactions | Operational blocker | Package 7C | durable records cover bounded identities, but arbitrary graph progress is not restart-safe |
| Planner persistence composition | Acceptable local limitation | Package 7C | no scientific writer bypass exists; extract only where direct composition obstructs product recovery or scoping ownership |
| stale Planner route labels | Documentation dependency | Package 7C | labels can imply unavailable interaction paths and must match the supported slice |
| user-facing approval, review, result, and resume interaction | Product blocker | Package 7D | schemas and durable records alone do not let a user govern an investigation |
| workspace and SQLite lifecycle ownership | Operational blocker | Package 7D | the product must open, migrate, lock, recover, and close its durable state predictably |
| explicit unsupported-edge behavior | Documentation dependency | Package 7D | the product must not imply dataset cleaning, Graph Miner, cross-database, or distributed support |

Missing production identity and adapters are product blockers, not foundational
ontology defects. The stranded approval, existing-Hypothesis reuse, and
multi-session frame-selection issues are structural blockers for restart-safe
coordination because an incorrect resolution could violate lifecycle or
authority ownership.

## Package 7A — trusted local identity and Analyst adapters

**Current status:** **Design target**.

### Purpose

Provide the trusted local dependencies required to construct
`CogniEDARuntime` for real protected evaluation and exact user authority.

### Why it is needed

The runtime requires a principal resolver and Analyst model. Current protocols
and injected fakes prove their boundaries but do not identify a deployment
user, load provider credentials, or define a supported model policy. Checked-in
MCP and skill references are also unresolved.

### Prerequisites

- retain the existing `AuthenticatedPrincipalResolver` and protected Analyst
  contracts;
- select a bounded local deployment host and secret-loading policy;
- define the supported environment and database location; and
- inventory every configured worker, MCP server, skill, tool, and model
  dependency.

### Protected invariants

- governance binds an authenticated principal to one exact proposal and scope;
- the Hypothesis Analyst receives only the closed synthesis bundle;
- the Analyst has no tools or raw-data access;
- Assumptions, Tasks, existing Discoveries, SessionFrames, and chat remain
  outside protected synthesis; and
- missing or incoherent dependencies fail before scientific work begins.

### Required implementation outcomes

- one trusted local principal adapter with explicit identity and authorization
  semantics;
- one production Hypothesis Analyst provider adapter compatible with the
  protected typed-output contract;
- coherent model, tool, skill, and MCP configuration for every enabled worker;
- startup validation for provider credentials, MCP definitions, skill
  definitions, worker references, and database configuration; and
- a documented deployment-factory contract that assembles the runtime without
  adding authority.

### Non-goals

- no product command or HTTP design merely to demonstrate adapter construction;
- no Data Explorer implementation;
- no broad Planner completion;
- no semantic retrieval, Graph Miner, or Evidence cache; and
- no change to scientific schemas or transaction owners.

### Known risks

- a local identity shortcut could become an unauthenticated global principal;
- provider middleware could capture or enrich the protected bundle;
- tool configuration could accidentally give the Analyst execution access; and
- startup fallback could silently substitute missing capabilities.

### Exit criteria

- a deployment-supplied factory constructs the runtime with a real local
  principal resolver and configured Analyst provider;
- startup rejects missing, ambiguous, or inconsistent identity, model, MCP,
  skill, and worker configuration before accepting a request;
- protected evaluation produces either the existing typed proposal or typed
  failure without tools or raw data;
- governance decisions remain principal-, scope-, expiry-, and
  proposal-fingerprint-bound; and
- explicit unsupported capabilities remain unavailable rather than falling
  back to fixtures or placeholders.

### Dependencies

Depends only on the protected in-process foundation. Its stable principal and
Analyst interfaces are prerequisites for Packages 7C and 7D.

### What becomes possible afterward

The product host can identify a real local user and run protected scientific
evaluation through a deployable provider. Execution still cannot analyze a real
dataset until Package 7B.

## Package 7B — Concrete Data Explorer

**Current status:** **Design target**.

### Purpose

Provide one real, registered, observation-only Data Explorer over a bounded
supported dataset path.

### Why it is needed

Execution approvals, attempts, dispatcher, result receiver, and Evidence
admission exist, but the repository has no production adapter that performs a
real method and returns typed observations.

### Prerequisites

- retain the current `DataExplorerResult`,
  `AnalysisFrameObservation`, and `EvidenceObservation` contracts;
- choose the initial dataset format, method set, artifact directory, and
  resource policy;
- define how an accepted DataProfile binds to the physical dataset version; and
- define deterministic method, parameter, artifact, and failure capture.

### Protected invariants

- the Data Explorer observes but does not interpret, authorize, or persist;
- one runtime registers exactly one explicit Data Explorer identity and factory;
- output is bound to the approved execution contract and durable attempt;
- only Evidence admission materializes AnalysisFrame and Evidence; and
- technical or validation failure creates no Discovery.

### Required implementation outcomes

- one concrete adapter that reads a real supported dataset version;
- at least one bounded analytical method with deterministic parameter handling;
- typed AnalysisFrame and Evidence observations with artifact references and
  failure detail;
- registry and dispatcher integration through the existing runtime;
- resource, path, artifact-integrity, and unsupported-method controls; and
- explicit retry-safe behavior for external effects.

### Non-goals

- no scientific claim wording;
- no direct repository writes from the adapter;
- no generalized plugin marketplace or arbitrary code execution;
- no Graph Miner; and
- no governed cleaning or DVC workflow unless separately approved later.

### Known risks

- adapter output could smuggle interpretation into observations;
- physical data may drift from the accepted DataProfile;
- artifact writes can occur outside the SQLite transaction;
- retries can duplicate external effects; and
- an overly broad method runner can bypass resource or path controls.

### Exit criteria

- one concrete registered Data Explorer produces typed AnalysisFrame and
  Evidence observations from a real supported dataset path without authoring
  interpretation;
- unsupported methods, invalid paths, changed profile bindings, resource
  breaches, and malformed observations fail explicitly;
- the dispatcher uses durable execution identity and the result receiver
  preserves replay and changed-payload conflict behavior;
- Evidence appears only through the canonical atomic admission owner; and
- failure leaves no partial AnalysisFrame, Evidence, or Discovery state.

### Dependencies

Depends on the protected execution and Evidence contracts. It can be developed
alongside Package 7A, but Package 7C must coordinate its real failure and retry
semantics.

### What becomes possible afterward

The library can perform one real approved analysis and admit immutable
observation-bound Evidence. It still lacks a restart owner and supported user
journey.

## Package 7C — restart-safe in-process coordination

**Current status:** **Design target**.

### Purpose

Make the bounded local workflow recoverable after process loss and correctly
scoped across the user, Objective, session, and active frame.

### Why it is needed

Durable approvals, runs, outbox/inbox records, evaluations, and admission claims
exist, but no loop owns their reconciliation. LangGraph uses process-local
checkpointing. Known approval, Hypothesis-reuse, and SessionFrame-selection
edges prevent a trustworthy restart contract.

### Prerequisites

- Package 7A identity and Analyst failure semantics;
- Package 7B Data Explorer dispatch, external-effect, and retry semantics;
- an explicit single-process ownership model for polling and reconciliation;
- a decision for existing-Hypothesis reuse versus lawful successor creation;
  and
- a scoping key for workspace, user, Objective, session, and frame selection.

### Protected invariants

- every retry preserves exact contract and authority binding;
- one eligible Task has at most one Hypothesis and one Hypothesis at most one
  Discovery;
- only canonical application services own scientific transactions;
- stale claims or leases cannot commit;
- frame selection cannot make invalid state active; and
- recovery either commits exactly once or records an explicit controlled
  terminal outcome.

### Required implementation outcomes

- a durable in-process reconciliation loop for pending dispatch, result
  finalization, evaluation, governance admission, and startup recovery;
- explicit handling for execution approvals left `APPROVED` after admission
  failure;
- an implemented and tested existing-Hypothesis retry/reuse or successor
  decision;
- user-, Objective-, session-, and branch-appropriate SessionFrame selection
  and Objective frame succession;
- durable reconstruction for every interaction included in Package 7D;
- Planner application-boundary extraction where direct persistence composition
  obstructs ownership, scoping, or retry; and
- route names and controlled failures aligned with the supported slice.

### Non-goals

- no distributed worker topology;
- no cross-database portability;
- no full completion of every Planner branch;
- no semantic retrieval or multi-user collaboration; and
- no silent auto-repair of changed scientific contracts.

### Known risks

- reconciliation ordering can duplicate or skip external work;
- retry may create an illegal second Hypothesis or reuse a changed contract;
- frame scoping migration can select the wrong predecessor;
- a durable graph checkpoint can conflict with repository-authoritative records;
  and
- facade extraction can accidentally relocate transaction ownership.

### Exit criteria

- every durable approval used by the product slice can be reconstructed after
  restart, is scoped to the correct workspace, user, Objective, and session,
  and either commits exactly once through its canonical owner or reaches an
  explicit terminal failure;
- pending execution, inbox finalization, evaluation, proposal decision, and
  Discovery admission are reconciled without manual database mutation;
- stranded `APPROVED` and existing-Hypothesis cases have explicit lawful
  outcomes and exact replay behavior;
- SessionFrame selection and Objective succession never depend on an unrelated
  database-global latest frame; and
- process loss at each durable boundary preserves authority, fencing, and
  historical state.

### Dependencies

Depends on the concrete identity/Analyst and Data Explorer behaviors from
Packages 7A and 7B. Package 7D depends on this recovery contract.

### What becomes possible afterward

A local host can coordinate one durable governed workflow through restart
without relying on test orchestration or manual reconciliation.

## Package 7D — persistent end-to-end product slice

**Current status:** **Design target**.

### Purpose

Expose one supported local product journey from user request to a visible,
evidence-bound outcome.

### Why it is needed

Library calls prove the scientific spine but do not define a product contract.
A coherent slice is required to validate workspace lifecycle, user
interactions, output delivery, recovery, and explicit unsupported edges
together.

### Prerequisites

- Package 7A trusted identity, Analyst, and coherent configuration;
- Package 7B concrete Data Explorer and real dataset binding;
- Package 7C restart-safe coordination and scoped continuity;
- a selected bounded local interface with security and operational ownership;
  and
- explicit support and compatibility policies for the first slice.

### Protected invariants

- proposed Tasks and execution contracts require exact user approval;
- proposed Tasks do not execute;
- Data Explorer remains observation-only;
- protected evaluation excludes Assumptions and existing Discoveries;
- governance cannot author or rewrite scientific wording;
- Discovery admission copies the exact authorized proposal atomically;
- invalid state remains historical and inactive; and
- unsupported operations fail visibly without fabricating success.

### Required implementation outcomes

- workspace and SQLite open, initialization, migration, lock, and close
  lifecycle;
- a typed user request and selected Planner path;
- Task proposal and approval;
- execution proposal and approval;
- real Data Explorer dispatch and result receipt;
- atomic Evidence admission;
- protected evaluation and principal-bound governance;
- atomic Discovery admission and a user-visible result;
- restart and resume at every included durable interaction; and
- explicit behavior for unsupported answer, cleaning, Graph Miner, portability,
  and distributed edges.

### Non-goals

- no claim of a complete analytical workbench;
- no requirement to expose every Planner route;
- no multi-user service or distributed worker;
- no semantic/vector retrieval;
- no cross-workspace import/export; and
- no mutation of DataProfile, Evidence, or admitted Discovery payloads.

### Known risks

- interface handlers can become alternate transaction owners;
- convenience shortcuts can bypass approval or exact-proposal binding;
- product wording can blur Evidence, proposal, Discovery, and generated
  presentation;
- restart UX can conceal failed or stale state; and
- unbounded scope can turn a coherent slice into an unsupported platform claim.

### Exit criteria

- one documented user journey opens a persistent workspace, accepts a request,
  approves a Task and execution, performs real Data Explorer work, admits
  Evidence, runs protected evaluation, records governance, admits a Discovery,
  and displays the result;
- stopping and restarting at each durable boundary resumes the same scoped
  workflow or reports an explicit terminal failure;
- all writes pass through the canonical application owner and retain exact
  proposal, contract, replay, fencing, and validity semantics;
- the interface visibly distinguishes proposal, approval, Evidence,
  interpretation, authorized Discovery, failure, and invalidated history; and
- every adjacent unsupported edge is documented and fails closed.

### Dependencies

Depends on Packages 7A, 7B, and 7C. It is the prerequisite for judging later
scale, reporting, portability, and distributed-operation needs from actual
product evidence.

### What becomes possible afterward

CogniEDA has one supported local product contract. Later work can be triggered
by observed user, data, retrieval, and deployment needs rather than by
speculation.

## Later capability disposition

Later areas retain their existing architectural meaning. They receive no new
package number here.

| Capability area | Status | Dependency and revisit trigger |
| --- | --- | --- |
| governed cleaning and executable DVC integration | **Design target** | after the product slice proves dataset lifecycle; revisit when a supported transformation must create a new dataset version and DataProfile |
| parent-Task `GeneratedView` and reporting | **Design target** | after valid child Discoveries can be selected in a product; revisit when users need regenerable synthesis that is not scientific authority |
| Graph Miner and semantic/hybrid retrieval | **Deferred** | after scoped lexical retrieval is measured; revisit when candidate volume, recall, lineage traversal, or latency exceeds the bounded repository path |
| persistent semantic-index invalidation | **Deferred** | depends on a persistent semantic index; authority filtering must precede or invalidate index use |
| SessionFrame branching and multi-user governance | **Deferred** | after the local scoped model is proven; revisit when concurrent users or research branches require explicit heads and policy |
| Evidence cache | **Deferred** | after concrete execution cost and validity keys are known; a cache can reuse observations but cannot author Discovery |
| PostgreSQL or remote database support | **Deferred** | after a product topology requires it; every lock, trigger, claim, replay, and transaction owner must be reverified |
| distributed execution and validity processing | **Deferred** | after local restart-safe coordination and external-effect idempotency are proven |
| cross-workspace import/export | **Unsupported** | no supported contract exists; reconsider only with explicit identity, provenance, namespace, validity, and conflict policy |

## Later milestone — governed data evolution and generated views

**Current status:** **Design target**.

### Purpose

Support approved physical data change and regenerable presentation without
mutating scientific records or manufacturing parent-level claims.

### Why it is needed

Real product use will eventually require cleaning, derived dataset versions,
plots, reports, and parent-Task summaries.

### Prerequisites

- the Package 7D dataset, artifact, identity, and interaction contracts;
- an immutable dataset-version identity and accepted DataProfile lifecycle; and
- a GeneratedView contract that depends only on current authoritative inputs.

### Protected invariants

- cleaning creates a new dataset version and DataProfile;
- DataProfile and Evidence payloads are not edited in place;
- GeneratedView is presentation, not an FCO, Evidence, or Discovery; and
- parent Tasks still produce neither Hypotheses nor Discoveries.

### Required implementation outcomes

- approval and provenance for supported transformations;
- executable DVC or another explicitly selected version adapter;
- new-profile activation and prior-profile lifecycle handling;
- GeneratedView inputs, regeneration, staleness, and artifact provenance; and
- user-visible distinction between claim and presentation.

### Non-goals

- no automatic claim rewriting;
- no parent-Task Discovery synthesis;
- no ungoverned arbitrary transformation; and
- no cross-workspace exchange.

### Known risks

- transformation tools can overwrite source data;
- generated prose can be mistaken for a Discovery;
- stale views can outlive invalid inputs; and
- artifact identity can drift from research-state provenance.

### Exit criteria

- every supported transformation preserves the prior version and creates a new
  DataProfile with complete provenance;
- every GeneratedView is reproducible from current eligible inputs, becomes
  stale when those inputs lose authority, and cannot enter protected synthesis
  as Evidence or Discovery; and
- parent-Task reporting never creates a synthetic Hypothesis or Discovery.

### Dependencies

Depends on Package 7D. It does not block the first product slice.

### What becomes possible afterward

Users can evolve data and present current knowledge without weakening
append-oriented scientific truth.

## Later milestone — retrieval and continuity scaling

**Current status:** **Deferred**.

### Purpose

Improve recall, lineage navigation, context governance, and performance after
the bounded lexical path reaches measured limits.

### Why it is needed

Lexical ranking and database-global legacy frame behavior will not serve every
large, branched, or multi-user investigation.

### Prerequisites

- Package 7D telemetry and retrieval-quality evidence;
- scoped SessionFrame identities from Package 7C;
- an explicit semantic index authority and invalidation model; and
- branch and multi-user governance policy.

### Protected invariants

- lifecycle and context-role admission precede relevance ranking;
- semantic similarity cannot restore invalid authority;
- Assumptions remain excluded from conclusion synthesis;
- pins cannot reactivate invalid state; and
- a SessionFrame remains context selection, not scientific truth.

### Required implementation outcomes

- measured lexical baseline and acceptance metrics;
- authority-first semantic or hybrid retrieval where justified;
- Graph Miner lineage traversal with explicit typed outputs;
- persistent-index invalidation and rebuild policy if an index is adopted; and
- branch/user frame selection, succession, and conflict governance when
  required.

### Non-goals

- no vector store as canonical memory;
- no retrieval result as scientific authority;
- no semantic implementation before measured need; and
- no implicit cross-workspace knowledge.

### Known risks

- approximate ranking can hide relevant current Evidence;
- stale indexes can return invalid candidates;
- multi-user pin and branch policy can conflict; and
- Graph Miner can become an alternate inference engine.

### Exit criteria

- retrieval quality and latency improve against a documented corpus without
  weakening lifecycle, profile, role, or operation-scope admission;
- index invalidation prevents inactive state from being returned as current;
- Graph Miner outputs remain retrieval or lineage views rather than claims; and
- concurrent frame selection has explicit ownership, replay, and conflict
  behavior.

### Dependencies

Depends on the local product slice and measured scale triggers. It may depend on
governed data evolution if profile lineages become larger.

### What becomes possible afterward

Larger or branched investigations can reconstruct relevant current context
without treating semantic similarity as authority.

## Later milestone — backend portability and distributed operation

**Current status:** **Deferred**.

### Purpose

Support another database or distributed execution only when the proven local
product topology requires it.

### Why it is needed

Remote persistence, multiple writers, or distributed workers change the
locking, failure, idempotency, and operational assumptions currently verified
only on SQLite.

### Prerequisites

- Package 7C local restart semantics and Package 7D operational evidence;
- explicit service, worker, and database topology;
- an immutable migration revision policy;
- external-effect idempotency and message-delivery contracts; and
- a backend-specific verification plan for every transaction owner.

### Protected invariants

- exact proposal and contract binding;
- canonical transaction ownership;
- complete atomic effects or explicit compensating state;
- lease and fencing safety;
- deterministic replay versus changed-input conflict; and
- historical retention with active invalidation.

### Required implementation outcomes

- backend-specific schema, migration, lock, claim, trigger, and isolation
  semantics;
- crash and retry policy across process and network boundaries;
- observable worker ownership and reconciliation;
- compatibility and upgrade policy; and
- requalification of every scientific admission and validity path.

### Non-goals

- no claim of database independence from SQLModel abstractions alone;
- no distributed topology without product evidence;
- no silent weakening of all-or-nothing scientific effects; and
- no cross-workspace import/export by implication.

### Known risks

- different isolation semantics can admit duplicate or partial scientific
  state;
- message delivery can race database commits;
- online migrations can violate historical compatibility; and
- operational credentials can bypass application guards.

### Exit criteria

- every canonical transaction owner has backend-specific atomicity,
  concurrency, rollback, replay, and crash evidence;
- migrations have immutable identities and fail closed across supported
  historical states;
- stale workers cannot commit after lease loss;
- external effects are idempotent or explicitly reconciled; and
- documentation names the exact supported topology rather than claiming broad
  portability.

### Dependencies

Depends on a proven local product and an explicit trigger such as remote
service operation, multiple writers, or distributed workers. It is not a
prerequisite for Package 7.

### What becomes possible afterward

CogniEDA can support the specifically qualified remote or distributed topology
without extrapolating SQLite evidence.

## Roadmap-wide non-negotiable boundaries

No roadmap work may:

- introduce a ninth FCO;
- make `Workspace`, `Question`, `AnalysisFrame`, `GeneratedView`,
  `PlannerOperation`, `ExecutionRun`, cache, or validity records scientific
  knowledge;
- execute a proposed or ineligible Task;
- permit a parent Task to produce a Hypothesis or Discovery;
- allow Assumptions, prior Discoveries, raw chat, or unverified views into
  protected synthesis;
- let Data Explorer evaluate or persist;
- let the Analyst authorize its own proposal;
- let governance author or rewrite scientific wording;
- create alternate writers for Evidence, Discovery, or validity effects;
- let pins, ranking, caches, or semantic similarity restore invalid authority;
  or
- overwrite a DataProfile or Evidence when data or observations change.

These boundaries are the acceptance conditions for every future milestone, not
optional implementation preferences.
