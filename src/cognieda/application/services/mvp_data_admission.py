"""Application-authority admission for bounded M3-A Data Explorer output."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataExplorerInput,
    DataExplorerResult,
    DataProfileCandidate,
)
from cognieda.delegation import (
    Capability,
    ExecutorRequest,
    ExecutionStatus,
    PlannerWorkOutcome,
    normalize_for_planner,
)
from cognieda.infrastructure.persistence.repositories import (
    DataProfileDatasetBindingRepository,
    DataProfileRepository,
    EvidenceRepository,
    TaskRepository,
)
from cognieda.schemas import (
    DataProfile,
    DataProfileDatasetBinding,
    Evidence,
    EvidenceProvenance,
    TaskKind,
    TaskStatus,
)


class DataAdmissionErrorCode(StrEnum):
    INVALID_RESULT = "invalid_result"
    TASK_MISMATCH = "task_mismatch"
    TASK_NOT_COMPLETED = "task_not_completed"
    DATA_PROFILE_MISMATCH = "data_profile_mismatch"
    DATASET_MISMATCH = "dataset_mismatch"
    DUPLICATE_WORK_CONFLICT = "duplicate_work_conflict"


class DataAdmissionError(ValueError):
    def __init__(self, code: DataAdmissionErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


class DataProfileAdmissionResult(BaseModel):
    """Authoritative profile plus replay information; activation is not implied."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    data_profile: DataProfile
    dataset_binding: DataProfileDatasetBinding
    created: bool


class EvidenceAdmissionResult(BaseModel):
    """Bounded M3-A handoff to later runtime composition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence: Evidence
    planner_outcome: PlannerWorkOutcome
    created: bool


def _normalized_explicit_path(raw_path: str | None) -> str:
    if raw_path is None or not raw_path.strip():
        raise DataAdmissionError(
            DataAdmissionErrorCode.DATASET_MISMATCH,
            "Evidence admission requires an explicit dataset_path.",
        )
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise DataAdmissionError(
            DataAdmissionErrorCode.DATASET_MISMATCH,
            "Evidence admission requires an absolute explicit dataset_path.",
        )
    return str(path.resolve())


class MvpDataProfileAdmissionService:
    """Admit only a typed initial profile candidate; do not activate it."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._profiles = DataProfileRepository(session)
        self._bindings = DataProfileDatasetBindingRepository(session)

    def admit_candidate(self, candidate: DataProfileCandidate) -> DataProfileAdmissionResult:
        normalized_path = _normalized_explicit_path(candidate.provenance.dataset_reference)
        if candidate.provenance.dataset_reference != normalized_path:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DATASET_MISMATCH,
                "DataProfile candidate provenance requires a normalized dataset path.",
            )
        if (
            candidate.provenance.tool_reference
            != "cognieda.data_explorer.dataset_profile:v1"
            or candidate.provenance.parameters != {"mode": "candidate"}
            or candidate.provenance.code_reference is not None
        ):
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                "DataProfile candidate provenance does not match deterministic profiling.",
            )
        binding = DataProfileDatasetBinding(
            data_profile_id=candidate.profile.data_profile_id,
            dataset_reference=normalized_path,
            dataset_digest=candidate.provenance.dataset_digest,
        )
        existing_profile = self._profiles.get_by_id(candidate.profile.data_profile_id)
        existing_binding = self._bindings.get_by_profile_id(
            candidate.profile.data_profile_id
        )
        if existing_profile is not None and existing_profile != candidate.profile:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DUPLICATE_WORK_CONFLICT,
                "DataProfile identity already exists with different content.",
            )
        if existing_binding is not None and existing_binding != binding:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DUPLICATE_WORK_CONFLICT,
                "DataProfile identity already has a different physical dataset binding.",
            )
        if existing_profile is not None and existing_binding is not None:
            return DataProfileAdmissionResult(
                data_profile=existing_profile,
                dataset_binding=existing_binding,
                created=False,
            )

        try:
            if existing_profile is None:
                self._profiles.add(candidate.profile)
                self._session.flush()
            if existing_binding is None:
                self._bindings.add(binding)
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            concurrent_profile = self._profiles.get_by_id(candidate.profile.data_profile_id)
            concurrent_binding = self._bindings.get_by_profile_id(
                candidate.profile.data_profile_id
            )
            if concurrent_profile == candidate.profile and concurrent_binding == binding:
                return DataProfileAdmissionResult(
                    data_profile=candidate.profile,
                    dataset_binding=binding,
                    created=False,
                )
            raise DataAdmissionError(
                DataAdmissionErrorCode.DUPLICATE_WORK_CONFLICT,
                "Concurrent DataProfile admission produced an identity conflict.",
            ) from None
        except Exception:
            self._session.rollback()
            raise

        admitted_profile = self._profiles.get_by_id(candidate.profile.data_profile_id)
        admitted_binding = self._bindings.get_by_profile_id(candidate.profile.data_profile_id)
        if admitted_profile is None or admitted_binding is None:
            raise RuntimeError("Committed DataProfile admission could not be reloaded.")
        return DataProfileAdmissionResult(
            data_profile=admitted_profile,
            dataset_binding=admitted_binding,
            created=True,
        )


