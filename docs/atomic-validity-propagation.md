# Atomic validity propagation

Validity changes are dangerous when their source transition, dependent effects,
and provenance can diverge. CogniEDA therefore gives one application service
ownership of the supported validity transaction.

> **Implementation status:** `AtomicValidityPropagationService`, the
> `validity-propagation/v1` contracts, deterministic effect planning, CAS-guarded
> writes, immutable event insertion, rollback, exact replay, and covered race
> behavior are **Implemented** and **Verified on SQLite**. A separate validity
> claim/lease protocol, distributed fencing, and cross-database guarantees are
> **Unsupported**.

The canonical path is:

```text
typed validity command
+ authenticated principal and durable authority
+ exact source-state fingerprint
-> deterministic affected-object plan
-> immutable ValidityEvent
-> atomic dependent-state updates
```

This is a validity-specific governance transaction, not a generic event system.

## One transaction owner

`AtomicValidityPropagationService` is the sole supported owner of source
lifecycle transition, dependent effects, and ValidityEvent insertion.
Repositories provide lookup, deterministic dependency discovery, conversion,
and a private stage-only event hook. They do not commit an alternative
repository-by-repository cascade.

The distinction matters:

- planning determines the complete effect set without mutating state; and
- committing applies that set only while its expected states still hold.

The plan is a frozen detached value. The public plan builder can be called
without writing any event or lifecycle transition. Execution does not trust an
old caller-supplied plan; it rebuilds the plan from current persisted state and
then applies guarded writes in the service-owned unit of work.

This costs an additional deterministic traversal, but it prevents an arbitrary
client from choosing the objects that will retain or lose authority.

## Typed command and validity authority

The command binds one requested transition to:

- contract version;
- source type and identity;
- requested event and reason;
- durable authority identity;
- workspace and, when required, session;
- expected source lifecycle and source fingerprint;
- caller-stable idempotency key; and
- replacement identity and fingerprint for supported supersession.

Authority is loaded from durable governance state. The service recomputes the
authority fingerprint and verifies:

- authority class and identity;
- active and expiry state for an original execution;
- exact workspace binding;
- exact session and authenticated principal for user-governed authority;
- allow-listed producer identity for trusted internal authority; and
- event-specific purpose and operation scope bound to the exact source and,
  for supersession, replacement.

An exact replay may be recognized after the original grant becomes inactive or
expires because replay is verification of a previously committed operation, not
new permission to mutate state. Identity, scope, principal binding, request
fingerprint, plan, and committed effects are still checked.

The runtime exposes an in-process propagation facade and can bind a
user-governed command to an injected authenticated-principal resolver. No
checked-in production identity provider or general validity-authority issuer
supplies these source-specific grants. The authority contract is
**Implemented**; the complete production authority workflow is
**Unsupported**.

## Why the fingerprints are distinct

Each fingerprint answers a different question.

| Binding | Question answered | Current role |
| --- | --- | --- |
| source-state fingerprint | Was this command planned against the exact supported source content? | server-computed from the source's immutable core, excluding lifecycle and allowed operational metadata |
| request fingerprint | Is this the same complete authorized command? | binds command content to persisted authority identity, class, purpose, and operation |
| plan fingerprint | Is this the same deterministic transition manifest? | hashes the frozen plan, including source binding and ordered target transitions |
| event identity | Is this the durable event for this exact request identity? | deterministically binds the idempotency key and request fingerprint |

The source fingerprint cannot replace the request fingerprint: two commands can
target the same source state for different reasons, effects, or authorities.
The request fingerprint cannot replace the plan fingerprint: the request names
the concern, while the plan names every intended effect. Event identity cannot
replace either: it gives the committed provenance a stable durable identity.

Supersession also verifies the persisted replacement's fingerprint and lineage.
Replacement Evidence must preserve Hypothesis and DataProfile lineage;
replacement DataProfiles must describe the same dataset path.

## Deterministic affected-object planning

