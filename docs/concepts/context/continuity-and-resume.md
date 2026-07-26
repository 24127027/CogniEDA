# Context continuity and resume

CogniEDA can preserve an investigation across interactions because its research
state is durable and typed. That is different from restoring an application
session, replaying chat, or automatically reopening a project.

> **Implementation status:** durable research objects, workspace-local
> repository access, SessionFrame read/latest-active selection, bounded context
> projection, and selected claim or lease recovery paths are **Implemented**.
> Their covered persistence behavior is **Verified on SQLite**. The complete
> user-facing continuity workflow is **Partially implemented**. Automatic
> workspace resume and durable Planner chat/checkpoint replay are
> **Unsupported**; parent-task GeneratedViews are a **Design target**.

Continuity is not achieved by remembering everything. It is achieved by
reconstructing a bounded context from state that is still authoritative for the
operation at hand.

## Durable object continuity is not product session resume

The configured workspace database can retain:

- Objectives, DataProfiles, Assumptions, Tasks, and Hypotheses;
- AnalysisFrame and ExecutionRun provenance;
- immutable Evidence and evidence-bound Discoveries;
- user decisions and pending Planner operations;
- execution, evaluation, governance, admission, and validity controls; and
- SessionFrame snapshots.

Those records survive an in-process interaction and can be read by a newly
constructed runtime pointed at the same database. Their identifiers, lifecycle
state, lineage, and transaction metadata provide durable object continuity.

Complete product-level session resume would additionally need to discover the
workspace, select the correct current Objective and frame, restore the intended
user or branch, explain stale state, rebuild presentation state, and expose a
supported UI or API. Current source does not provide that end-to-end bootstrap.

Raw chat restoration is neither implemented nor a substitute. A restored
conversation could contain rejected Tasks, obsolete assumptions, invalidated
claims, and generated prose that never became Evidence.

## The reconstruction sequence available today

A caller that already knows the workspace database can perform a library-level
reconstruction:

```text
open the same workspace-local database
  -> read durable current research state
  -> select an explicit frame or the latest eligible frame
  -> reject a superseded or archived frame
  -> build the operation-specific SessionFrame projection
  -> run repository-backed Discovery retrieval when planning needs it
  -> preserve protected evaluation as a separate repository reconstruction
```

`SessionFrameRepository.get_latest_active` selects the most recently created
active, checkpoint, or handoff frame. It does not filter by application session,
user, Objective, or branch. Current workspace isolation relies on using a
separate configured database. A caller may instead supply an exact frame
identifier to the Planner.

The Planner does not automatically call latest-active lookup during
construction. Its runtime context must carry the SessionFrame identifier for
current Task management or decomposition paths. This makes the library
capability real while keeping automatic workspace resume **Unsupported**.

## Frame reuse, succession, and current authority

A frame is useful only if its status and selected objects remain admissible.
`SessionContextBuilder` rejects superseded and archived frames. For an eligible
frame, it applies mode-specific policy to the stored summaries.

Ordinary Planner progress may copy the selected state into a successor with a
new frame identifier and predecessor link. The earlier snapshot remains
readable. The current implementation normally leaves its frame status unchanged
and relies on recency for latest selection.

Atomic Discovery admission creates a deterministic conclusion frame from the
new Discovery, its Evidence, the accepted DataProfile, and the current
Objective. It is appended in the same transaction as the scientific lifecycle
cutover, but it does not currently form a general predecessor chain with the
Planner frame that led to the work.

Validity propagation can supersede affected frames and add a stale marker. A
later caller must re-read lifecycle authority; it must not trust a cached
SessionFrame summary as proof that the referenced object remains current.
Affected-object planning, replay, concurrency, and authority-change continuity
are reconstructed in [Validity over time](../validity/validity-over-time.md) and
[Atomic validity propagation](../validity/validity-propagation.md).

## What survives process interruption

Reconstructing `CogniEDARuntime` with the same database and newly supplied
deployment adapters restores access to the durable repositories and application
controls. Runtime methods open fresh database sessions for each operation.

Several operational paths are deliberately recoverable from durable state:

- the Planner reconciles durable execution attempts before each configured
  run;
- the runtime exposes execution reconciliation directly;
- execution attempts use durable outbox/inbox, ownership, leases, and fencing;
- evaluation and Discovery admission use durable controls and claims, including
  reclaim or replay checks; and
- approved Planner operations and execution approvals can resume by durable
  identifiers rather than by trusting free-form conversation.

These mechanisms support interruption recovery for their own workflows. They do
not collectively provide deployment-level crash recovery, an automatic worker
loop, or a complete resumed research-session experience.

The Planner's default LangGraph checkpointer is in memory. A process restart
does not restore its message history or checkpoint graph. Durable approval
identifiers allow selected decision paths to reload persisted authority, but
that is narrower than restoring an entire conversation or paused graph state.

## Planner access to reconstructed context

Current Planner Task management and decomposition paths:

1. load the exact frame supplied in runtime context;
2. build Planning Context;
3. select the first projected DataProfile reference;
4. re-read that DataProfile and require current active state;
5. run bounded repository-backed Discovery retrieval; and
6. place eligible and context-only candidates into a typed proposal prompt.

