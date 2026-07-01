# Validity Envelope

## Target Design

Every target `Discovery` must have a `ValidityEnvelope`. The envelope records the conditions under which a claim is valid and the conditions that invalidate or flag it.

Required target metadata:

- `data_profile_id`
- `analysis_frame_refs`, including analysis frame IDs and frame hashes
- `hypothesis_id`
- `evidence_ids`
- method IDs
- parameter hashes
- code versions where available
- environment hashes where available
- random seeds where applicable
- scope
- decision rule
- strength
- uncertainty
- `assumptions_excluded_from_inference`
- invalidators

Target invalidators include:

- `DataProfile` superseded
- `AnalysisFrame` invalidated
- `Evidence` superseded
- method implementation error
- parameter change
- code defect
- metric definition change
- user invalidation
- stronger later Evidence

## Current Implementation

No `ValidityEnvelope` schema or enforcement was found.

Related partial fields:

- Current `Evidence` stores `dataset_id`, `method`, parameters, provenance, result summary, limitations, and typed hypothesis evaluations.
- `EvidenceProvenance` stores optional `source_profile_id`, execution label, code reference, and artifact paths.
- `SessionFrame` stores invalidation rules for summarized context.

These fields are not enough to satisfy the target envelope because there is no `Discovery`, no `AnalysisFrame`, no parameter hash, no execution run, no code/environment identity contract, and no assumptions-excluded audit.

## Implementation Status

Not implemented.

## Development Guidance

Do not create `Discovery` without a validity envelope. Natural-language summaries are convenience views only; structured claim and validity metadata are authoritative.

When this feature is implemented, add tests that assert:

- Discovery cannot be created without Evidence.
- Discovery cannot be created without a validity envelope.
- The envelope references DataProfile, AnalysisFrame, Hypothesis, Evidence, method, parameters, scope, uncertainty, and invalidators.
- Assumptions are recorded as excluded from inference rather than used as premises.