Planning reloads the source, verifies its expected state and fingerprint, checks
event eligibility, verifies any replacement, and discovers dependents from
repository state.

Every transition records:

- target type and identity;
- expected lifecycle state;
- target lifecycle state; and
- a fingerprint of the target's mutable validity or review fields.

Transitions are ordered deterministically before the plan fingerprint is
derived. Running the planner twice against unchanged state produces the same
plan and writes nothing.

The service fails closed if affected lineage is missing or contradictory.
Proceeding with a partial dependency set would make the plan fingerprint
precise but scientifically incomplete.

## Write-time guards and the SQLite boundary

The source fingerprint is checked while the execution plan is built. During the
write phase, the source transition uses compare-and-set on its expected
lifecycle or validity state, and every dependent transition checks the mutable
fields that were observed during planning. Losing any guard raises a stale
propagation error and rolls back the transaction.

The current service does not acquire a separate validity claim before planning,
does not hold a validity lease, and does not carry a validity fencing token.
SQLite serializes writers when updates begin; the configured file-backed
runtime uses WAL mode and a bounded busy timeout. The service combines that
database behavior with CAS predicates, event uniqueness, rollback, and
winner-event verification.

Supported application paths do not rewrite the immutable scientific core of a
DataProfile, Evidence, or AnalysisFrame. A future backend, a new mutable source
path, or a plan committed long after construction would require explicit
reevaluation of lock timing and source revalidation. The present guarantees are
not portable by assumption.

## The atomic write set

Depending on the source and current lineage, one transaction may include:

- source invalidation, conflict, or supersession;
- invalidation of downstream Evidence;
- invalidation of affected evaluation controls;
- invalidation of pending or claimed Discovery admission;
- invalidation and review provenance on dependent Discoveries;
- Hypothesis state adjustment or review reason;
- Task review reason without changing Task lifecycle;
- SessionFrame supersession and stale-context marker; and
- insertion of one immutable ValidityEvent containing the committed transition
  manifest.

Persisted proposal decisions remain historical and are not consumed or rewritten
by validity propagation. No successor Evidence, Discovery, Hypothesis, Task, or
SessionFrame is inserted.

Partial commits would create contradictory authority. For example:

```text
Discovery becomes invalid
but an affected SessionFrame remains eligible as current context
```

or:

```text
ValidityEvent says propagation committed
but dependent Evidence and Discovery remain active
```

The service stages every applicable transition and the event in one transaction.
Any exception, lost CAS, missing dependent, uniqueness conflict, or injected
failure rolls back the full write set.

## ValidityEvent is immutable provenance

A ValidityEvent records one authorized validity transition. It allows later
inspection of:

- the source and exact source state targeted;
- the authority identity and scope used;
- the requested event and reason;
- the replacement binding, when present;
- the deterministic affected-target manifest;
- the request and plan fingerprints; and
- the time and committed processing state.

It is not an FCO, Discovery, Evidence, replacement object, mutable status row,
generated summary, or event-bus message. SQLite triggers reject update and
delete of committed validity-event rows.

On replay, the service reconstructs the persisted plan, recomputes its
fingerprint and deterministic event identity, and verifies that every recorded
effect still exists with event provenance. An event row without its complete
effects is rejected as partial rather than treated as success.

## Exact replay

Exact replay exists for an uncertain outcome: the caller may not know whether a
prior attempt committed.

The same idempotency key and request fingerprint must resolve to the same event.
The service:

1. looks for an existing event before checking source freshness;
2. verifies the command against durable authority;
3. checks request identity;
4. verifies the persisted plan and every committed effect; and
5. returns the original event with a replay disposition.

This order is load-bearing. The source is expected to be non-active after a
successful validity transition. Treating that post-state as stale before
looking for the event would break legitimate retry.

## Concurrent exact replay

Two SQLite sessions can begin the same exact command before either sees a
committed event. One obtains the writer outcome. The other may encounter a stale
source during plan construction or lose a later write/uniqueness race.

