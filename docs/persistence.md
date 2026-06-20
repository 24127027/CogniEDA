# Persistence Notes

## Current Scope

CogniEDA currently uses a local SQLModel-backed artifact store intended to support contract-first development of the core analytical artifacts and the current context-frame model.

The persistence layer is deliberately narrow:

- artifact-specific repositories stay thin and typed
- append-only artifacts remain append-only at the repository surface
- explicit cross-artifact relations use normalized association tables where integrity matters
- `SessionFrame` stores context-memory snapshots, not business logic

## Runtime Source of Truth

- The SQLModel store is the operational runtime source of truth for all first-class artifacts.
- Git-tracked JSON files under `artifacts/dataset_assets/` and `artifacts/data_profiles/` are reviewable metadata mirrors and examples for dataset lineage and profile snapshots.
- The repository does not currently maintain Git-tracked JSON mirrors for assumptions, hypotheses, evidence, decisions, or session frames by default.

## Current Invariants

- `DatasetAsset` is unique by `project_id + name + version`.
- SQLite foreign keys are enabled on connect.
- `Evidence` is the source of truth for links from evidence to assumptions, hypotheses, and decisions.
- Hypothesis-to-evidence semantics are stored as typed outcomes, not inferred from free text.
- Dataset lineage supports multiple upstream assets plus explicit `lineage_steps`.
- `SessionFrame` persists:
  - frame topic, status, and outcome
  - branch and checkpoint metadata
  - stale-context markers
  - dead-end notes
  - cached tool-result metadata
  - frame-level invalidation rules

## Relation Storage Strategy

Use normalized association tables for:

- dataset lineage links
- hypothesis-to-assumption links
- hypothesis-to-dataset links
- evidence-to-assumption links
- evidence-to-hypothesis evaluation links
- evidence-to-decision links
- decision-to-assumption links
- decision-to-hypothesis links

Use JSON columns for:

- typed profile payloads such as schema summaries and quality flags
- typed context-frame payloads such as dataset summaries, stale-context markers, dead ends, cached tool results, and frame invalidation rules
- structured method parameters and evidence result payloads
- lineage-step details

## Known Boundaries

- The project still lacks a migration workflow. `init_db()` is sufficient for local scaffold refreshes and tests, but schema evolution is not yet managed through formal migrations.
- No persistent memory graph is stored yet.
- No background invalidation or cache-expiration executor exists yet; invalidation is recorded as typed metadata for future services to consume.
