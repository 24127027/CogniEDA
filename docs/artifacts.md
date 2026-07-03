# Artifact Notes

This file is retained as a legacy entry point. The current FCO contract is documented in [architecture/first-class-objects.md](architecture/first-class-objects.md).

## Current Implementation

Current Pydantic schemas and repositories exist for:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

Typed `UserDecision` records exist as provenance, not scientific knowledge.

## Current Storage Split

- The workspace-local SQLModel store is the current operational source of truth.
- `artifacts/data_profiles/` contains Git-tracked DataProfile mirror templates for review.
- Physical datasets live under `data/`.

See [architecture/implementation-gap-analysis.md](architecture/implementation-gap-analysis.md) for remaining gaps and architectural risk.
