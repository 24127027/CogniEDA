# Discovery governance and admission

A valid `DiscoveryProposal` is still not durable scientific knowledge.
CogniEDA requires an independently authorized decision and one all-or-nothing
materialization transaction.

The boundary answers two different questions:

1. May this exact proposal and evaluation lineage be admitted?
2. Can the complete durable Discovery chain be committed without changing its
   scientific meaning?

Governance answers the first. Discovery admission answers the second. Neither
component evaluates the Evidence or authors replacement wording.

> **Implementation status:** Principal-bound authority records, exact proposal
> decisions, admission claims, replay checks, fencing, compare-and-set guards,
> exact-copy materialization, and rollback are **Implemented** and **Verified on
> SQLite**. A production authentication provider and complete user-facing
> approval workflow are **Unsupported** or **Partially implemented**. No
> cross-database or distributed transaction guarantee is claimed.

## From principal to one admissible proposal

The current authority chain is:

```text
authenticated principal
  -> expiring GovernanceAuthority
  -> current ProposalAuthority reconstructed from repositories
  -> APPROVED | REJECTED | CANCELLED decision
  -> durable admission claim
  -> fenced atomic Discovery admission
```

The grant and the decision carry different bindings.

### Authenticated principal

An authentication adapter resolves an opaque authentication-context identity
to a principal, workspace, session, and authentication time. Callers are not
allowed to supply an arbitrary actor name and have it treated as authenticated.

The repository defines the resolver protocol and verifies the returned
principal. It does not ship a production authentication implementation.

### Expiring GovernanceAuthority

The authority issuer binds a resolved principal to:

- an authority class;
- workspace and session;
- a fixed purpose and operation;
- issuer identity;
- issue and expiry times;
- an authority fingerprint.

For the user-governed path, the current purpose is governed Discovery admission
and the operation is proposal authorization. The grant must be active,
unexpired, and owned by the authenticated principal that records the decision.

The grant is not itself the scientific proposal. Exact proposal and evaluation
identity are bound by the subsequently persisted decision after current
proposal authority is reconstructed.

### ProposalAuthority

Governance reloads the proposal-ready evaluation and rebuilds its protected
bundle. It validates the canonical serialized proposal, then binds:

- evaluation and evaluation-key identity;
- Hypothesis and direct source Task;
- DataProfile;
- proposal, bundle, Evidence-set, and manifest digests;
- the exact Evidence and AnalysisFrame identities;
- proposal contract version;
- evaluation attempt, owner, and fencing epoch.

This prevents an authority grant from being reused as permission for a
different proposal merely because the actor and workspace are the same.

## Decision semantics

Governance records exactly one of the current source outcomes:

```text
APPROVED
REJECTED
CANCELLED
```

An exact retry of the same decision under the same authority returns the durable
decision. A different outcome or authority for the same persisted proposal
conflicts.

### Approval

Approval authorizes only the proposal, bundle, Evidence set, evaluation,
principal, workspace/session, purpose, and operation bound to the decision. It
does not create a Discovery and does not guarantee that admission will succeed.
Admission still revalidates current lifecycle and lineage.

### Rejection

Rejection records that the proposal may not be admitted. It does not contradict
the Hypothesis, negate the Evidence, or create a scientific result. The
proposal and decision remain workflow and governance history.

### Cancellation

Cancellation stops this authorization path without making a judgment about the
claim's truth. No Discovery is materialized.

There is no `MODIFY` decision. The tempting simpler alternative is to allow a
reviewer to edit the proposal and approve the edit. That would give governance
unprotected scientific authorship. Changed scientific content must return
through protected evaluation and receive its own exact decision.

This separation protects the invariant that authorization never manufactures a
claim. The tradeoff is another proposal and decision cycle when wording must
change.

## Why approval and admission are separate

Approval can be recorded before a worker obtains transaction ownership.
Between those moments, Evidence can be invalidated, a Task or Hypothesis can
change state, an authority can expire, or another worker can commit the same
operation.

Treating approval as the write would make a stale decision sufficient to create
knowledge. Instead, admission reconstructs all current authority again and
fails closed when any binding no longer matches.

The tradeoff is that an approved proposal can still conflict at admission time.
That is intentional: authorization is necessary, not sufficient, for a valid
scientific commit.

## The atomic write set

For a new admission, the current transaction commits this conceptual write set:

1. insert the deterministic Discovery;
2. insert the deterministic conclusion SessionFrame;
3. move the source Hypothesis from `READY_FOR_EVALUATION` to `EVALUATED`;
4. move the direct terminal analytical Task from `ACTIVE` to `COMPLETED`;
5. move the selected EvaluationControl from `PROPOSAL_READY` to `COMMITTED`;
6. move the selected DiscoveryAdmissionClaim to `COMMITTED`;
7. consume the exact approved ProposalDecision.

