"""Canonical evaluation contracts package."""

from __future__ import annotations

from schemas.evaluation.bundle import (
    ActiveStateProof,
    BundleProvenanceManifest,
    DiscoverySynthesisBundle,
    InclusionRole,
    ManifestObjectType,
    ProvenanceManifestEntry,
    RepositorySource,
)
from schemas.evaluation.results import (
    DiscoveryProposal,
    EvaluationFailure,
    EvaluationFailureReason,
    HypothesisAnalystResult,
    compute_proposal_digest,
    validate_proposal_against_bundle,
)
from schemas.evaluation.snapshots import (
    AdmittedEvidenceSnapshot,
    AnalysisFrameEvaluationSnapshot,
    DataProfileEvaluationSnapshot,
    DecisionRuleSnapshot,
    EvidenceResultSnapshot,
    ExecutionRunEvaluationSnapshot,
    HypothesisEvaluationSnapshot,
    MethodParameterSnapshot,
    MetricThresholdSnapshot,
)

SUPPORTED_EVALUATION_CONTRACT_VERSION = "1.0"
SUPPORTED_PROPOSAL_SCHEMA_VERSION = "1.0"

__all__ = [
    "SUPPORTED_EVALUATION_CONTRACT_VERSION",
    "SUPPORTED_PROPOSAL_SCHEMA_VERSION",
    "ActiveStateProof",
    "AdmittedEvidenceSnapshot",
    "AnalysisFrameEvaluationSnapshot",
    "BundleProvenanceManifest",
    "DataProfileEvaluationSnapshot",
    "DecisionRuleSnapshot",
    "DiscoveryProposal",
    "DiscoverySynthesisBundle",
    "EvaluationFailure",
    "EvaluationFailureReason",
    "EvidenceResultSnapshot",
    "ExecutionRunEvaluationSnapshot",
    "HypothesisAnalystResult",
    "HypothesisEvaluationSnapshot",
    "InclusionRole",
    "ManifestObjectType",
    "MethodParameterSnapshot",
    "MetricThresholdSnapshot",
    "ProvenanceManifestEntry",
    "RepositorySource",
    "compute_proposal_digest",
    "validate_proposal_against_bundle",
]
