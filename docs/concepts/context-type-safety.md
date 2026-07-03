# Context Type Safety

## Target Design

Context Type Safety means relevance is insufficient. Retrieved context must also have the correct epistemic role for the operation.

## Planning Context

Planning Context may include:

- `Objective`
- active `Task`s and proposed task operations
- active `DataProfile` summaries
- active `Assumption`s
- relevant `Discovery` objects
- relevant `Evidence` summaries
- `SessionFrame` pins

Assumptions may guide planning.

## Conclusion Context

Conclusion Context must include only evidence-valid inputs:

- `Hypothesis`
- `DataProfile`
- `AnalysisFrame` provenance/reference
- `Evidence`
- method metadata
- parameters
- decision rule
- uncertainty
- validity basis
- necessary execution provenance

Conclusion Context must exclude by default:

- `Assumption`
- rejected or inactive `Task`
- completed `Hypothesis`
- raw chat turns
- failed reasoning chains
- unverified `GeneratedView`
- generic summaries

## Current Implementation

Current code provides:

- `SessionFrame` summaries with DataProfiles, Tasks, active assumptions, active hypotheses, Discoveries, Evidence, user-decision provenance, stale context, dead ends, and cached tool results.
- `SessionContextBuilder`, which projects a `SessionFrame` into `planning` or `conclusion` context bundles.
- Planning context includes active assumptions.
- Conclusion context excludes assumptions, tasks, user decisions, pending tasks, open questions, stale context, dead ends, and cached tool-result summaries.
- Conclusion context filters by safe memory status and active profile/evidence lifecycle.
- no retrieval engine
- no graph retrieval context mode selector
- no graph-level Conclusion Context constructor

## Implementation Status

Partially implemented.

The current code enforces a basic Planning Context vs Conclusion Context split for `SessionFrame` snapshots. Full target Context Type Safety remains incomplete because there is no typed graph retrieval engine or retrieval policy.

## Architectural Risk

If an LLM prompt is built from the raw `SessionFrame` instead of `SessionContextBuilder`, active assumptions can still appear beside evidence summaries. That is acceptable for planning but unsafe for conclusion generation.
