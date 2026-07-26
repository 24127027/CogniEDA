# ADR-004: Atomic Discovery admission

**Decision classification:** Durable architectural decision.

**Implementation status:** **Verified on SQLite** for the supported admission
path.

## Context

An approved `DiscoveryProposal` becomes durable knowledge only when several
records agree: the Discovery exists, its Hypothesis is evaluated, its terminal
Task is complete, the evaluation control is committed, the admission claim is
committed, the conclusion SessionFrame exists, and the governance decision is
consumed.

## Problem

Independent writers or commits can expose half-admitted knowledge. Retrying an
ambiguous failure can then duplicate a Discovery, consume a decision twice, or
bind a proposal to a different scientific path.

## Failure mode

A Discovery row commits while its Task remains active; a governance decision is
consumed without a Discovery; a stale worker wins after its lease changes; or a
retry with modified proposal content is accepted as if it were exact replay.
Retrieval then sees scientific authority that the workflow cannot justify.

## Tempting alternatives

- expose public `DiscoveryRepository.create()`;
- let the Planner or coordinator insert rows directly;
- commit each repository transition independently;
- rely only on application pre-checks before writing;
- make retries “best effort” without identity and content comparison; or
- publish a queue event before the database state is coherent.

These choices distribute transaction ownership and leave concurrency semantics
implicit.

## Decision

`AtomicDiscoveryAdmissionService` is the sole supported transaction owner for
Discovery materialization. `DiscoveryAdmissionCoordinator` is the supported
runtime entry point.

One transaction:

1. verifies the accepted governance decision and exact proposal identity;
2. verifies eligible terminal Task, Hypothesis, Evidence, evaluation control,
   and admission-claim state;
3. inserts the exact proposal-copy Discovery;
4. creates the conclusion SessionFrame;
5. marks the Hypothesis evaluated and the terminal Task complete;
6. commits evaluation control and the fenced admission claim; and
7. consumes the governance decision exactly once.

The transaction uses database uniqueness, compare-and-set conditions, proposal
digests, claim identity, fencing epoch, and exact replay checks. Same-command
replay returns the existing committed result. Changed content or stale
authority conflicts rather than becoming a second interpretation.

Parent Tasks are ineligible. They do not produce Hypotheses or Discoveries.
Inconclusive or insufficient Evidence can still support a scientifically
correct scoped proposal; technical failure or rejected governance produces no
Discovery.

## Invariant protected

There is no supported visible state in which only part of a Discovery admission
has committed. Scientific cardinality, workflow completion, proposal identity,
and governance authority change together.

## Current implementation

The coordinator and transaction owner live under
`src/application/discovery/`. Repository staging methods participate in the
service-owned transaction; public Discovery creation fails. SQLite constraints
and triggers reinforce proposal identity, unique Hypothesis-to-Discovery
cardinality, claim fencing, and exact decision consumption.

Focused tests cover rollback at injected failure points, exact replay, changed
replay conflict, stale claims, governance binding, proposal-copy equality,
cardinality, parent exclusion, and concurrent races. Architecture tests confine
the supported writer.

## Tradeoffs

The service is deliberately broad because the consistency unit spans multiple
repositories. It requires backend-aware transaction semantics and makes partial
progress unavailable as a recovery strategy. The benefit is one explicit
commit point and deterministic replay.

## Known limitations

- Atomicity and concurrency behavior are **Verified on SQLite**, not claimed for
  every database backend.
- The current service and trigger arrangement is a current-stage mechanism;
  repository or transaction packaging may change.
- No production service/worker bootstrap exposes the full workflow yet.
- Unsupported direct SQL remains outside the guarded application boundary.

## Risks

A future repository may commit independently, or a new field may be omitted
from proposal identity and replay comparison. Backend migration could also
weaken isolation, uniqueness, or trigger assumptions while leaving tests
apparently green on SQLite.

## Revisit triggers

Revisit the mechanism for another backend, multiple writer services,
distributed transactions, or an outbox-driven external side effect. Preserve a
single authoritative admission decision, exact scientific identity, atomic
visible state, and deterministic replay semantics.

## Consequences for future work

New admission side effects must either join the transaction or be driven from a
durable post-commit record without changing scientific truth. Repositories must
not regain an independent public Discovery writer. Backend ports require
equivalent concurrency and rollback tests before their guarantees are
documented.

## Related canonical concepts

- [Design decisions and tradeoffs](../design-decisions-and-tradeoffs.md)
- [Governance and Discovery admission](../governance-and-discovery-admission.md)
- [Scientific authority](../scientific-authority.md)
- [From question to Discovery](../from-question-to-discovery.md)
- [ADR-003: Separated scientific authority](ADR-003-specialist-scientific-authority.md)

## Implementation orientation

Start with `src/application/discovery/`, the participating repositories, claim
and governance schemas, and SQLite models/triggers under `src/db/`. Focused
verification lives under `tests/application/discovery/`,
`tests/application/governance/`, `tests/repositories/`, `tests/e2e/`, and
`tests/architecture/test_architecture_enforcement.py`.
