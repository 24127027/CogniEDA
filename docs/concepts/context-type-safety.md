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

## Discovery Synthesis Context

Discovery Synthesis Context must include only evidence-valid inputs:

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

Discovery Synthesis Context must exclude by default:

- `Assumption`
- rejected or inactive `Task`
- completed `Hypothesis`
- existing `Discovery`
- raw chat turns
- failed reasoning chains
- unverified `GeneratedView`
- generic summaries

Existing Discoveries may be used for answer/audit context, but a new Discovery must be synthesized from Hypothesis, accepted DataProfile, provenance, active Evidence, and validity metadata rather than from prior Discovery claims.

## Current Implementation

Current code provides:

- `SessionFrame` summaries with DataProfiles, Tasks, active assumptions, active hypotheses, Discoveries, Evidence, user-decision provenance, stale context, dead ends, and cached tool results.
- `SessionContextBuilder`, which projects a `SessionFrame` into `planning`, `answer`, `conclusion`, or `discovery_synthesis` context bundles.
- Planning context includes active assumptions, proposed/active/paused Tasks, relevant Discoveries, and active Evidence summaries.
- Answer context may include existing Discoveries for user Q&A, while keeping assumptions out of answer synthesis by default.
- `conclusion` is treated as a legacy alias for protected Discovery Synthesis Context.
- Discovery Synthesis Context excludes assumptions, tasks, existing Discoveries, user decisions, pending tasks, open questions, stale context, dead ends, and cached tool-result summaries.
- Discovery Synthesis Context filters by safe memory status and active profile/evidence lifecycle.
- no retrieval engine
- no graph retrieval context mode selector
- no graph-level Discovery Synthesis Context constructor

## Implementation Status

Partially implemented.

The current code enforces a local Planning/Answer/Discovery Synthesis split for `SessionFrame` snapshots. Full target Context Type Safety remains incomplete because there is no typed graph retrieval engine or retrieval policy.

## Architectural Risk

If an LLM prompt is built from the raw `SessionFrame` instead of `SessionContextBuilder`, active assumptions and prior Discoveries can still appear beside evidence summaries. That is acceptable for planning and some user Q&A, but unsafe for Discovery synthesis.
