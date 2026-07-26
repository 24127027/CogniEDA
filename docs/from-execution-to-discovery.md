# From execution to Discovery

This workflow follows one approved terminal analytical Task through observation,
evaluation, governance, and durable scientific admission. It begins after
planning and Task activation; the earlier path is covered in
[From question to Discovery](from-question-to-discovery.md).

The running Task asks:

> Test whether longer first-response time is associated with 90-day churn in
> the accepted 2025 small-business subscription cohort, using the approved
> method, parameters, and decision rule.

The path is:

```text
approved terminal analytical Task
  -> Hypothesis and execution admission
  -> Data Explorer execution
  -> AnalysisFrame / ExecutionRun provenance
  -> atomic Evidence admission
  -> protected evaluation
  -> exact governance decision
  -> atomic Discovery admission
```

This is not an automatic conveyor belt. Technical failure, evaluation failure,
rejection, cancellation, stale authority, or changed lineage can stop the path
without creating a Discovery.

> **Implementation status:** The guarded in-process workflow is
> **Implemented**, and the covered transaction, replay, fencing, rollback, and
> race behavior is **Verified on SQLite**. The user-facing workflow is
> **Partially implemented**. A production CLI, API, worker, authentication
> provider, concrete Data Explorer, and default Analyst model adapter are
> **Unsupported**.

## 1. The eligible Task is active, analytical, and terminal

The direct scientific unit must be:

- an `ACTIVE` Task;
- `ANALYTICAL`;
- bound to an active DataProfile accepted as ground truth;
- equipped with a complete approved analytical specification;
- terminal, meaning it has no child Tasks.

A parent Task can organize several churn-driver analyses, but it cannot produce
one Discovery because it has no single Hypothesis and Evidence set. Parent-level
presentation belongs in a future `GeneratedView`, not in this workflow.

An eligible Task still has no scientific outcome. Its description and
motivation remain workflow state, and they will not enter protected evaluation.

## 2. Approval admits one Hypothesis and one execution attempt

The prepared execution contract binds:

- Task, DataProfile, and session identity;
- Hypothesis statement;
- variables and cohort scope;
- analysis intent;
- method and parameters;
- decision rule;
- Evidence expectation;
- deterministic seed when required;
- configured Data Explorer identity.

The user approves the exact contract fingerprint. At commit, the application
reloads current Task and DataProfile authority, then creates or reuses the one
Hypothesis allowed for that terminal Task and admits an `ExecutionRun` plus
dispatch outbox.

The Hypothesis is the bounded test contract. It is not a conclusion. The
ExecutionRun is attempt provenance, not an FCO or scientific claim.

**Current status:** Approval-gated execution admission is **Implemented** and
**Verified on SQLite**. The Planner currently authors the operational
analytical contract, which is a **Known deviation** from the longer-term
specialist operationalization boundary.

## 3. A worker claims the attempt and invokes Data Explorer

A worker-like caller claims the outbox using owner, expiry, lease epoch, and
attempt version. The application reconstructs the durable prepared execution
and dispatches it to exactly one configured Data Explorer adapter.

The Data Explorer may return:

```text
AnalysisFrameObservation
EvidenceObservation
execution details
technical diagnostics
```

or a typed technical failure.

It cannot:

- evaluate the Hypothesis;
- choose supported, contradicted, inconclusive, or insufficient evidence;
- author a `DiscoveryProposal`;
- govern or persist scientific state;
- mutate the Task or Hypothesis lifecycle.

The observation-only boundary and its rationale are owned by
[Scientific authority](scientific-authority.md).

**Current status:** Contracts, registry, dispatch, receipt, retry, and recovery
are **Implemented**. A concrete production Data Explorer and production worker
are **Unsupported**.

## 4. Receipt makes execution output durable, not scientific

The receiver binds the returned payload to the claimed attempt and stores an
authoritative inbox record and result digest. Duplicate delivery can be
classified against durable identity. A different payload for the same attempt
is a conflict, not a second interpretation.

At this point:

- the ExecutionRun records what attempt occurred;
- the inbox records the returned observation or technical failure;
- no Evidence or Discovery has been created.

A technical failure can remain durable execution provenance. It cannot be
converted into Evidence merely to keep the workflow moving.