The source contract names these operations:

```text
discovery_insert
hypothesis_evaluated_transition
terminal_task_completed_transition
evaluation_control_committed_transition
admission_claim_committed_transition
authorization_decision_consumed_transition
conclusion_session_frame_insert
```

The order in the manifest is not a license for a partial commit. All effects
belong to one SQLite transaction and must either all commit or all roll back.

The conclusion SessionFrame is appended for continuity and points to the
admitted Discovery and supporting Evidence. It is not an evaluation input and
does not author the claim. Its later context role is explained in
[SessionFrame and active context](../context/session-frame.md).

## Why partial commits would corrupt research state

Consider the running churn example if only some writes succeeded.

### Discovery inserted, Hypothesis still ready

The database would say both “a conclusion exists” and “this test remains ready
to be evaluated.” Another worker could attempt a second proposal for a
Hypothesis that already has durable knowledge.

### Discovery inserted, Task still active

Workflow would invite more execution even though the direct terminal scientific
unit had already produced its one allowed Discovery.

### Discovery inserted, decision not consumed

The same approval could appear reusable. A later retry could not distinguish a
complete exact admission from an orphaned insert.

### Lifecycle committed, Discovery absent

The Task and Hypothesis would appear successfully finalized with no scientific
claim to explain their terminal state.

### Discovery inserted, conclusion SessionFrame absent

Scientific state would exist, but the deterministic completion chain and
replay proof would be incomplete. A later operation could not verify the exact
committed handoff.

### Admission claim committed, proposal changed

The claim would certify a different scientific operation than the Discovery it
purports to own.

These are not merely cleanup problems. They are contradictory durable accounts
of what the project knows. Atomic admission protects one coherent scientific
cutover.

The cost is a wider transaction touching several bounded contexts. That design
should be revisited if those contexts move to separate services, but a
replacement must preserve one observable all-or-nothing authority transition.

## Exact proposal-copy during materialization

Admission reloads the canonical persisted proposal and validates it against the
current repository-built protected bundle. It constructs the Discovery by
copying:

- claim;
- epistemic status;
- scope;
- exact Evidence identities;
- complete validity basis;
- uncertainty from that validity basis;
- limitations;
- invalidators from that validity basis.

Application-owned additions are deterministic identity, creation time,
lifecycle/review metadata, and transaction bindings. The existing
`analysis_intent` field is copied unchanged from the bound source Hypothesis as
lineage metadata. Scientific content is not paraphrased, normalized, truncated,
reordered, or defaulted.

Why this matters is covered in [Scientific authority](scientific-authority.md).
Focused tests compare every persisted scientific field with the proposal, so
the rule is not limited to claim wording.

## Exact retry

A caller may lose the response after commit and safely retry the same binding.
The service reconstructs the expected deterministic Discovery, claim, proposal,
bundle, decision, lifecycle chain, and conclusion SessionFrame.

If the complete committed chain matches, it returns the same Discovery and an
idempotent replay disposition. It does not insert a duplicate or repeat the
decision.

This behavior protects at-least-once callers from uncertain acknowledgement.
Its cost is deterministic identity and persisted fingerprints for more than the
Discovery row alone.

## Changed retry is a conflict

A retry is not “the same operation” when any authoritative binding changes,
including:

- proposal content or proposal digest;
- Evidence identities, Evidence fingerprints, or Evidence-set digest;
- AnalysisFrame or ExecutionRun lineage;
- DataProfile;
- Hypothesis, direct terminal Task, or their relationship;
- bundle, manifest, evaluation key, or contract version;
- evaluation attempt, owner, or fence;
- principal, authority, workspace/session, purpose, or operation;
- governance outcome, decision identity, or decision fingerprint;
- admission-plan fingerprint.

Changed content must fail closed or conflict. Returning the earlier Discovery
as though it represented the new binding would hide an authority change;
creating another Discovery would violate one-Discovery-per-Hypothesis
cardinality.

## Claim, lease, fencing token, and compare-and-set

Concurrency controls answer different failure questions.

### Claim

The durable admission claim records which evaluation and decision are awaiting
or have completed admission. It binds proposal, bundle, and admission-plan
fingerprints before a worker executes the scientific transaction.

### Lease

A worker claims that record for a bounded time. The lease prevents indefinite
ownership after process failure and makes reclaim explicit.

### Fencing token

Each successful claim or reclaim advances the fencing epoch and issues a fresh
opaque token. A worker holding an older lease cannot commit or cancel after a
new owner takes over.

