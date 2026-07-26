# Validity and Invalidation

> **Implementation status:** supported propagation commands are
> **Implemented** and **Verified on SQLite**. The in-process runtime facade is
> **Implemented**; a general production validity-authority issuer and
> production identity provider are **Unsupported**.

Canonical reader explanations are
[Validity over time](../validity-over-time.md),
[Atomic validity propagation](../atomic-validity-propagation.md), and
[Invalidation and active retrieval](../invalidation-and-active-retrieval.md).
This page retains the concise source-oriented reference.

## Command and authority

`ValidityPropagationCommand` is a versioned, frozen request binding:

- source type/id and expected state;
- server-computed source fingerprint;
- event type and reason;
- durable authority ID plus workspace/session scope;
- idempotency key;
- optional replacement identity/fingerprint.

`AtomicValidityPropagationService` reloads and fingerprints the source, verifies the immutable
`GovernanceAuthorityRecord`, checks event/source allowlists and principal or trusted-producer
scope, discovers dependents, derives a deterministic plan, and executes it atomically.

## Supported sources and effects

Supported events cover DataProfile invalidation/supersession, Evidence
invalidation/supersession/conflict, AnalysisFrame invalidity, ExecutionRun conflict, and
AnalysisFrame/ExecutionRun provenance corruption.

The write set may transition the source plus dependent Evidence, EvaluationControl, active
DiscoveryAdmissionClaim, Discovery, Hypothesis, Task review metadata, and SessionFrame. Tasks are
kept in their lifecycle state but gain review reasons. Pre-Discovery source loss moves a ready
Hypothesis to `AWAITING_ADDITIONAL_EVIDENCE`; post-Discovery dependencies are invalidated.
Affected SessionFrames become `SUPERSEDED`.

## Replay and concurrency

The immutable ValidityEvent records the request fingerprint, plan fingerprint, complete transition
manifest, authority, and committed state. Exact replay verifies the complete persisted effects and
returns the original event. A changed command under the same idempotency key conflicts.
Concurrent exact commands produce one commit and one verified replay; incompatible commands have
one winner. Source and dependent writes use compare-and-set guards; validity has no separate
claim, lease, or fencing token. Failure at any staged transition rolls back the source and event.

## Retrieval and history

Invalidated scientific records remain durable for historical trace. Active retrieval excludes
invalidated Discoveries and superseded frames. No event bus or persistent retrieval index is
notified; exclusion is enforced by persisted state and query policy.

## Limitations

**Known deviation:** a SessionFrame containing an affected Discovery only in `user_pins` may remain
active-status, although repository-current retrieval still excludes the invalid Discovery.

**Unsupported:** no general production validity-authority issuer or identity provider is checked
in. All transaction and trigger guarantees are SQLite-only.
