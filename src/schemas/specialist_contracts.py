"""Canonical contracts for protected Hypothesis Analyst evaluation."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, NonNegativeInt, field_validator, model_validator

from schemas.canonical import canonical_sha256
from schemas.common import (
    CogniEDABaseModel,
    DiscoveryClaim,
    EvaluationThresholds,
    ImmutableCogniEDABaseModel,
    MethodParameter,
    NonEmptyStr,
    ScalarParameterValue,
    ValidityBasis,
)
from schemas.enums import AnalysisIntent, DatasetSourceType, DiscoveryEpistemicStatus, EvidenceType

__all__ = [
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
    "ProvenanceManifestEntry",
    "RepositorySource",
    "compute_proposal_digest",
    "validate_proposal_against_bundle",
]

SUPPORTED_EVALUATION_CONTRACT_VERSION = "1.0"
SUPPORTED_PROPOSAL_SCHEMA_VERSION = "1.0"


class MethodParameterSnapshot(ImmutableCogniEDABaseModel):
    """Deeply immutable approved method parameter."""

    name: NonEmptyStr
    value: ScalarParameterValue

    def to_domain(self) -> MethodParameter:
        return MethodParameter(name=self.name, value=self.value)


class MetricThresholdSnapshot(ImmutableCogniEDABaseModel):
    """One ordered metric threshold entry."""

    name: NonEmptyStr
    value: float


class DecisionRuleSnapshot(ImmutableCogniEDABaseModel):
    """Deeply immutable approved decision rule."""

    p_value: float | None = None
    effect_size: float | None = None
    metric_thresholds: tuple[MetricThresholdSnapshot, ...] = ()
    rule_description: str | None = None

    @field_validator("metric_thresholds")
    @classmethod
    def _metric_names_are_unique_and_canonical(
        cls, value: tuple[MetricThresholdSnapshot, ...]
    ) -> tuple[MetricThresholdSnapshot, ...]:
        names = [entry.name for entry in value]
        if len(names) != len(set(names)):
            raise ValueError("Decision-rule metric threshold names must be unique.")
        if names != sorted(names):
            raise ValueError("Decision-rule metric thresholds must be sorted by name.")
        return value

    @classmethod
    def from_domain(cls, value: EvaluationThresholds) -> DecisionRuleSnapshot:
        return cls(
            p_value=value.p_value,
            effect_size=value.effect_size,
            metric_thresholds=tuple(
                MetricThresholdSnapshot(name=name, value=threshold)
                for name, threshold in sorted(value.metric_thresholds.items())
            ),
            rule_description=value.rule_description,
        )

    def to_domain(self) -> EvaluationThresholds:
        return EvaluationThresholds(
            p_value=self.p_value,
            effect_size=self.effect_size,
            metric_thresholds={entry.name: entry.value for entry in self.metric_thresholds},
            rule_description=self.rule_description,
        )


class HypothesisEvaluationSnapshot(ImmutableCogniEDABaseModel):
    """Immutable scientific content of one durably approved Hypothesis contract."""

    hypothesis_id: UUID
    data_profile_id: UUID
    statement: NonEmptyStr
    analysis_intent: AnalysisIntent
    variables: tuple[NonEmptyStr, ...] = Field(min_length=1)
    scope: NonEmptyStr
    validation_method: NonEmptyStr
    method_parameters: tuple[MethodParameterSnapshot, ...] = ()
    decision_rule: DecisionRuleSnapshot
    deterministic_seed: int | None = None
    evidence_expectation: NonEmptyStr


class DataProfileEvaluationSnapshot(ImmutableCogniEDABaseModel):
    """Safe accepted-profile metadata without a filesystem dataset locator."""

    data_profile_id: UUID
    source_type: DatasetSourceType
    version_fingerprint: NonEmptyStr
    dvc_hash: str | None = None
    dvc_version_label: str | None = None
    row_count: NonNegativeInt
    column_count: NonNegativeInt
    accepted_as_ground_truth: Literal[True] = True


class AnalysisFrameEvaluationSnapshot(ImmutableCogniEDABaseModel):
    """Immutable evaluation snapshot of one admitted AnalysisFrame."""

    analysis_frame_id: UUID
    data_profile_id: UUID
    frame_fingerprint: NonEmptyStr
    frame_hash: NonEmptyStr | None = None
    frame_ref: NonEmptyStr | None = None
    column_refs: tuple[NonEmptyStr, ...] = ()
    row_filter_description: str | None = None

    @model_validator(mode="after")
    def _has_frame_identity(self) -> AnalysisFrameEvaluationSnapshot:
        if self.frame_hash is None and self.frame_ref is None:
            raise ValueError("AnalysisFrame snapshot requires frame_hash or frame_ref.")
        return self


class ExecutionRunEvaluationSnapshot(ImmutableCogniEDABaseModel):
    """Fenced admitted-attempt provenance needed for evaluation."""

    execution_run_id: UUID
    task_id: UUID
    hypothesis_id: UUID
    analysis_frame_id: UUID
    executor_type: NonEmptyStr
    method_id: NonEmptyStr
    parameter_hash: NonEmptyStr
    attempt_version: int = Field(ge=1)
    run_fingerprint: NonEmptyStr
    status: Literal["evidence_admitted"] = "evidence_admitted"


class EvidenceResultSnapshot(ImmutableCogniEDABaseModel):
    """Deeply immutable observed result content."""

    summary: NonEmptyStr
    key_findings: tuple[NonEmptyStr, ...] = ()
    metric_name: str | None = None
    metric_value: ScalarParameterValue = None
    metric_unit: str | None = None


class AdmittedEvidenceSnapshot(ImmutableCogniEDABaseModel):
    """Deeply immutable, active Evidence input stripped of timestamps and raw artifacts."""

    evidence_id: UUID
    hypothesis_id: UUID
    data_profile_id: UUID
    analysis_frame_id: UUID
    execution_run_id: UUID
    evidence_type: EvidenceType
    method: NonEmptyStr
    parameters: tuple[MethodParameterSnapshot, ...] = ()
    result: EvidenceResultSnapshot
    limitations: tuple[NonEmptyStr, ...] = ()
    code_reference: str | None = None
    environment_reference: str | None = None
    evidence_fingerprint: NonEmptyStr
    lifecycle_state: Literal["active"] = "active"


class DiscoverySynthesisBundle(ImmutableCogniEDABaseModel):
    """Versioned protected input; no generic context or workflow-state container exists."""

    contract_version: Literal["1.0"] = "1.0"
    evaluation_policy_version: Literal["protected-evaluation/v1"] = "protected-evaluation/v1"
    hypothesis: HypothesisEvaluationSnapshot
    data_profile: DataProfileEvaluationSnapshot
    analysis_frames: tuple[AnalysisFrameEvaluationSnapshot, ...] = Field(min_length=1)
    execution_runs: tuple[ExecutionRunEvaluationSnapshot, ...] = Field(min_length=1)
    admitted_evidence: tuple[AdmittedEvidenceSnapshot, ...] = Field(min_length=1)
    required_invalidators: tuple[NonEmptyStr, ...] = Field(min_length=1)
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_bundle_lineage(self) -> DiscoverySynthesisBundle:
        profile_id = self.data_profile.data_profile_id
        hypothesis_id = self.hypothesis.hypothesis_id
        if self.hypothesis.data_profile_id != profile_id:
            raise ValueError("Hypothesis snapshot must match the DataProfile snapshot.")
        if any(frame.data_profile_id != profile_id for frame in self.analysis_frames):
            raise ValueError("AnalysisFrame snapshots must match the DataProfile snapshot.")

        for ids in (
            [item.analysis_frame_id for item in self.analysis_frames],
            [item.execution_run_id for item in self.execution_runs],
            [item.evidence_id for item in self.admitted_evidence],
        ):
            if len(ids) != len(set(ids)):
                raise ValueError("Protected bundle durable object IDs must be unique.")
            if ids != sorted(ids, key=str):
                raise ValueError(
                    "Protected bundle durable object lists must use canonical ID order."
                )

        frame_ids = {frame.analysis_frame_id for frame in self.analysis_frames}
        run_ids = {run.execution_run_id for run in self.execution_runs}
        evidence_frame_ids = {evidence.analysis_frame_id for evidence in self.admitted_evidence}
        evidence_run_ids = {evidence.execution_run_id for evidence in self.admitted_evidence}
        if frame_ids != evidence_frame_ids:
            raise ValueError("Bundle must include exactly the AnalysisFrames used by Evidence.")
        if run_ids != evidence_run_ids:
            raise ValueError("Bundle must include exactly the ExecutionRuns used by Evidence.")
        if any(
            evidence.hypothesis_id != hypothesis_id
            or evidence.data_profile_id != profile_id
            or evidence.method != self.hypothesis.validation_method
            or evidence.parameters != self.hypothesis.method_parameters
            for evidence in self.admitted_evidence
        ):
            raise ValueError("Admitted Evidence must match the approved Hypothesis contract.")

        runs_by_id = {run.execution_run_id: run for run in self.execution_runs}
        if any(
            runs_by_id[evidence.execution_run_id].hypothesis_id != hypothesis_id
            or runs_by_id[evidence.execution_run_id].analysis_frame_id
            != evidence.analysis_frame_id
            for evidence in self.admitted_evidence
        ):
            raise ValueError("ExecutionRun provenance must match Evidence lineage.")
        return self


class ManifestObjectType(StrEnum):
    HYPOTHESIS = "Hypothesis"
    DATA_PROFILE = "DataProfile"
    ANALYSIS_FRAME = "AnalysisFrame"
    EXECUTION_RUN = "ExecutionRun"
    EVIDENCE = "Evidence"


class InclusionRole(StrEnum):
    EVALUAND = "evaluand"
    GROUND_TRUTH_PROFILE = "ground_truth_profile"
    DATA_SCOPE_PROVENANCE = "data_scope_provenance"
    EXECUTION_PROVENANCE = "execution_provenance"
    OBSERVED_PREMISE = "observed_analytical_premise"


class RepositorySource(StrEnum):
    HYPOTHESIS = "HypothesisRepository"
    DATA_PROFILE = "DataProfileRepository"
    ANALYSIS_FRAME = "AnalysisFrameRepository"
    EXECUTION_RUN = "ExecutionRunRepository"
    EVIDENCE = "EvidenceRepository"


class ActiveStateProof(StrEnum):
    READY_FOR_EVALUATION = "ready_for_evaluation"
    ACTIVE_ACCEPTED_GROUND_TRUTH = "active_accepted_ground_truth"
    LINEAGE_VALIDATED = "lineage_validated"
    EVIDENCE_ADMITTED = "evidence_admitted"
    ACTIVE_EVIDENCE = "active_evidence"


class ProvenanceManifestEntry(ImmutableCogniEDABaseModel):
    """Closed provenance entry; it cannot carry arbitrary context payloads."""

    object_type: ManifestObjectType
    object_id: UUID
    version_or_fingerprint: NonEmptyStr
    inclusion_role: InclusionRole
    repository_source: RepositorySource
    active_state_proof: ActiveStateProof


class BundleProvenanceManifest(ImmutableCogniEDABaseModel):
    """Durable, closed manifest for one protected bundle."""

    manifest_version: Literal["protected-manifest/v1"] = "protected-manifest/v1"
    bundle_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    entries: tuple[ProvenanceManifestEntry, ...] = Field(min_length=5)

    @field_validator("entries")
    @classmethod
    def _entry_identities_are_unique(
        cls, value: tuple[ProvenanceManifestEntry, ...]
    ) -> tuple[ProvenanceManifestEntry, ...]:
        identities = [(entry.object_type, entry.object_id) for entry in value]
        if len(identities) != len(set(identities)):
            raise ValueError("Provenance manifest entries must be unique.")
        return value


class EvaluationFailureReason(StrEnum):
    """Typed reasons that prevent or interrupt an evaluation attempt."""

    EVIDENCE_INADMISSIBLE = "evidence_inadmissible"
    INVALID_LINEAGE = "invalid_lineage"
    SCOPE_MISMATCH = "scope_mismatch"
    MISSING_MANDATORY_PROVENANCE = "missing_mandatory_provenance"
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    EVALUATION_NOT_IDENTIFIABLE = "evaluation_not_identifiable"
    TRANSIENT_PROVIDER_FAILURE = "transient_provider_failure"
    MALFORMED_STRUCTURED_OUTPUT = "malformed_structured_output"
    INVALID_PROPOSAL = "invalid_proposal"
    STALE_BUNDLE = "stale_bundle"


class DiscoveryProposal(CogniEDABaseModel):
    """Lifecycle-distinct scientific proposal without durable Discovery identity."""

    status: Literal["proposed"] = "proposed"
    claim: DiscoveryClaim
    epistemic_status: DiscoveryEpistemicStatus
    scope: NonEmptyStr
    evidence_ids: list[UUID] = Field(min_length=1)
    validity_basis: ValidityBasis
    limitations: tuple[NonEmptyStr, ...] = ()
    proposal_schema_version: Literal["1.0"] = "1.0"

    @field_validator("evidence_ids")
    @classmethod
    def _validate_unique_evidence_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_ids must not contain duplicates")
        return value

    @model_validator(mode="after")
    def _validate_proposal_alignment(self) -> DiscoveryProposal:
        if self.claim.scope != self.scope:
            raise ValueError("DiscoveryProposal claim scope must match proposal scope.")
        if set(self.validity_basis.evidence_ids) != set(self.evidence_ids):
            raise ValueError("DiscoveryProposal validity_basis must match evidence_ids.")
        if self.validity_basis.assumptions_excluded_from_inference is not True:
            raise ValueError("DiscoveryProposal validity_basis must exclude assumptions.")
        if not self.validity_basis.strength:
            raise ValueError("DiscoveryProposal validity_basis requires evidence strength.")
        if not self.validity_basis.uncertainty:
            raise ValueError("DiscoveryProposal validity_basis requires uncertainty.")
        if self.claim.result is None:
            raise ValueError("DiscoveryProposal claim requires an observed-result interpretation.")
        return self


class EvaluationFailure(CogniEDABaseModel):
    """Typed failure outcome; scientific outcomes are represented as proposals instead."""

    status: Literal["failed"] = "failed"
    failure_reason: EvaluationFailureReason
    message: NonEmptyStr
    details: tuple[NonEmptyStr, ...] = ()


type HypothesisAnalystResult = Annotated[
    DiscoveryProposal | EvaluationFailure,
    Field(discriminator="status"),
]


def compute_proposal_digest(proposal: DiscoveryProposal, source_bundle_digest: str) -> str:
    """Digest every authoritative proposal field plus its source bundle identity."""

    return canonical_sha256(
        {
            "source_bundle_digest": source_bundle_digest,
            "proposal": proposal.model_dump(mode="python"),
        }
    )


def validate_proposal_against_bundle(
    proposal: DiscoveryProposal,
    bundle: DiscoverySynthesisBundle,
) -> None:
    """Reject any proposal that changes or escapes the protected scientific contract."""

    hypothesis = bundle.hypothesis
    if proposal.validity_basis.hypothesis_id != hypothesis.hypothesis_id:
        raise ValueError("Proposal hypothesis_id does not match the protected bundle.")
    if proposal.scope != hypothesis.scope or proposal.claim.scope != hypothesis.scope:
        raise ValueError("Proposal scope does not match the protected Hypothesis scope.")

    bundle_evidence_ids = {evidence.evidence_id for evidence in bundle.admitted_evidence}
    if set(proposal.evidence_ids) != bundle_evidence_ids:
        raise ValueError("Proposal must cite the exact active Evidence set from the bundle.")
    if proposal.validity_basis.data_profile_id != bundle.data_profile.data_profile_id:
        raise ValueError("Proposal DataProfile does not match the protected bundle.")

    expected_frame_refs = {
        frame.frame_ref or str(frame.analysis_frame_id) for frame in bundle.analysis_frames
    }
    if set(proposal.validity_basis.analysis_frame_refs) != expected_frame_refs:
        raise ValueError("Proposal AnalysisFrame provenance does not match the protected bundle.")
    if proposal.validity_basis.method != hypothesis.validation_method:
        raise ValueError("Proposal method does not match the approved method.")
    expected_parameters = [parameter.to_domain() for parameter in hypothesis.method_parameters]
    if proposal.validity_basis.parameters != expected_parameters:
        raise ValueError("Proposal parameters do not match the approved parameters.")
    if proposal.validity_basis.decision_rule != hypothesis.decision_rule.to_domain():
        raise ValueError("Proposal decision rule does not match the approved decision rule.")
    if tuple(proposal.validity_basis.invalidators) != bundle.required_invalidators:
        raise ValueError("Proposal validity invalidators do not match the protected policy.")

    required_limitations = {
        limitation
        for evidence in bundle.admitted_evidence
        for limitation in evidence.limitations
    }
    if not required_limitations.issubset(set(proposal.limitations)):
        raise ValueError("Proposal omitted one or more admitted Evidence limitations.")

    text_fields = (
        proposal.claim.statement,
        proposal.claim.result or "",
        *proposal.claim.conditions,
    )
    if any(
        token in text.lower()
        for text in text_fields
        for token in ("assumption_id", "prior discovery", "discovery_id")
    ):
        raise ValueError("Proposal must not reference Assumptions or prior Discoveries.")

    p_threshold = hypothesis.decision_rule.p_value
    observed_p_values = [
        evidence.result.metric_value
        for evidence in bundle.admitted_evidence
        if evidence.result.metric_name == "p_value"
        and isinstance(evidence.result.metric_value, (int, float))
        and not isinstance(evidence.result.metric_value, bool)
    ]
    if (
        p_threshold is not None
        and observed_p_values
        and all(float(value) >= p_threshold for value in observed_p_values)
        and proposal.epistemic_status
        not in {
            DiscoveryEpistemicStatus.INCONCLUSIVE,
            DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE,
        }
    ):
        raise ValueError(
            "Fail-to-reject evidence requires inconclusive or insufficient-evidence status."
        )