Root-Task motivation additionally requires the DataProfile to be accepted as
ground truth. Decomposition checks active state while later commit validation
protects any selected analytical profile and motivating Discovery from changing
between proposal and approval.

Answer and suggestion nodes remain scaffold-level. The existence of Answer
Context policy therefore does not establish a supported question-answering or
resume product.

## Parent Tasks and GeneratedViews

A parent Task organizes work; it does not produce a Hypothesis, Evidence, or
Discovery. When a user asks for the answer to a parent churn investigation, the
target workflow is:

```text
find terminal analytical descendants
  -> retrieve each descendant's currently active Discovery
  -> retrieve supporting Evidence when presentation needs it
  -> construct a bounded GeneratedView
```

The GeneratedView is a regenerable presentation over current authority. It must
not merge several independent findings into a new durable scientific claim.
After invalidation, the view may be regenerated from the remaining active
Discoveries while the old scientific records remain historical.

This parent-task synthesis is a **Design target**. Current source provides Task
hierarchy, descendant Discoveries through their individual lineage, retrieval
helpers, and the non-authority policy boundary, but no complete GeneratedView
schema, synthesis service, Planner answer path, or user-facing product flow.

Keeping the view separate costs regeneration and makes parent answers less
convenient to cite. Promoting a narrative summary to Discovery would be worse:
no single Hypothesis or Evidence set would justify the combined claim.

## Current continuity boundary

| Capability | Status | Boundary |
| --- | --- | --- |
| durable FCO and provenance reads from the same database | **Implemented** and **Verified on SQLite** | caller already knows the database |
| SessionFrame create/read/list/latest/latest-active | **Implemented** | latest selection is database-local and recency-based |
| Planner successor snapshots | **Implemented** | selected paths only; previous frames usually remain active-status |
| conclusion SessionFrame append | **Implemented** and **Verified on SQLite** | owned by atomic Discovery admission |
| lifecycle exclusion after validity change | **Implemented** and **Verified on SQLite** | durable review signals are **Partially implemented**; notification delivery and automatic context refresh are **Unsupported** |
| execution reconciliation and durable claim recovery | **Implemented** for selected workflows | no automatic worker or daemon |
| automatic workspace or project reopening | **Unsupported** | no product bootstrap |
| restored chat or persistent Planner checkpoint | **Unsupported** | default checkpointing is in memory |
| complete SessionFrame editor and stale-context queue | **Partially implemented** | contracts exist; product surface does not |
| parent-task GeneratedView synthesis | **Design target** | no complete service or answer path |
| persistent semantic index or Graph Miner retrieval | **Deferred** | current retrieval is bounded and lexical |
| multi-user or cross-project continuity | **Unsupported** | no supported governance or retrieval surface |

## Why rebuild from durable state instead of replaying everything

Reconstruction costs repository reads, validation, and bounded selection on each
operation. Chat replay appears cheaper, but it makes the effective input depend
on an untyped historical transcript and hides which statements still have
authority.

Rebuilding from durable state makes authority changes take effect on the next
read. The tradeoff is latency and the need for explicit current-frame policy.
Revisit the design if reconstruction latency becomes material, frames grow
beyond direct projection, or concurrent branches need stronger identity and
selection. Preserve repository-current lifecycle checks and context type safety
in any cache or index added for speed.

## Scaling and future continuity

The current design may need extension when:

- several active DataProfiles require an explicit comparative operation;
- many branches or users require frame ownership and concurrency rules;
- candidate volume makes bounded lexical retrieval insufficient;
- users require an explainable stale-context and conflict queue;
- resume latency requires materialized indexes or incremental reconstruction;
- backend portability changes lifecycle-query or transaction semantics; or
- cross-project knowledge transfer becomes an explicit governed capability.

Semantic ranking, Graph Miner, or a larger context cache may improve retrieval
and latency. None may bypass lifecycle, profile, scope, epistemic-type, or
protected-evaluation boundaries.

The current technical validity sequence is described in
[Validity propagation workflow](../../reference/workflows/validity-propagation.md). Its
canonical temporal-authority and active-context consequences are
[Validity over time](../validity/validity-over-time.md) and
[Active retrieval after invalidation](../validity/active-retrieval-after-invalidation.md).

## Implementation orientation

Runtime composition is under `src/application/runtime.py` and
`src/application/runtime_loader.py`. SessionFrame persistence and projection
are under `src/repositories/research/session_frame.py` and `src/memory/`.
Planner context use is under `src/agents/planner/`; workflow-specific recovery
is under `src/application/`.

Focused verification is under `tests/memory/`, `tests/agents/planner/`,
`tests/application/`, `tests/repositories/`, and `tests/e2e/`.

Selection and checkpoint limits continue in
[SessionFrame scaling and resume limits](session-frame-scaling.md).
The product-process gap continues in
[Product bootstrap](../../operations/product-bootstrap.md).

Continue with the running example in
[Building active context from research state](building-active-context.md).