### Compare-and-set

Guarded updates state what must still be true at write time: Hypothesis
`READY_FOR_EVALUATION`, Task `ACTIVE`, EvaluationControl `PROPOSAL_READY`,
matching digests, matching evaluation fence, unconsumed decision, and current
claim ownership. A zero-row update means that authority was lost and the
transaction conflicts.

Claims alone would not prevent a stale process from writing. Leases alone would
not bind scientific content. Fencing alone would not prove current lifecycle.
Compare-and-set alone would not provide recoverable work ownership. The
mechanisms work together.

The tradeoff is substantial operational state and more race cases. The redesign
trigger is a production distributed worker or multi-database deployment, where
equivalent ownership and cutover semantics must be proven rather than assumed.

## SQLite transaction boundary

The current service acquires SQLite's writer lock through guarded writes,
reconstructs the complete authority again under that lock, stages the entire
write set, and commits once. Injected failures after every transaction stage are
tested to roll back the Discovery, frame, lifecycle, control, claim, and
decision effects together.

Current guarantees are therefore:

- **Implemented** for the guarded application service;
- **Verified on SQLite** for atomicity, exact replay, changed-binding conflict,
  stale-lease fencing, rollback, and covered races;
- **Unsupported** as a general cross-database, distributed-transaction, or
  cross-service guarantee.

SQLite-specific triggers and uniqueness constraints add defense in depth, but
they do not justify claims about another database backend.

## Failure and stopping behavior

| Condition | Durable consequence |
| --- | --- |
| exact approved proposal and current lineage | full Discovery chain commits |
| exact retry after uncertain response | existing complete chain is returned |
| changed binding | conflict; no partial scientific write |
| stale or expired lease | old owner is fenced; eligible work may be reclaimed |
| injected or database failure before commit | transaction rolls back |
| rejected or cancelled governance decision | no admission eligibility and no Discovery |
| expired/inactive authority before new admission | admission fails closed |
| invalidated Evidence or provenance | bundle reconstruction/admission fails closed |
| partial pre-existing chain | conflict rather than repair by guesswork |

Application services do not repair an authority failure by inventing substitute
scientific text. A new valid chain must be established through the owning
boundary.

## Design costs and revisit triggers

| Decision | Invariant protected | Tradeoff | Revisit trigger |
| --- | --- | --- | --- |
| principal resolution before authority | actor identity is not caller-authored | deployment needs an authentication adapter | production identity system is selected |
| expiring scoped grant plus exact decision | actor scope and proposal identity remain distinct and traceable | more governance records | a simpler mechanism proves the same bindings |
| no governance editing | decision authority cannot become proposal authority | wording changes require reevaluation | edited proposals can be independently protected |
| atomic seven-effect admission | durable research state cannot split | wide transaction and lock contention | contexts move across services or backend changes |
| deterministic exact replay | uncertain responses do not duplicate knowledge | fingerprints and replay verification | an equivalent content-addressed protocol replaces it |
| claim, lease, fence, and CAS | stale/concurrent owners cannot commit | operational complexity | distributed ownership is implemented and verified |
| SQLite-qualified guarantees | documentation matches evidence | backend portability remains limited | focused verification exists for another backend |

## Current limitations

- The authentication resolver is an injected protocol; a production provider is
  **Unsupported**.
- Governance services exist in-process, but the complete interactive proposal
  review and approval experience is **Partially implemented**.
- Admission uses a single SQLite transaction. Distributed execution and
  cross-database atomicity are **Unsupported**.
- External Data Explorer effects occur before these scientific transactions and
  remain at-least-once.
- Conclusion SessionFrame reconstruction and multi-session continuity are
  **Deferred** to their own documentation; this page covers only the atomic
  append.

## Related decision rationale

The epistemic reason for independent governance, exact proposal-copy, and one
admission transaction is summarized in
[Design decisions and tradeoffs](../../design-decisions/index.md).
[Scientific authority by role](../../design-decisions/scientific-authority-by-role.md) owns authority
separation, and
[Creating Discoveries after authorization](../../design-decisions/creating-discoveries-after-authorization.md) owns atomic
materialization.

## Implementation orientation

Authority issuance, proposal reconstruction, decision fingerprints, and
decision recording are under `src/application/governance/` and
`src/schemas/governance/`.

Admission plans, claims, replay, fencing, exact materialization, and transaction
ownership are under `src/application/discovery/` and
`src/schemas/discovery/`.

Focused verification is under `tests/application/governance/` and
`tests/application/discovery/`.

For the full scientific handoff, read
[Execution to Discovery](execution-to-discovery.md).