## 5. Evidence admission materializes observation and provenance

For a successful result, the finalizer claims Evidence-admission ownership and
builds a deterministic plan. It validates the current Task, Hypothesis,
DataProfile, approved specification, outbox, inbox, method, parameters, result
digest, attempt version, lease, and fence.

One transaction then:

```text
inserts AnalysisFrame
inserts immutable Evidence
moves ExecutionRun to EVIDENCE_ADMITTED
moves Hypothesis to READY_FOR_EVALUATION
consumes the authoritative inbox
```

The direct Task remains `ACTIVE`. The transaction deliberately stops before
interpretation.

`AnalysisFrame` identifies the data view. `ExecutionRun` identifies the
attempt. `Evidence` records the observed result and its limitations. None is a
Discovery.

**Current status:** Evidence admission, exact replay, conflict quarantine,
fencing, and rollback are **Implemented** and **Verified on SQLite**.

## 6. Protected evaluation reconstructs scientific input

Evaluation starts from the ready Hypothesis identity. The application reloads:

- the active terminal analytical Task and approved specification;
- the active accepted DataProfile;
- the complete active admitted Evidence set;
- each Evidence item's AnalysisFrame and ExecutionRun lineage;
- the matching outbox contract.

It creates the closed, deterministic `DiscoverySynthesisBundle`. The Analyst
receives only that bundle, without tools or message history. Assumptions, Tasks,
prior Discoveries, SessionFrames, chat, retrieval scores, governance decisions,
raw files, and generic context are structurally absent.

The Analyst returns:

```text
DiscoveryProposal | EvaluationFailure
```

The closed input, Assumption quarantine, digest binding, generic-context
distinction, and tool isolation are owned by
[Protected evaluation context](protected-evaluation-context.md).

### DiscoveryProposal

A proposal carries a structured claim, epistemic status, exact Evidence set,
scope, validity basis, uncertainty, limitations, and invalidators. It is
persisted as exact Analyst output but remains lifecycle-distinct from
Discovery.

### EvaluationFailure

A typed failure means the protected evaluation could not produce a valid
proposal. It may reflect invalid lineage, missing provenance, unidentifiable
evaluation, unsupported contract, provider failure, or invalid structured
output. It is not an inconclusive scientific result, and application code does
not replace it with a guessed claim.

**Current status:** Bundle reconstruction, evaluation control, no-tool Analyst
invocation, proposal validation, failure publication, retry, and fencing are
**Implemented**. A default production Analyst provider is **Unsupported**.

## 7. The four proposal outcomes retain bounded meaning

| Outcome | Meaning in this workflow | Unsafe strengthening |
| --- | --- | --- |
| supported | Evidence supports the Hypothesis within the approved scope, method, and uncertainty | broad, universal, or causal support not tested by the contract |
| contradicted | Evidence conflicts with the Hypothesis as stated in the evaluated scope | automatic support for the inverse claim |
| inconclusive | no stable directional conclusion is justified under the contract | treating uncertainty as a technical failure or as proof of absence |
| insufficient evidence | the Evidence does not satisfy the required threshold for the claim | “there is no relationship” |

For the running example, if the approved threshold is not met, a valid proposal
might state:

> Available Evidence is insufficient to establish an association between
> first-response time and 90-day churn within the 2025 small-business cohort
> using the approved method and decision rule.

All four outcomes can become knowledge when expressed with their exact
Evidence, scope, uncertainty, and validity basis. None bypasses governance.

## 8. Governance records a decision about the exact proposal

An authenticated principal receives expiring authority bound to the
workspace/session, purpose, and operation. Governance reloads the current
proposal and protected lineage and records one exact outcome:

```text
APPROVED
REJECTED
CANCELLED
```

The decision binds the evaluation, proposal digest, bundle digest, Evidence-set
digest, Hypothesis, Task, principal, and authority. There is no modification
outcome.

Approval makes the proposal eligible for admission; it does not create a
Discovery. Rejection or cancellation leaves the proposal and decision as
workflow/governance history and stops the path.

**Current status:** The in-process authority and decision services are
**Implemented**. A production authentication provider and complete interactive
review surface are **Unsupported** or **Partially implemented**.

## 9. Atomic admission commits the exact Discovery chain

