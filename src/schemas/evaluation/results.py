"""Canonical evaluation output schemas, proposal validation, and digest calculation."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from schemas.canonical import canonical_sha256
from schemas.common import CogniEDABaseModel, DiscoveryClaim, NonEmptyStr, ValidityBasis
from schemas.enums import DiscoveryEpistemicStatus
from schemas.evaluation.bundle import DiscoverySynthesisBundle


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
