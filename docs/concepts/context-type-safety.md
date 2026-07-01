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
- no retrieval engine
- no context mode selector
- no Conclusion Context constructor
- no enforcement that assumptions are excluded from inference
- no epistemic-role field on current artifact models

## Implementation Status

Design target.

Some data needed for future filtering exists in current statuses and summary fields, but the target rule is not yet enforced in code.

## Architectural Risk

If an LLM prompt is built from the current `SessionFrame` without filtering, active assumptions can appear beside evidence summaries. That is acceptable for planning but unsafe for conclusion generation.

## Required Tests When Implemented

Add tests that verify:

- Planning Context may include active assumptions.
- Conclusion Context excludes assumptions.
- Rejected tasks do not enter Conclusion Context.
- Completed hypotheses are not retrieved as current knowledge by default.
- Stale evidence and old data profiles are excluded unless the user requests audit/history.
