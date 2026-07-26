# Design decisions and tradeoffs

CogniEDA is validity-preserving research-state infrastructure. Its architecture
is evaluated in this order:

1. conclusion validity and traceability;
2. context type safety; and
3. multi-session project continuity.

This page is the canonical entry point for the reasoning behind that
architecture. It explains why the core epistemic boundaries exist, what they
cost, where current source only partially realizes them, and what a future
redesign must preserve. Concept pages remain the owners of detailed behavior;
the ADRs preserve the identity of individual decisions.

> **Implementation status:** The guarded research-state, scientific-authority,
> protected-evaluation, Discovery-admission, validity, retrieval, and
> SessionFrame seams described here are **Implemented** or **Partially
> implemented** as identified per decision. Transaction and concurrency claims
> are **Verified on SQLite** only. Operational backend, runtime, deployment, and
> scaling choices are **Deferred** to Phase 3B.

## How CogniEDA classifies a decision

| Classification | Meaning | What a redesign may do |
| --- | --- | --- |
| Foundational invariant | A rule that protects the core validity thesis | change its implementation, not silently remove its protection |
| Durable architectural decision | A boundary expected to survive major product evolution | replace mechanisms while preserving authority and failure semantics |
| Current-stage implementation choice | A reasonable local mechanism rather than part of the epistemic thesis | replace it when scale, portability, or product needs justify the cost |
| Known temporary deviation | Source differs from the preferred long-term boundary without creating a supported authority bypass | keep it explicit and remove it through dedicated work |
| Deferred design decision | The project has not yet selected or implemented the complete design | do not present a possible solution as current behavior |
| Unsupported future possibility | A conceivable direction with no current commitment or supported path | require a new decision before relying on it |

