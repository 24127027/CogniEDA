# ADR-002: Assumption Quarantine in Synthesis Contexts

**Status:** Accepted; structurally enforced for protected evaluation.

## Context

Assumptions may guide planning, but using them as empirical premises would turn
unverified beliefs into scientific claims.

## Decision

Conclusion/Discovery synthesis excludes `Assumption`, existing `Discovery`,
`SessionFrame`, raw chat, and caller-supplied generic context. The Hypothesis
Analyst receives only the closed `DiscoverySynthesisBundle`.

## Consequences

Assumptions can be compared with a Discovery only after admission to raise a
review signal; the comparison does not rewrite either object.

## Rejected alternatives

Soft-prompt assumption context and embedding assumptions into proposed claim
text.

## Enforcement

`src/schemas/evaluation/bundle.py` has no unsafe context channel and
`src/application/evaluation/bundle_builder.py` reconstructs the bundle from
repositories. `tests/application/evaluation/test_synthesis_bundle.py` and
`tests/application/evaluation/test_bundle_digest.py` verify the exclusion.
