# Validity Basis

## Target Design

Every `Discovery` must carry validity metadata. The implementation uses `validity_basis` to avoid confusing this metadata with the claim condition.

A Discovery claim answers: what can be concluded, under what scope or condition?

A validity basis answers: what evidence, data profile, analysis frame, method, parameters, code version, decision rule, uncertainty, and invalidators make this claim valid or stale?

Required metadata:

- `data_profile_id`
- `analysis_frame_refs`
- `hypothesis_id`
- `evidence_ids`
- method identity
- parameters
- code/environment identity where available
- decision rule
- strength
- uncertainty
- `assumptions_excluded_from_inference`
- invalidators

## Current Implementation

`Discovery` requires:

- non-empty `evidence_ids`
- structured `claim`
- `epistemic_status`
- `scope`
- `validity_basis`

`Discovery.claim` and `Discovery.scope` hold the claim condition/scope. `Discovery.validity_basis` holds dependency and invalidation metadata.

## Implementation Status

Implemented locally for schema and repository persistence. Minimal durable `AnalysisFrame` and execution-attempt `ExecutionRun` records exist and may be strictly dereferenced by `EvidenceRepository`; full row/filter/code/environment/artifact reproducibility remains incomplete.

## Development Guidance

Do not create `Discovery` without Evidence or `validity_basis`. Natural-language summaries are convenience views only; structured claim and validity metadata are authoritative.
