"""Persistence access for immutable Discovery FCOs."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import DiscoveryRecord, EvidenceRecord, HypothesisRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import Discovery
from schemas.enums import (
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvidenceLifecycleState,
)

DISCOVERY_JSON_FIELDS = {
    "evidence_ids",
    "claim",
    "validity_basis",
    "limitations",
    "review_reasons",
    "flagged_by_evidence_ids",
}
_DISCOVERY_REVIEW_TERMINAL_STATES = {
    DiscoveryLifecycleState.INVALIDATED,
    DiscoveryLifecycleState.DEPRECATED,
}

__all__ = ["DISCOVERY_JSON_FIELDS", "DiscoveryRepository"]


class DiscoveryRepository:
    """Repository for evidence-bound Discovery claims."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def uses_session(self, session: Session) -> bool:
        """Return whether this repository is bound to the supplied session object."""

        return self._session is session

    def create(self, discovery: Discovery) -> Discovery:
        """Reject the removed generic Discovery writer."""

        del discovery
        raise RuntimeError("Discovery creation is owned by AtomicDiscoveryAdmissionService.")

    def _stage_create_from_atomic_admission(self, discovery: Discovery) -> DiscoveryRecord:
        """Validate and stage a Discovery for the sole application-owned writer."""

        self._validate_discovery_admission(discovery)
        record = DiscoveryRecord(
            **schema_to_record_payload(discovery, json_fields=DISCOVERY_JSON_FIELDS)
        )
        self._session.add(record)
        return record

    def _validate_discovery_admission(self, discovery: Discovery) -> None:
        if self._session.get(HypothesisRecord, discovery.hypothesis_id) is None:
            raise ValueError("Discovery creation requires an existing Hypothesis.")

        duplicate = self._session.exec(
            select(DiscoveryRecord).where(DiscoveryRecord.hypothesis_id == discovery.hypothesis_id)
        ).first()
        if duplicate is not None:
            raise ValueError("A Hypothesis can produce exactly one Discovery.")

        for evidence_id in discovery.evidence_ids:
            evidence_record = self._session.get(EvidenceRecord, evidence_id)
            if evidence_record is None:
                raise ValueError("Discovery requires existing Evidence references.")
            if evidence_record.hypothesis_id != discovery.hypothesis_id:
                raise ValueError(
                    "Discovery Evidence references must belong to the same Hypothesis."
                )
            if evidence_record.lifecycle_state != EvidenceLifecycleState.ACTIVE:
                raise ValueError("Discovery can only synthesize active Evidence.")

    def get_by_id(self, discovery_id: UUID) -> Discovery | None:
        """Return a Discovery by primary id if it exists."""

        record = self._session.get(DiscoveryRecord, discovery_id)
        if record is None:
            return None
        return record_to_schema(Discovery, record)

    def list(
        self,
        *,
        hypothesis_id: UUID | None = None,
        epistemic_status: DiscoveryEpistemicStatus | None = None,
        lifecycle_state: DiscoveryLifecycleState | None = None,
        limit: int | None = None,
    ) -> list[Discovery]:
        """List Discoveries by source Hypothesis, epistemic status, or lifecycle state."""

        statement = select(DiscoveryRecord).order_by(desc(DiscoveryRecord.created_at))
        if hypothesis_id is not None:
            statement = statement.where(DiscoveryRecord.hypothesis_id == hypothesis_id)
        if epistemic_status is not None:
            statement = statement.where(DiscoveryRecord.epistemic_status == epistemic_status)
        if lifecycle_state is not None:
            statement = statement.where(DiscoveryRecord.lifecycle_state == lifecycle_state)
        if limit is not None:
            statement = statement.limit(limit)
        records = self._session.exec(statement).all()
        return [record_to_schema(Discovery, record) for record in records]

    def list_for_hypothesis(self, hypothesis_id: UUID) -> builtins.list[Discovery]:
        """List Discoveries produced for one Hypothesis."""

        return self.list(hypothesis_id=hypothesis_id)

    def flag_by_evidence_change(
        self,
        evidence_id: UUID,
        reason: str,
        *,
        change_type: EvidenceLifecycleState,
        replacement_evidence_id: UUID | None = None,
    ) -> builtins.list[Discovery]:
        """Reject post-commit Discovery flagging outside validity propagation."""

        del evidence_id, reason, change_type, replacement_evidence_id
        raise RuntimeError(
            "Evidence-driven Discovery review requires AtomicValidityPropagationService."
        )

    def mark_historically_scoped_by_data_profile(
        self,
        old_data_profile_id: UUID,
        replacement_data_profile_id: UUID | None = None,
        reason: str | None = None,
    ) -> builtins.list[Discovery]:
        """Reject post-commit DataProfile review outside validity propagation."""

        del old_data_profile_id, replacement_data_profile_id, reason
        raise RuntimeError(
            "DataProfile-driven Discovery review requires AtomicValidityPropagationService."
        )

    @staticmethod
    def _validity_basis_matches_data_profile(
        record: DiscoveryRecord,
        *,
        data_profile_id: UUID,
    ) -> bool:
        return record.validity_basis.get("data_profile_id") == str(data_profile_id)

    @staticmethod
    def _format_data_profile_review_reason(
        old_data_profile_id: UUID,
        *,
        replacement_data_profile_id: UUID | None,
        reason: str | None,
    ) -> str:
        reason_parts = [
            f"historically_scoped_data_profile_id={old_data_profile_id}",
        ]
        if replacement_data_profile_id is not None:
            reason_parts.append(f"replacement_data_profile_id={replacement_data_profile_id}")
        if reason is not None and reason.strip():
            reason_parts.append(f"reason={reason.strip()}")
        return "; ".join(reason_parts)

    @staticmethod
    def _format_evidence_review_reason(
        evidence_id: UUID,
        reason: str,
        *,
        change_type: EvidenceLifecycleState,
        replacement_evidence_id: UUID | None,
    ) -> str:
        reason_parts = [
            f"changed_evidence_id={evidence_id}",
            f"change_type={change_type.value}",
        ]
        if replacement_evidence_id is not None:
            reason_parts.append(f"replacement_evidence_id={replacement_evidence_id}")
        reason_parts.append(f"reason={reason.strip()}")
        return "; ".join(reason_parts)