Current-state claims use the shared vocabulary defined in
[the documentation index](index.md#implementation-status-vocabulary). An ADR
records why a boundary exists; source and tests determine whether that boundary
is implemented.

## How source conformance is reported

| Class | Meaning |
| --- | --- |
| A | Implemented and enforced on the supported path |
| B | Implemented, but enforcement is incomplete |
| C | Partially implemented |
| D | Design target only |
| E | Contradicted by supported source |

An E-class finding against a foundational invariant requires a dedicated source
patch. Documentation must not redefine the decision to legitimize the defect.

## Decision map

| Decision | Decision classification | Current status | Source class | Canonical concept owner |
| --- | --- | --- | --- | --- |
| typed research state instead of conversation history | Foundational invariant | **Implemented** | A | [Research-state model](research-state-model.md) |
| exactly eight First-Class Objects | Foundational invariant | **Implemented** | A | [Research-state model](research-state-model.md) |
| Workspace outside the FCO graph | Durable architectural decision | **Implemented** | A | [Research-state model](research-state-model.md#important-non-fco-records-and-artifacts) |
| immutable DataProfile identity | Foundational invariant | **Implemented** with an under-enforced storage boundary | B | [Research-state model](research-state-model.md#dataprofile-immutable-dataset-state) |
| Assumption quarantine | Foundational invariant | **Implemented** | A | [Protected evaluation context](protected-evaluation-context.md#assumption-quarantine) |
| Task as workflow state | Foundational invariant | **Implemented**; parent synthesis is a **Design target** | A / D | [Research-state model](research-state-model.md#task-durable-workflow-state) |
| atomic scoped Hypothesis | Foundational invariant | **Partially implemented** as a split durable contract | C | [Research-state model](research-state-model.md#hypothesis-one-bounded-test-contract) |
| Evidence without interpretation | Foundational invariant | **Implemented** | A | [Scientific authority](scientific-authority.md) |
| Discovery as an evidence-bound claim | Foundational invariant | **Implemented** | A | [Research-state model](research-state-model.md#discovery-durable-evidence-bound-claim) |
| GeneratedView separation | Foundational invariant | separation **Implemented**; complete view workflow is a **Design target** | A / D | [Context reconstruction and continuity](context-reconstruction-and-continuity.md#parent-tasks-and-generatedviews) |
| separated scientific authority | Durable architectural decision | **Implemented** | A | [Scientific authority](scientific-authority.md) |
| protected conclusion context | Durable architectural decision | **Implemented** with a named-context **Known deviation** | A | [Protected evaluation context](protected-evaluation-context.md) |
| exact proposal-copy | Durable architectural decision | **Implemented** | A | [Scientific authority](scientific-authority.md#exact-proposal-copy) |
| atomic Discovery admission | Durable architectural decision | **Verified on SQLite** | A | [Governance and Discovery admission](governance-and-discovery-admission.md) |
| historical retention and active exclusion | Foundational invariant | **Implemented** with an under-enforced storage boundary | B | [Validity over time](validity-over-time.md) |
| atomic validity propagation | Durable architectural decision | **Verified on SQLite** | A | [Atomic validity propagation](atomic-validity-propagation.md) |
| user-governed active context | Durable architectural decision | **Partially implemented** | C | [SessionFrame and active context](session-frame-and-active-context.md) |

No reviewed decision is E-class on the supported path.

## 1. Typed research state instead of conversation history

- **Context:** Long-running analytical work must survive sessions while keeping
  identity, scope, provenance, lifecycle, and validity visible.
- **Problem:** Messages and summaries record what was said, but not which
  dataset state, test contract, observation, or authority supports a claim.
- **Failure mode:** A summary can merge incompatible scopes, lose negative or
  inconclusive outcomes, and retrieve superseded material as though it were
  current.
- **Tempting alternatives:** Save all chat, summarize each session, retain
  notebook history, vectorize every artifact, or maintain one evolving project
  summary.
- **Decision:** Represent research continuity through durable typed objects and
  typed non-FCO provenance rather than treating conversation as the research
  graph.
- **Invariant protected:** Every scientific conclusion remains traceable to an
  exact test contract, data state, Evidence set, scope, and validity basis.
- **Current implementation:** **Implemented**. Schemas, records, repositories,
  lifecycle guards, protected evaluation, retrieval policy, and SessionFrame
  projections operate on typed state. No supported raw-chat authority path
  exists.
- **Tradeoffs:** The design requires more schemas, admission services,
  lifecycle transitions, joins, validation code, and product interactions than
  a chat log.
- **Known limitations:** Complete project opening, restored conversation, and
  end-to-end user resume are **Unsupported** or **Partially implemented**.
- **Risks:** Typed state can become ceremony without enough product support, and
  duplicate projections can drift if concept ownership is unclear.
- **Revisit triggers:** Revisit storage layout, indexing, or schema partitioning
  when projects or lineages become large.
- **Consequences for future work:** New durable information must be classified
  as an FCO, workflow state, provenance, cache, filesystem artifact, or
  generated view before implementation. Typed identity, provenance, validity,
  and authority separation must remain.

## 2. Exactly eight First-Class Objects

- **Context:** Durable identity is valuable only when it corresponds to a
  concept that must be independently addressed across the investigation.
- **Problem:** Promoting every persisted record to scientific object status
  erases the difference between research intent, workflow, provenance,
  authority, presentation, and knowledge.
- **Failure mode:** A governance decision, execution attempt, generated answer,
  or cache entry can be retrieved as though it were an evidence-bound claim.
- **Tempting alternatives:** Treat every table as an FCO, add Workspace or
  Question for convenience, or use one generic object envelope.
- **Decision:** The FCO set is exactly `Objective`, `DataProfile`, `Assumption`,
  `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.
  `Objective` preserves intent; `DataProfile` preserves data-state identity;
  `Assumption` preserves explicit provisional planning input; `Task` preserves
  governed work; `Hypothesis` preserves the bounded test identity; `Evidence`
  preserves observed results; `Discovery` preserves evidence-bound knowledge;
  and `SessionFrame` preserves governable active-context snapshots.
- **Invariant protected:** Persistence does not confer scientific authority, and
  each epistemic role retains a distinct lifecycle and retrieval policy.
- **Current implementation:** **Implemented**. The source enum, schemas,
  persistence records, repository boundaries, and context policy use these
  eight types. `Workspace`, `AnalysisFrame`, `ExecutionRun`,
  `PlannerOperation`, `GeneratedView`, `EvidenceCacheEntry`, and
  `ValidityEvent` remain non-FCOs.
- **Tradeoffs:** Eight object types create more state transitions and lineage
  traversal than a generic record model.
- **Known limitations:** Some non-FCO product workflows, especially
  GeneratedView and persistent Evidence Cache, are **Design target** or
  **Deferred**.
- **Risks:** A future contributor may mistake durable provenance for knowledge
  or introduce a ninth FCO to solve a local persistence problem.
- **Revisit triggers:** The ontology may be reconsidered only when a candidate
  concept demonstrably needs independent epistemic identity, lifecycle,
  validity, and retrieval authority that cannot belong to an existing type.
- **Consequences for future work:** `Question` remains transient user input that
  may be answered or converted into Task proposals; no persisted Question
  schema, table, or repository currently exists. Adding a ninth FCO requires an
  explicit architectural decision.

## 3. Workspace outside the FCO graph

- **Context:** Research data, artifacts, configuration, and persistence need a
  containment and runtime boundary.
- **Problem:** Operational locality matters, but locality is not a scientific
  proposition.
- **Failure mode:** If Workspace becomes an inference object, filesystem or
  deployment state can be cited as support for a claim merely because it is
  durable.
- **Tempting alternatives:** Persist Workspace as a project FCO, attach all
  state to a generic project object, or infer workspace identity from the
  active Objective.
- **Decision:** Workspace remains a filesystem/runtime boundary that scopes
  data, artifacts, configuration, database locality, and authority bindings
  without entering the FCO graph.
- **Invariant protected:** Operational containment cannot become a claim,
  Evidence, or inference premise.
- **Current implementation:** **Implemented**. Runtime configuration uses a
  database location, DataProfiles bind dataset paths, and governance/validity
  authority carries workspace identity. No Workspace FCO schema or table
  exists.
- **Tradeoffs:** Workspace identity still couples operational composition to
  local research-state lookup and continuity.
- **Known limitations:** Workspace opening, discovery, authentication, and
  complete resume are **Unsupported**.
- **Risks:** Scalar workspace bindings can become inconsistent across services
  if deployment composition is not governed.
- **Revisit triggers:** Multi-tenant storage, remote artifact stores, or
  cross-workspace lineage may require a stronger operational Workspace record.
- **Consequences for future work:** A stronger Workspace representation may
  coordinate runtime resources, but it must remain non-scientific and outside
  conclusion authority.

## 4. Immutable DataProfile identity

- **Context:** A conclusion is valid only for the accepted data state actually
  analyzed.
- **Problem:** A mutable “current profile” makes an old identifier point to new
  schema, preprocessing, or population semantics.
- **Failure mode:** Existing Evidence and Discoveries silently appear to have
  been produced from data they never observed.
- **Tempting alternatives:** Update one profile row after cleaning, replace a
  dataset in place, or treat a file path as sufficient version identity.
- **Decision:** Data-changing preprocessing produces a new dataset version and
  a new DataProfile. The prior profile remains historical and may be
  superseded or invalidated through authorized validity propagation.
- **Invariant protected:** Evidence and Discovery references continue to name
  the exact accepted data semantics that supported them.
- **Current implementation:** **Implemented** at the schema and supported
  repository/application boundaries. DataProfile schemas are frozen,
  repositories are append-oriented, and split supersession is sealed.
  Lifecycle metadata may change atomically. Database-level protection of every
  scientific payload field is incomplete, so the source classification is B.
- **Tradeoffs:** Versioned profiles increase storage, lineage, review steps,
  joins, and migration complexity.
- **Known limitations:** Governed cleaning, executable dataset versioning, and
  external artifact integration are **Deferred** or **Partially implemented**.
- **Risks:** Unsupported direct ORM or SQL writes could bypass the
  application-level payload boundary.
- **Revisit triggers:** Large datasets, external version stores, or expensive
  profile duplication may require content-addressed or externalized profile
  payloads.
- **Consequences for future work:** Storage and artifact mechanisms may change,
  but immutable accepted data-state identity and explicit supersession lineage
  must remain.

## 5. Assumption quarantine

- **Context:** Provisional beliefs are useful for choosing what to inspect or
  test.
- **Problem:** The same beliefs become bias when they are allowed to support the
  conclusion they helped plan.
- **Failure mode:** A planning rationale is laundered into an empirical premise,
  making the final claim circular and untraceable.
- **Tempting alternatives:** Include Assumptions in every prompt, let the
  Analyst see Task rationale, or treat accepted Assumptions as weak Evidence.
- **Decision:** Assumptions may guide planning but must not determine scientific
  conclusions. Protected evaluation is built without Assumptions, and
  contradiction comparison happens only after Discovery admission.
- **Invariant protected:** Scientific inference is supported by the bounded
  Hypothesis, accepted data state, provenance, method, and active Evidence
  rather than unverified belief.
- **Current implementation:** **Implemented**. The protected bundle has no
  Assumption or generic-context channel, the Analyst has no alternate input,
  and architecture checks block SessionFrame projection from the protected
  path.
- **Tradeoffs:** Planning and evaluation need separate context construction,
  contracts, tests, and user explanations.
- **Known limitations:** General contradiction review, notifications, and Task
  or frame follow-up after Assumption replacement are **Partially implemented**
  or **Design target**.
- **Risks:** Assumption content could still leak through future free-form
  parameters or generated summaries if typed boundaries are weakened.
- **Revisit triggers:** New assumption categories may justify different
  planning policies, but any use as an inference premise requires an explicit
  evidence-bearing type and authority decision.
- **Consequences for future work:** Replacing an Assumption changes planning
  state; it does not automatically invalidate Evidence or Discovery because
  the Assumption was not a conclusion premise.

## 6. Task as workflow state, not scientific knowledge

- **Context:** Users need durable, decomposable, approvable work across
  sessions.
- **Problem:** Work descriptions and completion state do not establish that a
  proposition is scientifically true.
- **Failure mode:** A completed parent plan or accepted Task becomes a claim
  without one bounded test and Evidence basis.
- **Tempting alternatives:** Treat Task completion as knowledge, let every Task
  generate a Discovery, or synthesize child results into a parent Discovery.
- **Decision:** Task remains an FCO for governed workflow identity while
  remaining non-scientific. Only an eligible active terminal analytical Task
  may generate at most one Hypothesis; a parent Task produces no Discovery.
- **Invariant protected:** Workflow intent, decomposition, and lifecycle cannot
  substitute for observed Evidence and protected interpretation.
- **Current implementation:** **Implemented**. Planner, repository, evaluation,
  and admission guards reject proposed, inactive, non-analytical, or parent
  Tasks. Database uniqueness limits each Task to one Hypothesis.
- **Tradeoffs:** Users must decompose broad work, manage more Task states, and
  request a separate presentation for a parent answer.
- **Known limitations:** Parent-task GeneratedView synthesis is a **Design
  target** and the complete answer branch is **Partially implemented**.
- **Risks:** Broad analytical Tasks can still be poorly scoped before approval,
  increasing pressure to overstate a later result.
- **Revisit triggers:** Better plan synthesis or UI may change decomposition
  mechanics, but parent aggregation must remain presentation unless it receives
  its own bounded scientific contract.
- **Consequences for future work:** Parent answers belong in regenerable
  GeneratedViews over current valid child Discoveries, not in fabricated parent
  Discoveries.

## 7. Atomic scoped Hypothesis

- **Context:** A scientific evaluation needs one bounded relationship, data
  state, population or subset, method, decision rule, expected Evidence
  contract, and invalidation conditions.
- **Problem:** “Investigate the data” cannot identify what was tested or what a
  result means.
- **Failure mode:** The evaluator broadens scope, changes methods after seeing
  results, or creates several incompatible claims under one identity.
- **Tempting alternatives:** Use a broad natural-language prompt as the
  Hypothesis, permit multiple Discoveries per Hypothesis, or overwrite the
  original contract after correction.
- **Decision:** One eligible terminal analytical Task admits at most one atomic
  Hypothesis, and one Hypothesis admits at most one Discovery.
- **Invariant protected:** Each Discovery has one identifiable test contract
  and cannot silently expand beyond it.
- **Current implementation:** **Partially implemented**. The Hypothesis stores
  statement, DataProfile, variables, scope, method, and Evidence expectation.
  Decision rule, method parameters, and execution details remain in the
  approved Task analytical specification and are rebound into the protected
  snapshot; required invalidators are added by protected evaluation policy.
  Repository and database cardinality guards are **Implemented**.
- **Tradeoffs:** Fine-grained hypotheses increase Task count, orchestration,
  lineage, and correction work.
- **Known limitations:** The durable contract is split across Hypothesis and the
  approved Task specification, and the Planner currently performs operational
  contract authoring.
- **Risks:** Future code could read the Hypothesis without its approved
  specification and mistake the partial record for the complete evaluation
  contract.
- **Revisit triggers:** Reconsider the storage boundary when operationalization
  moves to the Hypothesis Analyst or when successor scientific lineages become
  first-class workflow needs.
- **Consequences for future work:** Corrections after Discovery admission
  generally require a successor Task/Hypothesis lineage and new protected
  evaluation rather than overwriting the original claim.

## 8. Evidence without interpretation

- **Context:** Analytical execution observes values, statistics, artifacts,
  exclusions, and technical limitations.
- **Problem:** The component controlling computation should not also decide the
  scientific meaning of its output.
- **Failure mode:** An executor can promote its own result to a conclusion,
  bypass protected context, or hide method and provenance mismatch.
- **Tempting alternatives:** Let Data Explorer return a complete conclusion,
  persist executor prose directly as Discovery, or combine Evidence admission
  with interpretation.
- **Decision:** Data Explorer returns observation-only contracts. Evidence
  admission validates and materializes AnalysisFrame, ExecutionRun, result,
  method, parameters, provenance, artifacts, and limitations, then stops before
  interpretation.
- **Invariant protected:** Computation and observation remain reproducible and
  independently reviewable before scientific meaning is proposed.
- **Current implementation:** **Implemented**. Output schemas reject unknown
  authority fields, Evidence admission imports no Discovery authority, generic
  Evidence creation is sealed, and active Evidence is the observed premise of
  protected evaluation.
- **Tradeoffs:** A separate protected evaluation stage, control lifecycle, and
  additional failure/retry paths are required.
- **Known limitations:** A concrete production Data Explorer is **Unsupported**,
  and scientific payload immutability lacks a universal database trigger.
- **Risks:** Free-form result summaries could drift toward interpretation if
  schema and validation language are weakened.
- **Revisit triggers:** Richer observations or new analytical methods may extend
  typed result contracts, but executor output must remain non-conclusive.
- **Consequences for future work:** Wrong or stale output creates successor
  Evidence plus supersession/invalidation; the old Evidence payload is not
  edited.

## 9. Discovery as an evidence-bound claim

- **Context:** Research continuity needs durable knowledge, including supported,
  contradicted, inconclusive, and insufficient-evidence outcomes.
- **Problem:** A summary or insight string does not expose the exact Evidence,
  scope, uncertainty, limitations, or validity conditions behind it.
- **Failure mode:** Narrative confidence exceeds the decision rule, or a
  fail-to-reject result becomes “there is no relationship.”
- **Tempting alternatives:** Persist Task answers, Evidence results, Planner
  opinions, governance decisions, or free-form insights as Discoveries.
- **Decision:** Discovery is a structured evidence-bound claim linked to one
  Hypothesis, the complete admitted Evidence set, DataProfile and AnalysisFrame
  provenance, epistemic status, scope, uncertainty, limitations, invalidators,
  and validity basis.
- **Invariant protected:** Durable knowledge cannot exist without observed
  support and an explicit statement of where and how it is valid.
- **Current implementation:** **Implemented**. Schema validators require
  Evidence and Assumption exclusion; protected proposal validation constrains
  scope and lineage; atomic admission is the sole writer.
- **Tradeoffs:** Discoveries require more structured fields, validation, joins,
  governance, and lifecycle handling than insight text.
- **Known limitations:** Successor-claim automation after invalidation is
  **Unsupported**, and storage-level scientific-field immutability is
  under-enforced.
- **Risks:** Presentation layers may flatten epistemic status or omit
  limitations even while the durable object remains correct.
- **Revisit triggers:** New scientific outcome types may extend the schema only
  if their decision semantics remain bounded and testable.
- **Consequences for future work:** Fail-to-reject and insufficient Evidence may
  produce valid Discoveries at the correct epistemic strength; they do not
  prove absence of a relationship.

## 10. GeneratedView separation

- **Context:** Users need answers, reports, plots, and parent-level synthesis
  over current research state.
- **Problem:** Presentation may combine several claims or transform wording
  beyond what one Hypothesis directly tested.
- **Failure mode:** Persisting every generated answer as knowledge creates
  untested composite Discoveries and stale narrative authority.
- **Tempting alternatives:** Store every response as a Discovery, promote a
  report to Evidence, or let a parent Task manufacture a claim from children.
- **Decision:** Presentation, parent synthesis, user-facing answers, and report
  composition belong to GeneratedView, not Discovery.
- **Invariant protected:** Narrative composition cannot silently acquire
  scientific authority.
- **Current implementation:** The non-authority boundary is **Implemented** in
  context policy and the absence of alternate Discovery writers. A complete
  GeneratedView schema, synthesis service, provenance path, and product flow
  are a **Design target**.
- **Tradeoffs:** Views may need regeneration, separate provenance, cache
  invalidation, and explicit UI labels.
- **Known limitations:** Parent Task answers and complete Planner answer
  generation are **Partially implemented** or **Unsupported**.
- **Risks:** Teams may use ad hoc reports as de facto authority before the
  GeneratedView contract exists.
- **Revisit triggers:** Persist GeneratedView provenance when reproducible
  reporting, review, or collaboration requires durable presentation identity.
- **Consequences for future work:** A persisted view must remain derived,
  regenerable, and non-authoritative; it must never silently become Discovery.

## 11. Separated scientific authority

- **Context:** Observation, interpretation, authorization, and persistence each
  grant a different kind of power over scientific state.
- **Problem:** One component controlling the whole lifecycle can manufacture
  Evidence, interpret it, approve itself, and write the result.
- **Failure mode:** Errors or prompt injection cross every boundary without an
  independent check, leaving no trustworthy authority trail.
- **Tempting alternatives:** Use one powerful scientist agent, let Data Explorer
  evaluate, let the Analyst persist, let governance rewrite, or let application
  code author a safer-sounding claim.
- **Decision:** Data Explorer observes; Hypothesis Analyst proposes; governance
  authorizes; application materializes exactly.
- **Invariant protected:** No one component owns the entire scientific
  lifecycle, and each durable transition is attributable to the authority that
  actually made it.
- **Current implementation:** **Implemented**. Typed contracts, no-tool Analyst
  dependencies, durable governance authority, private transaction hooks, and
  architecture checks enforce the supported chain.
- **Tradeoffs:** More contracts, services, transaction boundaries, orchestration
  states, failure modes, and tests are required.
- **Known limitations:** Production adapters for Data Explorer, Analyst model,
  identity, and user-facing governance are **Unsupported**.
- **Risks:** Convenience facades may accidentally accumulate authority if
  dependency direction and writer confinement are relaxed.
- **Revisit triggers:** Model or execution providers may change; role boundaries
  should be revisited only to strengthen explicit authority, not collapse it.
- **Consequences for future work:** New specialists must receive the minimum
  typed authority needed and must not inherit persistence or governance by
  convenience.

## 12. Protected conclusion context

- **Context:** Scientific synthesis is only as valid as the inputs admitted as
  inference premises.
- **Problem:** Prompt instructions cannot prove that unsafe memory, prior
  conclusions, or workflow rationale was absent.
- **Failure mode:** Assumptions, Tasks, prior Discoveries, SessionFrames, chat,
  raw files, retrieval scores, arbitrary pins, governance decisions, or generic
  context influence a proposal without appearing in its validity basis.
- **Tempting alternatives:** Tell the model to ignore unsafe context, pass a
  generic context bag, reuse a SessionFrame projection, or let the caller select
  Evidence.
- **Decision:** Protected evaluation receives a closed immutable bundle rebuilt
  from authoritative repositories and a closed provenance manifest.
- **Invariant protected:** Conclusion input is typed, complete, current,
  digest-bound, and independently reconstructable.
- **Current implementation:** **Implemented**. The bundle contains the bounded
  Hypothesis snapshot, accepted DataProfile metadata, exact AnalysisFrames and
  ExecutionRuns, complete active Evidence, method, parameters, decision rule,
  limitations, invalidators, and digests.
- **Tradeoffs:** The Analyst has less flexibility, bundle construction is more
  explicit, and every new scientific input requires schema and policy changes.
- **Known limitations:** A generic SessionFrame projection named for Discovery
  synthesis still exists as a **Known deviation**, but architecture enforcement
  prevents the protected path from consuming it.
- **Risks:** A future optional or generic field could become an unreviewed
  authority channel.
- **Revisit triggers:** Provider, serialization, or evaluation environment may
  change when stronger isolation or scale requires it.
- **Consequences for future work:** The closed authoritative input and exclusion
  of planning assumptions and generic context must remain regardless of model
  provider or execution environment.

## 13. Exact proposal-copy

- **Context:** The Analyst-authored proposal is the scientific content that
  governance reviews.
- **Problem:** Paraphrasing at governance or persistence time creates a
  different claim from the one evaluated and authorized.
- **Failure mode:** Wording, scope, status, Evidence IDs, uncertainty,
  limitations, validity basis, or invalidators change without scientific
  authorship or approval.
- **Tempting alternatives:** Normalize prose, strengthen cautious wording,
  shorten limitations, let governance edit the proposal, or let application
  services generate the final claim.
- **Decision:** Governance authorizes the exact persisted proposal, and
  application admission copies its scientific fields exactly.
- **Invariant protected:** The durable Discovery is the claim that was proposed
  and authorized, not an application-authored derivative.
- **Current implementation:** **Implemented**. Proposal and bundle digests bind
  all scientific fields; plan construction snapshots them; admission copies
  claim, epistemic status, scope, Evidence IDs, validity basis, uncertainty,
  limitations, and invalidators without paraphrase.
- **Tradeoffs:** Proposal quality must be correct at the Analyst boundary, and
  presentation cleanup cannot repair a scientifically weak proposal.
- **Known limitations:** The application still owns deterministic identity,
  timestamps, lifecycle metadata, transaction bindings, and copied lineage
  metadata; these additions must remain non-scientific.
- **Risks:** A new normalization helper or output adapter could subtly rewrite
  meaning while preserving superficial structure.
- **Revisit triggers:** Proposal schema versions may evolve, but migrations must
  preserve the exact authorized content and its digest identity.
- **Consequences for future work:** Presentation improvements belong in
  GeneratedView. Governance may approve, reject, or cancel, but not author.

## 14. Atomic Discovery admission

- **Context:** Discovery materialization completes several linked scientific,
  workflow, authority, and continuity records.
- **Problem:** Separate commits can leave the system asserting mutually
  incompatible states.
- **Failure mode:** A Discovery exists while its Hypothesis or Task remains
  active, a decision remains reusable, a claim is not committed, evaluation is
  uncommitted, or the conclusion SessionFrame is absent.
- **Tempting alternatives:** Let repositories commit independently, insert the
  Discovery first and repair later, let Planner create it, or use
  best-effort asynchronous lifecycle updates.
- **Decision:** Discovery insertion, Hypothesis evaluation, terminal Task
  completion, EvaluationControl commit, admission-claim commit, governance
  decision consumption, and conclusion SessionFrame append form one atomic
  admission.
- **Invariant protected:** Scientific identity, workflow completion, authority
  consumption, and continuity become visible together or not at all.
- **Current implementation:** **Implemented** and **Verified on SQLite** through
  one transaction owner, write-time reconstruction, compare-and-set guards,
  deterministic identity, claim leases, fencing, rollback, and exact replay.
- **Tradeoffs:** The transaction owner is complex, the write set is larger, and
  recovery semantics and concurrency tests are substantial.
- **Known limitations:** Guarantees are SQLite-specific; distributed ownership
  and other database backends are **Unsupported**.
- **Risks:** A new writer or split transaction can reintroduce partial
  scientific state even if each local repository operation appears valid.
- **Revisit triggers:** Another backend, multiple writer services, or an
  impractically large atomic write set requires a new verified ownership
  protocol.
- **Consequences for future work:** Transaction implementation, claim mechanism,
  or database may change, but no partial lifecycle commit, exact replay, and
  changed-binding conflict must remain.

## 15. Historical retention and active exclusion

- **Context:** Research state can become superseded, invalidated, contradicted,
  rejected, cancelled, or obsolete without ceasing to be part of the historical
  record.
- **Problem:** The system must distinguish what was recorded then from what may
  support work now.
- **Failure mode:** Deletion destroys the reasoning chain; retaining everything
  without active filtering lets invalid state regain authority.
- **Tempting alternatives:** Delete invalid rows, rewrite them in place, or keep
  them retrievable with only a lower relevance score.
- **Decision:** Preserve historical records and provenance while excluding
  invalid or superseded state before active retrieval and context assembly.
- **Invariant protected:** Historical presence is not active authority.
- **Current implementation:** **Implemented** on supported repository,
  validity, and retrieval paths. No public FCO delete/update API performs
  destructive invalidation, and retrieval rechecks lifecycle before scoring.
  Universal database-level no-delete protection for every historical FCO is
  incomplete, so the source classification is B.
- **Tradeoffs:** Storage, lifecycle reasoning, UI, retrieval policy, and lineage
  traversal are more complex.
- **Known limitations:** A complete historical-query product and durable review
  experience are **Unsupported** or **Partially implemented**.
- **Risks:** A new query path may omit active-authority filtering, or an
  unsupported direct database operation may erase history.
- **Revisit triggers:** Retention policy, archival scale, privacy obligations,
  or external stores may require tiering or controlled erasure semantics.
- **Consequences for future work:** Any archival or deletion mechanism must
  preserve required provenance and must not make active validity depend on
  relevance ranking alone.

## 16. Atomic validity propagation

- **Context:** When a DataProfile, AnalysisFrame, ExecutionRun, or Evidence
  source loses authority, dependent state must stop being active coherently.
- **Problem:** Repository-by-repository invalidation can leave some dependents
  active or record an event whose effects did not commit.
- **Failure mode:** An invalid Discovery remains retrievable, a stale admission
  worker publishes after source loss, or replay accepts a partial effect set.
- **Tempting alternatives:** Delete the source, cascade best-effort updates,
  accept caller-selected dependents, or treat a reused idempotency key as replay
  regardless of changed command content.
- **Decision:** Use a typed command, independently persisted authority,
  server-computed source fingerprint, deterministic effect plan, immutable
  ValidityEvent, atomic dependent updates, exact replay, changed-command
  conflict, compare-and-set, and rollback.
- **Invariant protected:** A validity transition changes visible scientific
  authority as one traceable operation without rewriting historical content.
- **Current implementation:** **Implemented** and **Verified on SQLite** for the
  supported source/event matrix. Validity owns no separate claim, lease, or
  fencing epoch. An affected Discovery admission claim contributes its own
  fencing epoch as a dependent compare-and-set input.
- **Tradeoffs:** Dependency discovery, source/request/plan/event fingerprints,
  larger transactions, recovery checks, and concurrency coverage add
  substantial complexity.
- **Known limitations:** Source traversal is relational and local; production
  authority issuance, distributed coordination, semantic-index cutover, and
  automatic successor claims are **Unsupported** or **Deferred**.
- **Risks:** Large plans may make one synchronous transaction impractical, and a
  new dependent store can remain stale if it is not included in the cutover.
- **Revisit triggers:** Another backend, distributed workers, cross-workspace
  lineage, large effect plans, external caches/indexes, or authoritative
  notification delivery.
- **Consequences for future work:** Mechanisms may change, but exact authority,
  deterministic effects, stale-owner exclusion, immutable provenance, exact
  replay, changed-command conflict, and atomic visible authority must remain.

## 17. User-governed active context

- **Context:** A long-running project contains more durable state than one
  operation can safely or usefully consume.
- **Problem:** Opaque retrieval hides why an item was included, what the user
  selected, and whether the frame is stale.
- **Failure mode:** Context changes invisibly, pins appear to restore invalid
  authority, or old summaries are treated as protected conclusion input.
- **Tempting alternatives:** Inject the top vector matches, replay all chat, use
  one evolving summary, or let pins override lifecycle policy.
- **Decision:** SessionFrame exposes a typed active-context snapshot with pins,
  exclusions, inclusion reasons, warnings, stale markers, pending work, and
  predecessor/checkpoint/handoff metadata. Selected objects retain their own
  authority rules.
- **Invariant protected:** User context governance does not grant power to
  restore invalid scientific authority.
- **Current implementation:** **Partially implemented**. Frame schemas,
  append-oriented repository paths, successor snapshots, typed projections,
  pins/exclusions, deterministic retrieval, conclusion frames, and validity
  supersession exist.
- **Tradeoffs:** Explicit governance requires more UI, snapshots, storage,
  explanations, stale-state handling, and testing.
- **Known limitations:** The UI and resume workflow are incomplete; latest-active
  selection is database-global; pin-only relationships can miss frame
  supersession; and wrong-profile context-only items can consume the visible
  result budget.
- **Risks:** Stored summaries can become stale, and a mode name can be mistaken
  for protected authority even when the architecture blocks that path.
- **Revisit triggers:** Branching projects, multi-user collaboration, large
  frames, richer user controls, or stronger resume requirements.
- **Consequences for future work:** UI, selection algorithms, branching, and
  storage representation may change. User-visible governance and the inability
  to override current validity must remain.

## Recurring tradeoff themes

### Explicit state over implicit memory

Typed identity and lifecycle cost more schemas, joins, and product steps. The
cost is accepted because implicit memory cannot prove scope, provenance, or
current authority.

### Typed authority over prompt convention

Closed bundles and role-specific contracts constrain model flexibility and slow
ad hoc feature work. The cost is accepted because a prompt cannot prove that an
unsafe premise or writer was absent.

### Historical truth over destructive convenience

Retention increases storage, retrieval policy, and UI complexity. The cost is
accepted because correction without history is indistinguishable from
rewriting the record.

### Atomic consistency over partial progress

Larger transactions, compare-and-set guards, replay identity, and recovery
logic are harder to build and debug. The cost is accepted because partially
committed scientific lifecycle state is internally contradictory.

### User-governed context over opaque injection

Snapshots, pins, exclusions, reasons, and warnings require deliberate product
design. The cost is accepted because continuity should be inspectable without
turning user selection into scientific authority.

### Bounded scientific claims over broad narrative conclusions

Fine-grained Tasks and Hypotheses create more workflow state and parent-level
presentation work. The cost is accepted because one evidence-bound claim must
remain identifiable and falsifiable within its scope.

## Current-stage choices and known deviations

The following mechanisms are not foundational invariants:

| Item | Classification | Boundary |
| --- | --- | --- |
| SQLite synchronization, writer serialization, and current trigger behavior | Current-stage implementation choice | atomicity is **Verified on SQLite**; backend portability is **Deferred** |
| deterministic lexical scoring | Current-stage implementation choice | ranking may change after admissibility; retrieval implementation belongs to the operational decision follow-up |
| database-global latest-active SessionFrame selection | Known temporary deviation | selection is not yet user, Objective, or branch scoped |
| generic synthesis-named SessionFrame projection | Known temporary deviation | it is architecture-blocked from protected evaluation |
| pin-only SessionFrame freshness | Known temporary deviation | repository-current retrieval excludes invalid authority even when the frame is not marked stale |
| wrong-profile context-only items consuming result budget | Known temporary deviation | they cannot motivate work but may reduce the visible same-profile result set |
| operation-scope retrieval admission | Deferred design decision | no current request contract enforces a complete operation-specific admissibility policy |
| distributed scientific transactions | Unsupported future possibility | no supported distributed ownership or portability guarantee exists |

## What future redesigns must preserve

Storage backend, schema layout, indexing, model provider, serialization,
transaction mechanism, claim mechanism, SessionFrame UI, and retrieval ranking
may change. A redesign must still preserve:

- exactly typed epistemic identity and explicit non-FCO roles;
- immutable accepted data-state and observed-result identity;
- Assumption quarantine;
- bounded Task/Hypothesis/Discovery cardinality;
- Evidence/Discovery and GeneratedView/Discovery separation;
- observation, proposal, governance, and materialization authority boundaries;
- closed authoritative protected evaluation input;
- exact scientific proposal authority;
- no partial scientific lifecycle or validity commit;
- immutable transition provenance and exact replay;
- historical retention with active exclusion; and
- user-visible context governance that cannot restore invalid authority.

## Deferred Phase 3B operational decision scope

This page does not decide SQLite as a long-term backend, in-process runtime
composition, repository and transaction-owner packaging, Planner persistence
coupling, lexical versus semantic retrieval implementation, SessionFrame
selection mechanics at scale, migration strategy, CLI/API/worker timing,
deployment authentication, distributed execution, or database portability.
Those topics belong to Phase 3B and must preserve the epistemic invariants
above.

## Related decision records

- [ADR-001: First-Class research state](decisions/ADR-001-first-class-research-state.md)
- [ADR-002: Assumption quarantine](decisions/ADR-002-assumption-quarantine.md)
- [ADR-003: Specialist scientific authority](decisions/ADR-003-specialist-scientific-authority.md)
- [ADR-004: Atomic Discovery admission](decisions/ADR-004-atomic-discovery-admission.md)
- [ADR-005: Atomic validity propagation](decisions/ADR-005-atomic-validity-propagation.md)

## Implementation orientation

The primary source boundaries are under `src/schemas/`, `src/db/models/`,
`src/repositories/`, `src/agents/executor/`, `src/agents/planner/`,
`src/application/evidence/`, `src/application/evaluation/`,
`src/application/governance/`, `src/application/discovery/`,
`src/application/validity/`, and `src/memory/`.

Focused verification is under `tests/architecture/`, `tests/application/`,
`tests/memory/`, `tests/repositories/`, and `tests/e2e/`.
