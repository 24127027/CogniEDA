# Canonical Evaluation Schemas (`schemas.evaluation`)

## Purpose
`schemas.evaluation` defines canonical, immutable contracts for protected Hypothesis Analyst evaluation, synthesis bundles, provenance manifests, evaluation failure outcomes, and scientific proposals.

## Modules
- `snapshots.py`: Immutable evaluation snapshots (`HypothesisEvaluationSnapshot`, `DataProfileEvaluationSnapshot`, `AnalysisFrameEvaluationSnapshot`, `ExecutionRunEvaluationSnapshot`, `AdmittedEvidenceSnapshot`, `MethodParameterSnapshot`, `DecisionRuleSnapshot`, `EvidenceResultSnapshot`).
- `bundle.py`: Protected evaluation input container (`DiscoverySynthesisBundle`), closed manifest structures (`BundleProvenanceManifest`, `ProvenanceManifestEntry`), and vocabulary enums (`ManifestObjectType`, `InclusionRole`, `RepositorySource`, `ActiveStateProof`).
- `results.py`: Analyst output models (`DiscoveryProposal`, `EvaluationFailure`, `EvaluationFailureReason`, `HypothesisAnalystResult`) and canonical digest/validation functions (`compute_proposal_digest`, `validate_proposal_against_bundle`).

## Invariants
1. All models use Pydantic `extra="forbid"` and frozen/immutable settings where applicable.
2. `DiscoverySynthesisBundle` excludes `Assumption`s, generic context bags, raw chat, and prior `Discovery` objects.
3. `DiscoveryProposal` requires `validity_basis` to explicitly state `assumptions_excluded_from_inference = True`.
4. Serialization and digest algorithms preserve canonical SHA-256 formatting.
