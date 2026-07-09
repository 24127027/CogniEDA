"""Persistence access for immutable Discovery FCOs."""

from __future__ import annotations

import builtins
from uuid import UUID

from db.models import DiscoveryRecord, EvidenceRecord, HypothesisRecord
from repositories.common import (
    filter_records_by_related_id,
    record_to_schema,
    schema_to_record_payload,
)
from schemas.artifacts import Discovery
from schemas.enums import (
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvidenceLifecycleState,
)
from sqlmodel import Session, desc, select

DISCOVERY_JSON_FIELDS = {
    "evidence_ids",
    "claim",
    "validity_basis",
    "review_reasons",
    "flagged_by_evidence_ids",
}
_DISCOVERY_REVIEW_TERMINAL_STATES = {
    DiscoveryLifecycleState.INVALIDATED,
    DiscoveryLifecycleState.DEPRECATED,
}


class DiscoveryRepository:
    """Repository for evidence-bound Discovery claims."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, discovery: Discovery) -> Discovery:
        """Persist and return a new Discovery."""

        self._validate_discovery_admission(discovery)
        record = DiscoveryRecord(
            **schema_to_record_payload(discovery, json_fields=DISCOVERY_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Discovery, record)

    def _validate_discovery_admission(self, discovery: Discovery) -> None:
        if self._session.get(HypothesisRecord, discovery.hypothesis_id) is None:
            raise ValueError("Discovery creation requires an existing Hypothesis.")

        duplicate = self._session.exec(
            select(DiscoveryRecord).where(
                DiscoveryRecord.hypothesis_id == discovery.hypothesis_id
            )
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
    ) -> list[Discovery]:
        """List Discoveries by source Hypothesis, epistemic status, or lifecycle state."""

        statement = select(DiscoveryRecord).order_by(desc(DiscoveryRecord.created_at))
        if hypothesis_id is not None:
            statement = statement.where(DiscoveryRecord.hypothesis_id == hypothesis_id)
        if epistemic_status is not None:
            statement = statement.where(DiscoveryRecord.epistemic_status == epistemic_status)
        if lifecycle_state is not None:
            statement = statement.where(DiscoveryRecord.lifecycle_state == lifecycle_state)
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
        """Flag Discoveries affected by Evidence lifecycle changes for review."""

        if change_type not in {
            EvidenceLifecycleState.SUPERSEDED,
            EvidenceLifecycleState.INVALIDATED,
        }:
            raise ValueError("Discovery review flags require superseded or invalidated Evidence.")
        if not reason.strip():
            raise ValueError("Discovery review flags require a non-empty reason.")

        records = self._session.exec(
            select(DiscoveryRecord).order_by(desc(DiscoveryRecord.created_at))
        ).all()
        matching_records = filter_records_by_related_id(
            records,
            field_name="evidence_ids",
            related_id=evidence_id,
        )
        review_reason = self._format_evidence_review_reason(
            evidence_id,
            reason,
            change_type=change_type,
            replacement_evidence_id=replacement_evidence_id,
        )
        evidence_ref = str(evidence_id)
        affected_records: builtins.list[DiscoveryRecord] = []
        for record in matching_records:
            if record.lifecycle_state in _DISCOVERY_REVIEW_TERMINAL_STATES:
                continue

            review_reasons = list(record.review_reasons)
            if review_reason not in review_reasons:
                review_reasons.append(review_reason)

            flagged_by_evidence_ids = list(record.flagged_by_evidence_ids)
            if evidence_ref not in flagged_by_evidence_ids:
                flagged_by_evidence_ids.append(evidence_ref)

            record.lifecycle_state = DiscoveryLifecycleState.FLAGGED
            record.review_reasons = review_reasons
            record.flagged_by_evidence_ids = flagged_by_evidence_ids
            self._session.add(record)
            affected_records.append(record)

        if affected_records:
            self._session.commit()
            for record in affected_records:
                self._session.refresh(record)

        return [record_to_schema(Discovery, record) for record in affected_records]

    def mark_historically_scoped_by_data_profile(
        self,
        old_data_profile_id: UUID,
        replacement_data_profile_id: UUID | None = None,
        reason: str | None = None,
    ) -> builtins.list[Discovery]:
        """Flag Discoveries whose validity envelope is scoped to an old DataProfile."""

        records = self._session.exec(
            select(DiscoveryRecord).order_by(desc(DiscoveryRecord.created_at))
        ).all()
        review_reason = self._format_data_profile_review_reason(
            old_data_profile_id,
            replacement_data_profile_id=replacement_data_profile_id,
            reason=reason,
        )
        affected_records: builtins.list[DiscoveryRecord] = []
        for record in records:
            if record.lifecycle_state in _DISCOVERY_REVIEW_TERMINAL_STATES:
                continue
            if not self._validity_basis_matches_data_profile(
                record,
                data_profile_id=old_data_profile_id,
            ):
                continue

            review_reasons = list(record.review_reasons)
            if review_reason not in review_reasons:
                review_reasons.append(review_reason)

            record.lifecycle_state = DiscoveryLifecycleState.FLAGGED
            record.review_reasons = review_reasons
            self._session.add(record)
            affected_records.append(record)

        if affected_records:
            self._session.commit()
            for record in affected_records:
                self._session.refresh(record)

        return [record_to_schema(Discovery, record) for record in affected_records]

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
            reason_parts.append(
                f"replacement_data_profile_id={replacement_data_profile_id}"
            )
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
