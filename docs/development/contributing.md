# Contributing

## Development Principles

- Preserve CogniEDA as a governed research-state system.
- Do not turn conversation history into durable knowledge.
- Do not promote workflow state, provenance, cache, filesystem artifacts, or generated views into FCOs.
- Prefer explicit schemas, validators, lifecycle guards, and tests.
- Keep changes scoped to the layer they belong to: FCO, workflow state, provenance, cache, filesystem artifact, or generated view.

## Before Changing Code

1. Inspect existing schema, repository, and planner patterns.
2. Classify the feature using the target architecture.
3. Check [Implementation Gap Analysis](../architecture/implementation-gap-analysis.md).
4. Decide whether the change converges toward the target architecture or belongs in provenance/cache/runtime infrastructure.
5. Add or update tests for each invariant touched.

## Before Changing Docs

1. Inspect the relevant code first.
2. Label current implementation and target design separately.
3. Update the gap analysis when drift is found.
4. Do not claim a target invariant is implemented unless code or tests confirm it.
5. Update `README.md` only with verified commands and implemented features.
6. Update `AGENTS.md` when target invariants change.

## Architectural Guardrails

- `Workspace` is a filesystem/runtime boundary, not an FCO.
- `Question` is UI input that becomes a `Task`.
- `AnalysisFrame`, `PlannerOperation`, and `ExecutionRun` are provenance/runtime records.
- `GeneratedView` is runtime output, not `Discovery`.
- `EvidenceCacheEntry` is cache.
- `Assumption` may guide planning but must be excluded from Conclusion Context.
- `Evidence` and `DataProfile` are immutable.
- `Discovery` requires Evidence and `validity_basis`.
