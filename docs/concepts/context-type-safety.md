# Context Type Safety

## Target Design

Context Type Safety means relevance is insufficient. Retrieved context must also have the correct epistemic role for the operation.

## Planning Context

Planning Context may include:

- `Objective`
- proposed or active `Task`s
- active `DataProfile`
- active `Assumption`s
- relevant `Discovery` objects
- relevant `Evidence` summaries
- `SessionFrame` pinned items

Assumptions may guide planning.

## Conclusion Context

Conclusion Context must include only evidence-valid inputs:

- `Hypothesis`
- `DataProfile`
- `AnalysisFrame` provenance
- `Evidence`
- method metadata
- parameters
- decision rule
- uncertainty
- `ValidityEnvelope`
- necessary provenance

Conclusion Context must exclude by default:

- `Assumption`
- rejected `Task`
- completed `Hypothesis`
- raw chat turns
- failed reasoning chains
- unverified `GeneratedView`
- old `DataProfile` unless explicitly requested

## Current Implementation

Current code provides:

- `SessionFrame` summaries with active assumptions, active hypotheses, evidence summaries, stale context, dead ends, and cached tool results.
- `SessionContextBuilder`, which projects a `SessionFrame` into `planning` or `conclusion` context bundles.
- Planning context includes active assumptions when their memory status is eligible.
- Conclusion context excludes assumptions, recent decisions, pending tasks, open questions, stale context, dead ends, and cached tool-result summaries.
- Conclusion context also filters out stale, superseded, rejected, archived, dead-end, overruled, and review-only memory statuses.
- no retrieval engine
- no graph retrieval context mode selector
- no graph-level Conclusion Context constructor
- no epistemic-role field on current artifact models

## Implementation Status

Partially implemented.

The current code enforces a basic Planning Context vs Conclusion Context split for `SessionFrame` snapshots. Full target Context Type Safety remains incomplete because there is no typed retrieval engine, graph policy, `Discovery`, `Task`, `AnalysisFrame`, or epistemic-role field across all artifacts.

## Architectural Risk

If an LLM prompt is built from the raw `SessionFrame` instead of `SessionContextBuilder`, active assumptions can still appear beside evidence summaries. That is acceptable for planning but unsafe for conclusion generation.

## Required Tests When Implemented

Add tests that verify:

- Planning Context may include active assumptions. Implemented for `SessionFrame` projection.
- Conclusion Context excludes assumptions. Implemented for `SessionFrame` projection.
- Rejected tasks do not enter Conclusion Context.
- Completed hypotheses are not retrieved as current knowledge by default.
- Stale evidence and stale data summaries are excluded unless the user requests audit/history. Implemented for `SessionFrame` projection.
