# Persistence and admission

Application authority is the sole boundary that makes governed state durable.
Agents and specialists propose or return bounded results; application authority
validates contracts, owns transactions, and admits only the transitions allowed
by the designated authority.

This page defines the target persistence and admission architecture without
prescribing SQL, tables, packages, or a database topology.

## Canonical application-authority rule

```text
agents propose or return bounded results
application authority validates and admits durable state
```

Persistence is not scientific authorship. A stored model response is not
Evidence. A governance record is not a Discovery. A durable execution result is
not authoritative scientific content unless the Evidence-admission contract is
satisfied.

## Application authority responsibilities

Application authority owns:

- identity allocation and collision prevention;
- typed contract validation;
- Objective-scoped admission checks;
- persistence and transaction boundaries;
- lifecycle-transition guards;
- `Plan` activation;
- execution-attempt admission;
- Evidence admission;
- governance-decision application;
- Discovery admission;
- validity propagation and current-use eligibility;
- outbox and inbox processing;
- leases and fencing;
- idempotency and deduplication;
- replay and restart safety;
- fail-closed handling of ambiguous or incomplete state.

It may reject a scientifically plausible proposal because its identity,
lineage, approval, scope, contract version, provenance, or lifecycle state is
invalid. That rejection protects authority; it does not perform a competing
scientific evaluation.

## Total persistence boundaries

Total persistence contains more than the semantic Knowledge Graph. It must be
able to preserve:

| State family | Examples | Admission posture |
| --- | --- | --- |
| semantic research state | Objective, Hypothesis, Evidence, Discovery | typed, lineage-bound, lifecycle- and validity-governed |
| data and workflow state | DataProfile, Assumption, Task, SessionFrame | type-specific lifecycle and immutability rules |
| plan and investigation state | Plan, PlanDependency, scientific investigation, protocol, and EvidenceRequest records | append-oriented or lifecycle-governed; exact authority required |
| provenance | ExecutionRun, AnalysisFrame, method, parameters, code and environment identity | append-oriented and bound to work identity |
| governance and validity | decisions, holds, correction requests, admission records, validity events | exact proposal identity and authorized transition |
| operational recovery | outbox, inbox, leases, fencing tokens, idempotency keys, replay and retry records | transactional and restart-safe |
| presentation and cache | GeneratedView metadata and reusable computation references | derived; cannot author Evidence or Discovery |

The physical implementation may colocate or separate these families. Their
authority and lifecycle boundaries must remain distinct either way.

## Provenance and cache separation

Provenance preserves how work happened. It may include objective and planning
revisions, execution attempts, AnalysisFrames, rejected paths, cleaning
decisions, tool or notebook runs, user decisions, method parameters, code and
environment identity, and audit traces. These records may be durable and
transactionally important without becoming FCOs or semantic-graph nodes.

Cache is a reusable-computation index, not research authority. A cache key must
bind every input that can change reuse validity, including the applicable
Hypothesis signature, DataProfile, AnalysisFrame, method, parameters, code,
environment, and seed where relevant. A cache hit may propose reuse of admitted
Evidence after the normal eligibility checks; it cannot create Evidence or a
Discovery by itself.

## Identity and admission

Identity is allocated or validated before a durable transition. Admission then
checks, as applicable:

- object and contract type;
- schema and contract version;
- Objective scope;
- predecessor or successor identity;
- exact Plan membership and work binding;
- approval or governance identity;
- lifecycle eligibility;
- scientific lineage and cardinality;
- DataProfile and AnalysisFrame identity;
- execution attempt and result digest;
- method, parameters, decision rule, seed, and provenance obligations;
- current validity and invalidators;
- idempotency and replay state.

Missing or ambiguous required identity fails closed. Structural validation may
canonicalize finite typed structure and compute digests, but it does not infer
semantic equivalence, repair scientific meaning, or guess cross-Objective
compatibility.

## Atomic plan and execution transitions

An approved `Plan` becomes active only through an atomic application
transition. Plan identity, Task membership, dependencies, workflow state, and
eligible lifecycle changes must agree. Partial activation is invalid.

Execution admission similarly binds one authorized work identity to one
attempt and dispatch intent. The durable attempt and its outbox record must be
created consistently so a crash cannot leave executable work without an
authoritative attempt or leave an admitted attempt with no recoverable dispatch
intent.

The application, not the Planner or executor, owns the transaction. A failed
validation or write rolls back the transition and returns a typed failure or
blocker.

## Outbox, inbox, leases, and fencing

The outbox records an admitted intent to dispatch work. A worker claims that
intent under a lease and fencing token or epoch. The inbox records returned
messages or results with their source, attempt identity, digest, and processing
state.

These mechanisms protect against:

- dispatch lost after commit;
- duplicate delivery;
- a stale worker completing after its lease expired;
- concurrent workers writing for the same attempt;
- result replay after a newer attempt or plan exists;
- restart between result receipt and durable transition.

Only a currently fenced attempt may advance its lifecycle. Expiration returns
work to a recoverable state or produces a typed ending under policy; it does
not silently reuse stale worker authority.

## Idempotency, retry, replay, and restart

Every consequential command and result carries enough stable identity for the
application to distinguish a retry from new work. Replaying the same approved
proposal, dispatch command, worker result, governance decision, or admission
request must not create a second semantic object or duplicate transition.