After rollback, the losing path looks up the winner by idempotency key and
verifies the same request, plan, identity, and complete effects. The observed
result is:

```text
one original commit
+ one verified replay
```

Classification:

```text
A. SAFE AND ENFORCED
```

Focused concurrent tests enforce one event row and the original/replay result
pair. Concurrent incompatible commands against the same source produce one
commit and one stale failure rather than two lifecycle transitions. This is
**Verified on SQLite**, not a distributed coordination guarantee.

## Changed commands fail closed

A changed validity command is not a retry merely because it reuses an
idempotency key.

| Change | Current outcome |
| --- | --- |
| reason | request fingerprint conflict |
| requested event/effect | authority-scope failure or request fingerprint conflict |
| authority grant | authority verification followed by request fingerprint conflict when otherwise valid |
| authenticated principal | permission failure for a user-governed command |
| source identity or expected source fingerprint | authority-scope failure or request fingerprint conflict |
| replacement identity or fingerprint | authority/replacement binding failure or request fingerprint conflict |
| contract version | schema validation rejects versions other than `validity-propagation/v1` |
| persisted event identity, plan, or effect set | replay rejects the event as partial or invalid |

The affected-object plan is not a caller-editable retry field. Exact replay
verifies the committed plan recorded in the immutable event; it does not
recompute a new dependency plan and silently merge new effects into the old
event. A genuinely new validity concern requires a new authorized command and
idempotency identity, subject to the source's current eligibility.

## CAS, claims, leases, and fencing

These terms are not interchangeable.

- Compare-and-set is used directly: each transition succeeds only while its
  expected state and relevant mutable fields still match.
- A validity-owned claim row does not exist.
- A validity-owned lease does not exist.
- A validity-owned fencing epoch does not exist.
- An affected DiscoveryAdmissionClaim may itself be invalidated. Its current
  fencing epoch participates in that dependent CAS so a stale admission owner
  cannot publish after validity commits.

Calling the whole validity path “fenced” obscures the actual guarantee. Current
ownership comes from the application service, SQLite transaction, CAS
predicates, immutable event identity, and verified replay. If validity work
moves to long-running or distributed workers, explicit claims, leases, fencing,
or another ownership protocol must be designed and verified rather than
inferred from the present code.

## Tradeoffs and revisit triggers

The current design favors a closed, synchronous, all-or-nothing transaction.
That makes authority changes immediately coherent in one SQLite database, but
dependency traversal and write-set size grow together.

Revisit the design when:

- another database backend is introduced;
- multiple workers need long-running validity ownership;
- effect plans become too large for one practical transaction;
- graph traversal must cross workspaces or services;
- external indexes or caches hold active scientific state; or
- notification delivery becomes part of the authority cutover.

Future designs may introduce durable claims, chunked planning, explicit
materialized dependency indexes, or distributed coordination. They must retain
exact authority, deterministic effects, stale-owner exclusion, immutable event
provenance, exact replay, changed-command conflict, and atomic visible
authority.

Continue with
[Invalidation and active retrieval](invalidation-and-active-retrieval.md) to see
how committed validity state is enforced at read time.

## Related decision rationale

The invariant-versus-mechanism classification is summarized in
[Design decisions and tradeoffs](design-decisions-and-tradeoffs.md#16-atomic-validity-propagation).
[ADR-005](decisions/ADR-005-atomic-validity-propagation.md) preserves the
decision, rejected alternatives, limitations, and revisit triggers.

## Implementation orientation

The transaction owner is `AtomicValidityPropagationService` under
`src/application/validity/`. Typed contracts are under
`src/schemas/validity/`; dependency traversal and stage-only event persistence
are under `src/repositories/validity/`; the event record is under
`src/db/models/validity.py`.

Focused verification is under `tests/application/validity/`,
`tests/repositories/`, `tests/architecture/`, and `tests/e2e/`.
