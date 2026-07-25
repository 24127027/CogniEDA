# Evaluation Application Package

Canonical references: [Scientific Specialist Contracts](../../../docs/architecture/scientific-specialist-contracts.md)
and [Evidence to Discovery](../../../docs/workflows/evidence-to-discovery.md).

`EvaluationTransitionService` owns durable `EvaluationControl` enqueue, claim,
proposal/failure publication, retry, cancellation, invalidation, and conflict
transitions. `build_synthesis_bundle` reconstructs a closed
`DiscoverySynthesisBundle` from repositories; the protected Analyst runner
receives only that bundle and publishes a typed proposal or failure.

This package does not record user decisions, materialize Discoveries, or admit
Assumptions/generic context into synthesis.

Primary verification: `tests/application/evaluation/test_synthesis_bundle.py`,
`test_bundle_digest.py`, and `test_hypothesis_analyst_execution.py`.