A retry is a new traceable execution attempt when the prior attempt has ended
or lost authority. It retains predecessor identity and the exact authorization
for retry. Replay reconstructs application progress from durable records; it
does not ask an agent to remember what happened.

If the application cannot prove which proposal, plan, attempt, result, or
decision a message belongs to, it fails closed and requests recovery or review.

## Evidence admission

Data Explorer returns observation material; it does not create authoritative
Evidence. Evidence admission validates the observation against the applicable
scientific and provenance obligations, including:

- Hypothesis and EvidenceRequest identity;
- admitted DataProfile;
- exact AnalysisFrame and ExecutionRun;
- method, parameters, decision rule, and seed where applicable;
- artifacts, result digest, limitations, and uncertainty;
- attempt fencing and result integrity;
- Objective and lifecycle eligibility.

Admitted Evidence is immutable. Correction, invalidation, or supersession
creates new Evidence or a governed validity or lifecycle relation; it never
edits the observed content in place.

Execution output is therefore not automatically Evidence, even on successful
completion.

## Governance application and Discovery admission

Protected evaluation may produce a `DiscoveryProposal` or typed
non-completion. Governance may approve, reject, hold, request correction,
request additional Evidence, or request conflict review.

Governance does not rewrite scientific content. When correction is requested,
the scientific authority creates a revised proposal. Application authority
then applies only a decision bound to the exact eligible proposal version.

Discovery admission verifies proposal identity, governance authorization,
Hypothesis and Evidence lineage, allowed epistemic outcome, scope, validity
basis, cardinality, and current eligibility. Only after that transaction does a
`DiscoveryProposal` become a `Discovery`.

## Validity transitions

Application authority applies authorized validity events to current-use
eligibility while preserving historical truth-to-record. It propagates
invalidators across exact typed dependencies and prevents invalid or stale
objects from entering protected contexts or validity-sensitive GeneratedViews.

Validity transition is not deletion and does not rewrite Evidence or Discovery
content. It changes whether recorded state is eligible for a specified present
use and preserves why that changed.

## Dependency inversion and role boundaries

The target architecture keeps role meaning independent from technical
adapters. Planner and specialists depend on bounded capabilities; they do not
construct model providers, persistence, mutable global tooling, or user
presentation. Application composition supplies those capabilities from the
outside, which preserves the authority boundaries even when storage, model, or
tool implementations change.

**Partially implemented.** The execution and model/tooling composition paths
follow this boundary. Application services still depend on the concrete
SQLite persistence implementation, so complete persistence-port inversion
remains a **Design target**. [Source layout](../development/source-layout.md)
owns the implementation-level package map.

## Implementation status

**Partially implemented.** Current source includes typed provenance and
operational records plus bounded transaction, attempt, outbox, lease, fencing,
retry, and idempotency seams. These donor and infrastructure surfaces are not
composed into the complete canonical workflow and do not establish restart or
scientific admission by themselves.

The bounded current surface is **Verified on SQLite** for atomic initial
DataProfile admission with an immutable one-to-one physical dataset binding.
The binding stores `data_profile_id`, normalized dataset reference, and the
`sha256:<hex>` digest of exact loaded file bytes. Direct Evidence admission fails
closed unless request path, observed execution path, observed digest, and
provenance profile identity all match that authoritative binding. This is a
non-FCO provenance/authority record and does not expand the semantic graph.

Side-effect-free Plan candidate validation is **Implemented**.
Application requires exact persisted Objective and Assumption content, resolves
every member Task from persistence, revalidates exact membership and DAG
structure, verifies canonical representation, and recomputes the fingerprint
without writing or committing. It does not consult provider or capability
availability.

Immutable Plan repository infrastructure is **Verified on SQLite**.
Normalized `plans`, `plan_assumptions`, `plan_tasks`, and
`plan_dependencies` rows preserve exact Plan content and fingerprint in one
caller-owned transaction. `plan_tasks` contains only `plan_id` and `task_id`.
The domain groups all outgoing dependents under one prerequisite; repository
writes flatten those groups to atomic edge rows and loads regroup them
canonically.
The Plan header snapshots exact Objective content;
each assumption link snapshots exact admitted Assumption content. Reload still
requires the referenced Objective, Assumptions, and Tasks to exist, but it
reconstructs historical Objective and Assumption semantics from the immutable
snapshots rather than mutable live rows. Child-write failure rolls the complete
snapshot back; loading fails closed on missing references, inconsistent
snapshot identity, or fingerprint mismatch. Same-ID replay or collision cannot
overwrite the existing snapshot, while different IDs with the same content
fingerprint remain distinct. The repository is append-only and exposes no
update or delete surface.

Application retains the exact Planner candidate in-process without writing it.
Frozen `PlanReviewDecision` is the Human authority value; conversation text is
not sufficient. Reject/revise write nothing. Approval requires the exact
candidate ID and atomically validates existing Assumptions, resolves or admits
the exact Objective and Tasks, persists the immutable Plan, and writes one
objective-scoped active pointer. Any failure rolls the complete transaction
back. Pending candidates and review decisions are not durable or recoverable.

The complete target boundary is not implemented. Canonical Task DAG execution,
durable pending-review recovery, role-native result inbox processing,
complete replay coordination, scientific Evidence admission from
`EvidenceRequest`, governance
workflow, Discovery admission from exact governed proposals, and end-to-end
validity propagation are incomplete or absent. Existing foundations must not be
described as a supported complete runtime.

See [End-to-end flow](end-to-end-flow.md) for how these transitions compose.
