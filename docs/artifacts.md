# Artifact Notes

This file is retained as a legacy map for the current scaffold. The target FCO contract is documented in [architecture/first-class-objects.md](architecture/first-class-objects.md).

## Current Implementation

Current Pydantic schemas and repositories exist for:

- `Project`
- `DatasetAsset`
- `DataProfile`
- `Assumption`
- `Hypothesis`
- `Evidence`
- `DecisionLog`
- `SessionFrame`

These are real current implementation artifacts.

## Target Architecture

The final target FCO set is:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

`Project`, `DatasetAsset`, and `DecisionLog` are current scaffold artifacts, but they are not target FCOs. Treat this as implementation drift unless the project owner explicitly revises the target design.

## Current Storage Split

- The SQLModel store is the current operational source of truth.
- `artifacts/dataset_assets/` and `artifacts/data_profiles/` contain Git-tracked metadata mirror templates for review.
- Other current artifacts are DB-backed in the scaffold.

See [architecture/implementation-gap-analysis.md](architecture/implementation-gap-analysis.md) for mismatches and architectural risk.
