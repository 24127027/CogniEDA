# ADR-003: Specialist Scientific Authority Separation

**Status:** Accepted; implemented at the current specialist boundaries.

## Context

Giving an execution adapter authority to interpret its own output collapses
observation, inference, governance, and persistence.

## Decision

Data Explorer has observation authority only. The tool-free Hypothesis Analyst
is the sole specialist author of `DiscoveryProposal` values and receives only a
protected bundle. Neither specialist has governance or persistence authority.

## Consequences

Executor output cannot directly become a Discovery. Proposal authoring still
cannot authorize or materialize the claim.

## Rejected alternatives

A monolithic scientist agent and executor-produced Discovery prose.

## Enforcement

Boundary tests live in
`tests/architecture/test_architecture_enforcement.py`,
`tests/application/evidence/test_evidence_admission.py`, and
`tests/application/evaluation/test_hypothesis_analyst_execution.py`.
