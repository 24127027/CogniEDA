# Scientific authority by role

Decision ID: D-003

**Decision classification:** Durable architectural decision.

**Implementation status:** **Implemented** at the supported specialist,
governance, and persistence boundaries.

## Context

Producing a durable scientific claim requires computation, interpretation,
authorization, and persistence. These are different powers. A component that
owns all four can convert its own mistakes, prompt injection, or implementation
shortcuts into authoritative knowledge without an independent boundary.

## Problem

CogniEDA needs useful model-assisted analysis without allowing an executor to
interpret its own output, an evaluator to approve its own claim, governance to
author scientific wording, or persistence code to “improve” an approved
proposal.

## Failure mode

Data Explorer returns conclusion prose; the Planner inserts it as a Discovery;
the application silently strengthens the scope or wording; or governance edits
the claim while recording an approval. The final row has no trustworthy answer
to who observed, who inferred, who authorized, and who copied.

## Tempting alternatives

- use one general “scientist” agent for execution through persistence;
- let Data Explorer emit Evidence and a Discovery together;
- give the Hypothesis Analyst tools or repository writes;
- let governance normalize or rewrite proposals;
- let the application repair wording before insertion; or
- treat the Planner as a scientific writer.

These designs are simpler to orchestrate but make authority laundering a
supported path.

## Decision

Scientific authority is separated:

- **Data Explorer** has computation and observation authority only. It returns
  observation-shaped contracts and cannot author interpretation.
- **Hypothesis Analyst** has proposal authorship only. It is tool-free, receives
  the protected synthesis bundle, and returns a typed `DiscoveryProposal`.
- **Governance** accepts or rejects the exact proposal and records decision
  authority. It does not author or revise the claim.
- **Application admission** materializes the accepted proposal and performs
  lifecycle transitions. It does not have scientific authorship.
- **Planner** coordinates governed operations; it does not create Discovery
  content.

Materialization uses exact proposal-copy. Claim, scope, status, Evidence
references, uncertainty, validity basis, and scientific provenance are copied
without semantic rewriting. The application may add deterministic persistence
envelope fields such as identity, timestamps, lifecycle state, transaction
metadata, and proposal lineage; those fields do not change the approved
scientific content.

## Invariant protected

No single specialist can observe, infer, authorize, and persist a scientific
claim. The admitted Discovery is exactly the scientific proposal governance
approved.

## Current implementation

Data Explorer output models reject interpretation and authority fields.
Evidence admission imports observation contracts and stops before evaluation.
The Hypothesis Analyst is bound to the closed
`DiscoverySynthesisBundle`. Governance records decisions and proposal digests.
`AtomicDiscoveryAdmissionService` performs exact-copy materialization, and
public or Planner-side Discovery creation fails closed.

Dependency-direction and source-shape tests prevent alternate writers and unsafe
authority channels. Application tests compare proposal and Discovery scientific
fields and cover changed-proposal, stale-decision, and replay failures.

## Tradeoffs

The pipeline requires more typed handoffs, digests, validation, and failure
states. A rejected proposal cannot be silently repaired; it must return through
an explicit authoring and governance cycle. This costs latency and orchestration
complexity but makes authority reviewable.

## Known limitations

- The complete production Planner, executor graph, service, worker, and user
  review experience are **Unsupported**.
- Boundary enforcement proves supported source paths, not the impossibility of
  unsupported direct database access.
- Exact-copy applies to scientific proposal fields; deterministic persistence
  envelope fields are necessarily application-authored.
- Provider behavior remains an operational concern even when schema and
  authority boundaries reject malformed output.

## Risks

A future convenience adapter could reintroduce interpretation in an observation
metadata field. A “copy-editing” governance or application layer could alter
meaning while preserving superficial field equality. New schemas therefore need
semantic as well as structural review.

## Revisit triggers

Model providers, execution engines, or governance interfaces may change.
Authority roles may be split further if risk increases. They may be combined
only if the replacement still exposes independent, enforceable observation,
authorship, authorization, and persistence boundaries.

## Consequences for future work

Every new specialist must declare its authority. New output fields must be
classified as observation, proposal, governance, or persistence envelope.
Retries and edits must create a new proposal/decision cycle rather than mutate
the approved scientific content in flight.

## Related canonical concepts

- [Design decisions and tradeoffs](index.md)
- [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md)
- [Protected evaluation](../concepts/scientific-lifecycle/protected-evaluation.md)
- [Discovery governance and admission](../concepts/scientific-lifecycle/discovery-governance-and-admission.md)
- [Creating Discoveries after authorization](creating-discoveries-after-authorization.md)

## Implementation orientation

Start with `src/agents/executor/`, `src/application/evidence/`,
`src/schemas/evaluation/`, `src/application/evaluation/`,
`src/application/governance/`, and `src/application/discovery/`. Enforcement is
concentrated under `tests/architecture/`, `tests/application/evidence/`,
`tests/application/evaluation/`, `tests/application/governance/`, and
`tests/application/discovery/`.
