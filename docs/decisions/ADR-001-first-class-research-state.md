# ADR-001: First-Class Research State Model

**Status:** Accepted; implemented for the current schema/persistence boundary.

## Context

Raw chat history and generic vector memories cannot preserve scientific identity,
lifecycle, scope, or provenance.

## Decision

CogniEDA defines exactly eight First-Class Objects: `Objective`, `DataProfile`,
`Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.
Workflow state, provenance, caches, filesystem boundaries, and generated views
are explicitly non-FCO.

## Consequences

Scientific claims must enter through typed, evidence-bound state. New durable
records require an explicit classification before implementation.

## Rejected alternatives

Generic chat logs, untyped JSON memories, and vector-only knowledge stores.

## Enforcement

Schemas live under `src/schemas/research`, `src/schemas/evidence`, and
`src/schemas/discovery`. The explicit model facade and definition-ownership checks
are exercised by `tests/db/test_s3b_sqlite_schema_equivalence.py` and
`tests/architecture/test_architecture_enforcement.py`.
