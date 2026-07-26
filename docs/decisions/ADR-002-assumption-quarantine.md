# ADR-002: Assumption quarantine

**Decision classification:** Foundational invariant.

**Implementation status:** **Implemented** for the protected
Conclusion/Discovery synthesis path.

## Context

Analytical planning often requires beliefs about domain meaning, data quality,
expected mechanisms, or practical constraints. CogniEDA preserves those beliefs
as `Assumption` objects so they can guide planning and later be reviewed.
Preservation does not make an Assumption observed fact.

## Problem

If an Assumption enters conclusion synthesis as a premise, the evaluator can
produce a claim that appears evidence-bound while actually depending on an
unverified belief. Prompt instructions such as “do not rely on assumptions” are
not a type boundary and cannot prove what influenced the proposal.

## Failure mode

A planning expectation is repeated in the proposed claim, weak Evidence is
interpreted to agree with it, or an earlier Discovery is used to confirm itself.
The persisted Discovery then launders context into scientific authority even
though the governance record and provenance look valid.

## Tempting alternatives

- pass all active project memory to the evaluator and rely on prompting;
- include Assumptions but label them “unverified”;
- let a SessionFrame or caller assemble an arbitrary evaluation prompt;
- use existing Discoveries as default synthesis premises; or
- automatically invalidate or rewrite an Assumption when a new Discovery
  disagrees with it.

Each alternative collapses planning context, protected scientific context, or
post-admission review.

## Decision

Assumptions may enter Planning Context but must not enter
Conclusion/Discovery Synthesis Context. Existing Discoveries, SessionFrames,
raw chat, caller-supplied generic context, rejected Tasks, and failed reasoning
chains are also excluded from the protected bundle.

The Hypothesis Analyst receives a closed, repository-reconstructed
`DiscoverySynthesisBundle` containing only the bounded Hypothesis, accepted
DataProfile, AnalysisFrame provenance, admitted Evidence, method and parameter
metadata, decision rule, uncertainty, validity basis, and necessary provenance.

Only after a Discovery is admitted may it be compared with Assumptions. A
contradiction is a review signal; it does not rewrite, delete, validate, or
invalidate either object automatically. Replacing an Assumption is also not a
validity cascade over scientific claims.

## Invariant protected

An Assumption can guide what to investigate but cannot support what CogniEDA
concludes. Every Discovery premise is reconstructable from protected typed
scientific state.

## Current implementation

`src/schemas/evaluation/bundle.py` defines a closed model with no Assumption,
Discovery, SessionFrame, chat, or generic-context channel.
`src/application/evaluation/bundle_builder.py` constructs it from repositories
and validates the eligible terminal analytical path before evaluation.
The Analyst boundary accepts that bundle rather than a caller-authored prompt.

Architecture and application tests reject unsafe fields, alternate context
construction, parent-Task evaluation, stale scientific inputs, and dependencies
that would let protected evaluation import generic memory or planning state.

## Tradeoffs

Protected synthesis can be less conversational and cannot exploit every piece of
project context. Bundle construction requires more repository reads and
validation. In exchange, the proposal has a finite, auditable premise set and
does not depend on the evaluator remembering prompt caveats.

## Known limitations

- A generic SessionFrame projection named for Discovery synthesis still exists
  as a **Known deviation**. Architecture checks prevent that projection from
  entering the protected evaluation path.
- Assumption comparison is post-admission review, not an automated scientific
  adjudication system.
- Rich product workflows for assumption contradiction, replacement, and
  follow-up are **Partially implemented**.
- Unsupported direct model invocation is outside the protected application
  boundary.

## Risks

Future developers may add a flexible metadata or context field that recreates
the unsafe channel under a different name. Another risk is treating
post-admission contradiction as proof that an Assumption is false beyond the
Discovery's scope.

## Revisit triggers

New assumption categories or formally observed priors may require distinct
types, but only with explicit authority and admissibility rules. Provider or
prompt changes may alter serialization; they do not justify weakening the
closed-bundle boundary.

## Consequences for future work

New evaluator inputs must be typed, scientifically necessary, and reconstructable
from authoritative state. SessionFrame and retrieval work must never bypass the
bundle builder. Assumption review UI must present contradiction as a scoped
signal and require an explicit user decision before changing planning state.

## Related canonical concepts

- [Design decisions and tradeoffs](../design-decisions-and-tradeoffs.md)
- [Protected evaluation context](../protected-evaluation-context.md)
- [Scientific authority](../scientific-authority.md)
- [Governance and Discovery admission](../governance-and-discovery-admission.md)
- [Validity over time](../validity-over-time.md)

## Implementation orientation

Start with `src/schemas/evaluation/bundle.py`,
`src/application/evaluation/bundle_builder.py`, and the Hypothesis Analyst
application boundary. Focused enforcement lives under
`tests/application/evaluation/` and
`tests/architecture/test_architecture_enforcement.py`.
