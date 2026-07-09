"""Persistence access for immutable Evidence FCOs."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING
from uuid import UUID

from db.models import EvidenceRecord
from repositories.analysis_frame_repository import AnalysisFrameRepository
from repositories.common import record_to_schema, schema_to_record_payload
from repositories.execution_run_repository import ExecutionRunRepository
from schemas.artifacts import Evidence
from schemas.enums import EvidenceLifecycleState
from sqlmodel import Session, desc, select

if TYPE_CHECKING:
    from repositories.discovery_repository import DiscoveryRepository

EVIDENCE_JSON_FIELDS = {
    "parameters",
    "provenance",
    "result_summary",
    "artifact_refs",
    "limitations",
}
_EVIDENCE_HISTORICAL_SCOPE_TERMINAL_STATES = {
    EvidenceLifecycleState.SUPERSEDED,
    EvidenceLifecycleState.INVALIDATED,
}


class EvidenceRepository:
    """Repository for append-only Evidence records."""

    def __init__(
        self,
        session: Session,
        analysis_frame_repository: AnalysisFrameRepository | None = None,
        execution_run_repository: ExecutionRunRepository | None = None,
        *,
        strict_provenance_validation: bool = False,
    ) -> None:
        self._session = session
        self._strict_provenance_validation = (
            strict_provenance_validation
            or analysis_frame_repository is not None
            or execution_run_repository is not None
        )
        self._analysis_frame_repository: AnalysisFrameRepository | None
        self._execution_run_repository: ExecutionRunRepository | None
        if self._strict_provenance_validation:
            self._analysis_frame_repository = (
                analysis_frame_repository or AnalysisFrameRepository(session)
            )
            self._execution_run_repository = (
                execution_run_repository or ExecutionRunRepository(session)
            )
        else:
            self._analysis_frame_repository = None
            self._execution_run_repository = None

    def create(self, evidence: Evidence) -> Evidence:
        """Persist and return a new Evidence record."""

        if self._strict_provenance_validation:
            self._validate_provenance_refs(evidence)
        record = EvidenceRecord(
            **schema_to_record_payload(evidence, json_fields=EVIDENCE_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Evidence, record)

    def _validate_provenance_refs(self, evidence: Evidence) -> None:
        """Validate Evidence refs against minimal provenance repositories."""

        analysis_frame_id = self._parse_uuid_ref(
            evidence.analysis_frame_ref,
            field_name="analysis_frame_ref",
        )
        execution_run_id = self._parse_uuid_ref(
            evidence.execution_run_ref,
            field_name="execution_run_ref",
        )

        analysis_frame_repository = self._require_analysis_frame_repository()
        execution_run_repository = self._require_execution_run_repository()

        analysis_frame = analysis_frame_repository.get_by_id(analysis_frame_id)
        if analysis_frame is None:
            raise ValueError(
                "Evidence strict provenance validation requires an existing AnalysisFrame."
            )
        if analysis_frame.data_profile_id != evidence.profile_id:
            raise ValueError(
                "Evidence AnalysisFrame data_profile_id must match Evidence profile_id."
            )

        execution_run = execution_run_repository.get_by_id(execution_run_id)
        if execution_run is None:
            raise ValueError(
                "Evidence strict provenance validation requires an existing ExecutionRun."
            )
        if (
            execution_run.hypothesis_id is not None
            and execution_run.hypothesis_id != evidence.hypothesis_id
        ):
            raise ValueError(
                "Evidence ExecutionRun hypothesis_id must match Evidence hypothesis_id."
            )

    @staticmethod
    def _parse_uuid_ref(ref_value: str, *, field_name: str) -> UUID:
        try:
            return UUID(ref_value)
        except ValueError as exc:
            raise ValueError(
                f"Evidence {field_name} must be a persisted provenance UUID in strict mode."
            ) from exc

    def _require_analysis_frame_repository(self) -> AnalysisFrameRepository:
        if self._analysis_frame_repository is None:
            raise RuntimeError("Strict provenance validation requires AnalysisFrameRepository.")
        return self._analysis_frame_repository

    def _require_execution_run_repository(self) -> ExecutionRunRepository:
        if self._execution_run_repository is None:
            raise RuntimeError("Strict provenance validation requires ExecutionRunRepository.")
        return self._execution_run_repository

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        """Return an Evidence record by primary id if it exists."""

        record = self._session.get(EvidenceRecord, evidence_id)
        if record is None:
            return None
        return record_to_schema(Evidence, record)

    def list(
        self,
        *,
        hypothesis_id: UUID | None = None,
        profile_id: UUID | None = None,
        lifecycle_state: EvidenceLifecycleState | None = None,
    ) -> list[Evidence]:
        """List evidence by hypothesis, DataProfile, or lifecycle state."""

        statement = select(EvidenceRecord).order_by(desc(EvidenceRecord.created_at))
        if hypothesis_id is not None:
            statement = statement.where(EvidenceRecord.hypothesis_id == hypothesis_id)
        if profile_id is not None:
            statement = statement.where(EvidenceRecord.profile_id == profile_id)
        if lifecycle_state is not None:
            statement = statement.where(EvidenceRecord.lifecycle_state == lifecycle_state)
        records = self._session.exec(statement).all()
        return [record_to_schema(Evidence, record) for record in records]

    def list_for_hypothesis(self, hypothesis_id: UUID) -> builtins.list[Evidence]:
        """List Evidence records for one Hypothesis."""

        return self.list(hypothesis_id=hypothesis_id)

    def list_for_profile(self, profile_id: UUID) -> builtins.list[Evidence]:
        """List Evidence records for one DataProfile."""

        return self.list(profile_id=profile_id)

    def supersede(
        self,
        evidence_id: UUID,
        superseded_by_evidence_id: UUID,
        reason: str | None = None,
        discovery_repository: DiscoveryRepository | None = None,
    ) -> Evidence | None:
        """Mark Evidence superseded without editing the observed result payload."""

        record = self._session.get(EvidenceRecord, evidence_id)
        if record is None:
            return None
        if self._session.get(EvidenceRecord, superseded_by_evidence_id) is None:
            raise ValueError("Superseding Evidence requires an existing replacement Evidence.")
        record.lifecycle_state = EvidenceLifecycleState.SUPERSEDED
        record.superseded_by_evidence_id = superseded_by_evidence_id
        record.lifecycle_reason = reason
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        superseded = record_to_schema(Evidence, record)
        if discovery_repository is not None:
            # Future orchestration may own broader propagation; this is a narrow review signal.
            discovery_repository.flag_by_evidence_change(
                evidence_id,
                reason or "Evidence was superseded without a lifecycle reason.",
                change_type=EvidenceLifecycleState.SUPERSEDED,
                replacement_evidence_id=superseded_by_evidence_id,
            )
        return superseded

    def invalidate(
        self,
        evidence_id: UUID,
        reason: str | None = None,
        discovery_repository: DiscoveryRepository | None = None,
    ) -> Evidence | None:
        """Mark Evidence invalidated without editing the observed result payload."""

        record = self._session.get(EvidenceRecord, evidence_id)
        if record is None:
            return None
        record.lifecycle_state = EvidenceLifecycleState.INVALIDATED
        record.lifecycle_reason = reason
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        invalidated = record_to_schema(Evidence, record)
        if discovery_repository is not None:
            # Future orchestration may own broader propagation; this is a narrow review signal.
            discovery_repository.flag_by_evidence_change(
                evidence_id,
                reason or "Evidence was invalidated without a lifecycle reason.",
                change_type=EvidenceLifecycleState.INVALIDATED,
            )
        return invalidated

    def mark_historically_scoped_by_data_profile(
        self,
        old_data_profile_id: UUID,
        replacement_data_profile_id: UUID | None = None,
        reason: str | None = None,
    ) -> builtins.list[Evidence]:
        """Mark Evidence as historical for a superseded DataProfile scope."""

        records = self._session.exec(
            select(EvidenceRecord)
            .where(EvidenceRecord.profile_id == old_data_profile_id)
            .order_by(desc(EvidenceRecord.created_at))
        ).all()
        historical_reason = self._format_data_profile_historical_reason(
            old_data_profile_id,
            replacement_data_profile_id=replacement_data_profile_id,
            reason=reason,
        )
        affected_records: builtins.list[EvidenceRecord] = []
        for record in records:
            if record.lifecycle_state in _EVIDENCE_HISTORICAL_SCOPE_TERMINAL_STATES:
                continue

            record.lifecycle_state = EvidenceLifecycleState.HISTORICALLY_SCOPED
            record.lifecycle_reason = historical_reason
            self._session.add(record)
            affected_records.append(record)

        if affected_records:
            self._session.commit()
            for record in affected_records:
                self._session.refresh(record)

        return [record_to_schema(Evidence, record) for record in affected_records]

    @staticmethod
    def _format_data_profile_historical_reason(
        old_data_profile_id: UUID,
        *,
        replacement_data_profile_id: UUID | None,
        reason: str | None,
    ) -> str:
        reason_parts = [
            f"historically_scoped_data_profile_id={old_data_profile_id}",
        ]
        if replacement_data_profile_id is not None:
            reason_parts.append(
                f"replacement_data_profile_id={replacement_data_profile_id}"
            )
        if reason is not None and reason.strip():
            reason_parts.append(f"reason={reason.strip()}")
        return "; ".join(reason_parts)
