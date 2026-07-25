"""Canonical protected bundle and closed provenance manifest schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from schemas.common import ImmutableCogniEDABaseModel, NonEmptyStr
from schemas.evaluation.snapshots import (
    AdmittedEvidenceSnapshot,
    AnalysisFrameEvaluationSnapshot,
    DataProfileEvaluationSnapshot,
    ExecutionRunEvaluationSnapshot,
    HypothesisEvaluationSnapshot,
)


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