An admission worker durably claims the approved operation. Before writing, it
reconstructs the current proposal, decision, authority, Hypothesis, terminal
Task, DataProfile, Evidence, AnalysisFrames, ExecutionRuns, bundle, manifest,
and digests. After guarded writes acquire the SQLite writer lock, it reconstructs
the authority again.

One transaction:

```text
inserts exact proposal-copy Discovery
appends deterministic conclusion SessionFrame
moves Hypothesis to EVALUATED
moves direct terminal Task to COMPLETED
moves EvaluationControl to COMMITTED
moves DiscoveryAdmissionClaim to COMMITTED
consumes the exact approved ProposalDecision
```

The application may add deterministic identity, time, lifecycle metadata, and
transaction bindings. It cannot rewrite scientific content.

Exact retry returns the same complete chain. A changed proposal, Evidence set,
lineage, principal, authority, decision, Task/Hypothesis relation, bundle, or
contract version conflicts. A stale worker loses its fence. A failure before
commit rolls back every staged scientific and lifecycle effect.

The full authority, exact-copy, replay, claim/lease/fence, compare-and-set, and
SQLite transaction reasoning is owned by
[Governance and Discovery admission](governance-and-discovery-admission.md).

**Current status:** Atomic Discovery admission is **Implemented** and
**Verified on SQLite**. Cross-database and distributed cutover guarantees are
**Unsupported**.

## 10. The conclusion SessionFrame is a handoff, not an inference premise

The atomic transaction appends a deterministic conclusion SessionFrame that
points to the admitted Discovery and supporting Evidence and records warnings.
It contains no active Assumptions.

The frame did not produce the proposal. Protected evaluation had already used
the repository-built bundle. The frame exists so later work can inspect and
resume from the committed conclusion without treating conversation or generic
context as scientific authority.

SessionFrame reconstruction and active retrieval continue in
[SessionFrame and active context](session-frame-and-active-context.md),
[Retrieval and context type safety](retrieval-and-context-type-safety.md), and
[Context reconstruction and continuity](context-reconstruction-and-continuity.md).
Later authority changes continue in
[Validity over time](validity-over-time.md) and
[From validity change to reconstructed context](from-validity-change-to-reconstructed-context.md).

## Where the workflow stops

| Stop condition | What remains durable | What is not created |
| --- | --- | --- |
| execution technical failure | ExecutionRun, inbox, diagnostics as applicable | Evidence and Discovery |
| invalid or conflicting observation admission | attempt/conflict provenance | admissible Evidence and Discovery |
| evaluation failure | EvaluationControl and typed `EvaluationFailure` | DiscoveryProposal and Discovery |
| governance rejection | proposal and rejected decision | Discovery |
| governance cancellation | proposal and cancelled decision | Discovery |
| stale or changed admission binding | existing workflow/authority history and conflict state as applicable | partial Discovery chain |
| atomic transaction failure | pre-transaction committed controls; staged cutover is rolled back | every cutover effect |

Stopping is part of validity preservation. “At most one” Hypothesis and
Discovery cardinality leaves room for these legitimate non-success paths.

## Current boundary

The source proves an in-process scientific spine, not a deployed product:

- **Implemented:** guarded Task-to-Hypothesis execution admission, execution
  provenance, Evidence admission, protected evaluation, governance decisions,
  and exact atomic Discovery admission;
- **Verified on SQLite:** transaction, replay, rollback, fencing, and covered
  race behavior;
- **Partially implemented:** the complete user-facing orchestration and
  approval journey;
- **Unsupported:** production Data Explorer, authentication provider, Analyst
  provider, CLI, API, worker, daemon, deployment bootstrap, distributed
  execution, and cross-database transaction guarantees.

## Implementation orientation

The workflow is distributed across:

- `src/application/execution/`;
- `src/agents/executor/`;
- `src/application/evidence/`;
- `src/application/evaluation/`;
- `src/agents/executor/hypothesis_analyst/`;
- `src/application/governance/`;
- `src/application/discovery/`.

Focused verification is under:

- `tests/application/execution/`;
- `tests/application/evidence/`;
- `tests/application/evaluation/`;
- `tests/application/governance/`;
- `tests/application/discovery/`.