class MvpEvidenceAdmissionService:
    """Atomically validate and admit successful deterministic Data Explorer work."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tasks = TaskRepository(session)
        self._profiles = DataProfileRepository(session)
        self._bindings = DataProfileDatasetBindingRepository(session)
        self._evidence = EvidenceRepository(session)

    @staticmethod
    def _evidence_id(
        request: ExecutorRequest,
        result: DataExplorerResult,
        content: dict[str, JsonValue],
    ) -> UUID:
        identity = json.dumps(
            {
                "task_id": str(request.input.task.task_id),
                "work_id": result.work_id,
                "data_profile_id": str(request.context.data_profile_id),
                "dataset_digest": (
                    result.provenance.dataset_digest
                    if result.provenance is not None
                    else None
                ),
                "content": content,
            },
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return uuid5(NAMESPACE_URL, f"cognieda:m3a-evidence:{digest}")

    def _validate(
        self,
        request: ExecutorRequest,
        result: DataExplorerResult,
    ) -> tuple[dict[str, JsonValue], EvidenceProvenance]:
        if result.status is not ExecutionStatus.SUCCEEDED or result.failure is not None:
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                "Only successful Data Explorer work can become Evidence.",
            )
        if result.source_role != "data_explorer":
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                "Evidence admission requires the Data Explorer source role.",
            )
        if request.input.task.kind is not TaskKind.DATA:
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                "Bounded M3-A Evidence admission accepts only DATA Tasks.",
            )
        if result.capability not in {Capability.DATA_ANALYSIS, Capability.DATA_PROFILING}:
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                "This capability is not admitted to M3-A Evidence.",
            )
        if request.capability is not result.capability:
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                "Execution request and result capabilities do not match.",
            )
        if request.input.task.task_id != result.task_id:
            raise DataAdmissionError(
                DataAdmissionErrorCode.TASK_MISMATCH,
                "Execution request and result Task identities do not match.",
            )

        task = self._tasks.get_by_id(result.task_id)
        request_task = request.input.task
        if task is None or (
            task.task_id,
            task.objective_id,
            task.kind,
            task.instruction,
        ) != (
            request_task.task_id,
            request_task.objective_id,
            request_task.kind,
            request_task.instruction,
        ):
            raise DataAdmissionError(
                DataAdmissionErrorCode.TASK_MISMATCH,
                "Evidence requires the matching authoritative Task.",
            )
        if task.status is not TaskStatus.COMPLETED:
            raise DataAdmissionError(
                DataAdmissionErrorCode.TASK_NOT_COMPLETED,
                "Evidence requires an authoritative COMPLETED Task.",
            )

        profile_id = request.context.data_profile_id
        authoritative_profile = (
            self._profiles.get_by_id(profile_id) if profile_id is not None else None
        )
        if profile_id is None or authoritative_profile is None:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DATA_PROFILE_MISMATCH,
                "Evidence requires an authoritative matching DataProfile.",
            )
        binding = self._bindings.get_by_profile_id(profile_id)
        if binding is None:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DATA_PROFILE_MISMATCH,
                "Evidence requires an authoritative physical dataset binding.",
            )
        if isinstance(request.input, DataExplorerInput) and (
            request.input.data_profile != authoritative_profile
        ):
            raise DataAdmissionError(
                DataAdmissionErrorCode.DATA_PROFILE_MISMATCH,
                "The execution DataProfile projection is not authoritative.",
            )
        provenance = result.provenance
        if provenance is None or provenance.data_profile_id != binding.data_profile_id:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DATA_PROFILE_MISMATCH,
                "Execution provenance does not match the authoritative DataProfile.",
            )
        request_path = _normalized_explicit_path(request.context.dataset_path)
        if request_path != binding.dataset_reference:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DATASET_MISMATCH,
                "The requested dataset path does not match the authoritative binding.",
            )
        if provenance.dataset_reference != binding.dataset_reference:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DATASET_MISMATCH,
                "Execution provenance path does not match the authoritative binding.",
            )
        if provenance.dataset_digest != binding.dataset_digest:
            raise DataAdmissionError(
                DataAdmissionErrorCode.DATASET_MISMATCH,
                "Executed dataset content does not match the authoritative binding.",
            )
        if len(result.observations) != 1 or result.produced_data_profile is not None:
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                "Evidence requires exactly one non-authoritative observation.",
            )
        observation = result.observations[0]
        if not observation.payload:
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                "Evidence requires a non-empty deterministic result payload.",
            )

        if result.capability is Capability.DATA_ANALYSIS:
            plan = result.analysis_plan
            if (
                plan is None
                or provenance.operation != plan.operation
                or provenance.parameters != plan.bounded_parameters()
            ):
                raise DataAdmissionError(
                    DataAdmissionErrorCode.INVALID_RESULT,
                    "Analysis plan and deterministic execution provenance do not agree.",
                )
        else:
            if provenance.operation != "dataset_profile":
                raise DataAdmissionError(
                    DataAdmissionErrorCode.INVALID_RESULT,
                    "Profiling Evidence requires dataset_profile provenance.",
                )
            expected_profile = authoritative_profile.model_dump(
                mode="json", exclude={"data_profile_id"}
            )
            if observation.payload != expected_profile:
                raise DataAdmissionError(
                    DataAdmissionErrorCode.DATA_PROFILE_MISMATCH,
                    "Profile observations do not match the authoritative DataProfile.",
                )

        operation = provenance.operation
        operation_value = (
            operation.value if isinstance(operation, DataAnalysisOperation) else operation
        )
        content: dict[str, JsonValue] = {
            "operation": operation_value,
            "parameters": provenance.parameters,
            "result": observation.payload,
        }
        evidence_provenance = EvidenceProvenance(
            producer_role=result.source_role,
            work_reference=result.work_id,
            dataset_reference=provenance.dataset_reference,
            data_profile_id=profile_id,
            tool_reference=provenance.tool_reference,
            code_reference=provenance.code_reference,
        )
        return content, evidence_provenance

    def admit(
        self,
        request: ExecutorRequest,
        result: DataExplorerResult,
    ) -> EvidenceAdmissionResult:
        content, provenance = self._validate(request, result)
        try:
            evidence = Evidence(
                evidence_id=self._evidence_id(request, result, content),
                task_id=result.task_id,
                data_profile_id=provenance.data_profile_id,
                content=content,
                provenance=provenance,
                artifact_refs=tuple(result.artifact_refs),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise DataAdmissionError(
                DataAdmissionErrorCode.INVALID_RESULT,
                f"Evidence content or provenance is invalid: {exc}",
            ) from exc

        for prior in self._evidence.list(task_id=result.task_id):
            if prior.provenance.work_reference != result.work_id:
                continue
            if prior == evidence:
                return self._result(result, prior, created=False)
            raise DataAdmissionError(
                DataAdmissionErrorCode.DUPLICATE_WORK_CONFLICT,
                "The Data Explorer work reference is already admitted with different content.",
            )

        existing = self._evidence.get_by_id(evidence.evidence_id)
        if existing is not None:
            if existing != evidence:
                raise DataAdmissionError(
                    DataAdmissionErrorCode.DUPLICATE_WORK_CONFLICT,
                    "Deterministic Evidence identity conflicts with existing content.",
                )
            return self._result(result, existing, created=False)

        try:
            self._evidence.add(evidence)
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            existing = self._evidence.get_by_id(evidence.evidence_id)
            if existing == evidence:
                return self._result(result, evidence, created=False)
            raise DataAdmissionError(
                DataAdmissionErrorCode.DUPLICATE_WORK_CONFLICT,
                "Concurrent Evidence admission produced an identity conflict.",
            ) from None
        except Exception:
            self._session.rollback()
            raise

        admitted = self._evidence.get_by_id(evidence.evidence_id)
        if admitted is None:
            raise RuntimeError("Committed Evidence could not be reloaded.")
        return self._result(result, admitted, created=True)

    @staticmethod
    def _result(
        result: DataExplorerResult,
        evidence: Evidence,
        *,
        created: bool,
    ) -> EvidenceAdmissionResult:
        outcome = normalize_for_planner(result).model_copy(
            update={"authoritative_refs": [f"evidence:{evidence.evidence_id}"]}
        )
        return EvidenceAdmissionResult(
            evidence=evidence,
            planner_outcome=outcome,
            created=created,
        )
