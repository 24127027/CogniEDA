"""Persistence access for evidence artifacts."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import (
    EvidenceAssumptionLinkRecord,
    EvidenceDecisionLinkRecord,
    EvidenceHypothesisLinkRecord,
    EvidenceRecord,
)
from repositories.common import (
    dedupe_preserving_order,
    load_records_by_ids,
    load_related_ids,
    replace_link_records,
)
from schemas.artifacts import Evidence
from schemas.common import HypothesisEvaluation
from schemas.enums import HypothesisEvidenceOutcome

EVIDENCE_JSON_FIELDS = {
    "parameters",
    "provenance",
    "result_summary",
    "limitations",
}


class EvidenceRepository:
    """Artifact-specific CRUD access for evidence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, evidence: Evidence) -> Evidence:
        """Persist and return a new evidence artifact."""

        record = EvidenceRecord(**self._record_payload(evidence))
        self._session.add(record)
        self._sync_assumption_links(evidence.evidence_id, evidence.assumption_ids)
        self._sync_hypothesis_evaluations(
            evidence.evidence_id,
            evidence.hypothesis_evaluations,
        )
        self._sync_decision_links(evidence.evidence_id, evidence.decision_ids)
        self._session.commit()
        self._session.refresh(record)
        return self._hydrate(record)

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        """Return an evidence artifact by primary id if it exists."""

        record = self._session.get(EvidenceRecord, evidence_id)
        if record is None:
            return None
        return self._hydrate(record)

    def list(self, *, project_id: UUID | None = None) -> list[Evidence]:
        """List evidence artifacts, optionally scoped to a project."""

        statement = select(EvidenceRecord).order_by(desc(EvidenceRecord.created_at))
        if project_id is not None:
            statement = statement.where(EvidenceRecord.project_id == project_id)
        records = self._session.exec(statement).all()
        return [self._hydrate(record) for record in records]

    def list_for_dataset(self, dataset_id: UUID) -> builtins.list[Evidence]:
        """List evidence records for a dataset id."""

        statement = (
            select(EvidenceRecord)
            .where(EvidenceRecord.dataset_id == dataset_id)
            .order_by(desc(EvidenceRecord.created_at))
        )
        records = self._session.exec(statement).all()
        return [self._hydrate(record) for record in records]

    def list_for_assumption(self, assumption_id: UUID) -> builtins.list[Evidence]:
        """List evidence records linked to an assumption id."""

        evidence_ids = load_related_ids(
            self._session,
            EvidenceAssumptionLinkRecord,
            owner_field_name="assumption_id",
            owner_id=assumption_id,
            related_field_name="evidence_id",
        )
        records = load_records_by_ids(self._session, EvidenceRecord, evidence_ids)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return [self._hydrate(record) for record in records]

    def list_for_hypothesis(
        self,
        hypothesis_id: UUID,
        *,
        outcome: HypothesisEvidenceOutcome | None = None,
    ) -> builtins.list[Evidence]:
        """List evidence records linked to a hypothesis id."""

        statement = select(EvidenceHypothesisLinkRecord).where(
            EvidenceHypothesisLinkRecord.hypothesis_id == hypothesis_id
        )
        if outcome is not None:
            statement = statement.where(EvidenceHypothesisLinkRecord.outcome == outcome)
        links = self._session.exec(statement).all()
        evidence_ids = [link.evidence_id for link in links]
        records = load_records_by_ids(self._session, EvidenceRecord, evidence_ids)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return [self._hydrate(record) for record in records]

    def list_for_decision(self, decision_id: UUID) -> builtins.list[Evidence]:
        """List evidence records linked to a decision id."""

        evidence_ids = load_related_ids(
            self._session,
            EvidenceDecisionLinkRecord,
            owner_field_name="decision_id",
            owner_id=decision_id,
            related_field_name="evidence_id",
        )
        records = load_records_by_ids(self._session, EvidenceRecord, evidence_ids)
        records.sort(key=lambda item: item.created_at, reverse=True)
        return [self._hydrate(record) for record in records]

    def _hydrate(self, record: EvidenceRecord) -> Evidence:
        payload = record.model_dump()
        payload["assumption_ids"] = load_related_ids(
            self._session,
            EvidenceAssumptionLinkRecord,
            owner_field_name="evidence_id",
            owner_id=record.evidence_id,
            related_field_name="assumption_id",
        )
        payload["decision_ids"] = load_related_ids(
            self._session,
            EvidenceDecisionLinkRecord,
            owner_field_name="evidence_id",
            owner_id=record.evidence_id,
            related_field_name="decision_id",
        )
        hypothesis_links = self._session.exec(
            select(EvidenceHypothesisLinkRecord)
            .where(EvidenceHypothesisLinkRecord.evidence_id == record.evidence_id)
        ).all()
        payload["hypothesis_evaluations"] = [
            HypothesisEvaluation(
                hypothesis_id=link.hypothesis_id,
                outcome=link.outcome,
                note=link.note,
            )
            for link in hypothesis_links
        ]
        return Evidence.model_validate(payload)

    def _record_payload(self, evidence: Evidence) -> dict[str, object]:
        python_payload = evidence.model_dump(
            mode="python",
            exclude={"assumption_ids", "hypothesis_evaluations", "decision_ids"},
        )
        json_payload = evidence.model_dump(
            mode="json",
            include=EVIDENCE_JSON_FIELDS,
        )
        for field_name in EVIDENCE_JSON_FIELDS:
            python_payload[field_name] = json_payload[field_name]
        return python_payload

    def _sync_assumption_links(
        self,
        evidence_id: UUID,
        assumption_ids: builtins.list[UUID],
    ) -> None:
        deduped_ids: builtins.list[UUID] = dedupe_preserving_order(assumption_ids)
        replace_link_records(
            self._session,
            EvidenceAssumptionLinkRecord,
            owner_field_name="evidence_id",
            owner_id=evidence_id,
            payloads=[
                {
                    "evidence_id": evidence_id,
                    "assumption_id": assumption_id,
                }
                for assumption_id in deduped_ids
            ],
        )

    def _sync_hypothesis_evaluations(
        self,
        evidence_id: UUID,
        evaluations: builtins.list[HypothesisEvaluation],
    ) -> None:
        deduped_evaluations: builtins.list[HypothesisEvaluation] = dedupe_preserving_order(
            evaluations
        )
        replace_link_records(
            self._session,
            EvidenceHypothesisLinkRecord,
            owner_field_name="evidence_id",
            owner_id=evidence_id,
            payloads=[
                {
                    "evidence_id": evidence_id,
                    "hypothesis_id": evaluation.hypothesis_id,
                    "outcome": evaluation.outcome,
                    "note": evaluation.note,
                }
                for evaluation in deduped_evaluations
            ],
        )

    def _sync_decision_links(
        self,
        evidence_id: UUID,
        decision_ids: builtins.list[UUID],
    ) -> None:
        deduped_ids: builtins.list[UUID] = dedupe_preserving_order(decision_ids)
        replace_link_records(
            self._session,
            EvidenceDecisionLinkRecord,
            owner_field_name="evidence_id",
            owner_id=evidence_id,
            payloads=[
                {
                    "evidence_id": evidence_id,
                    "decision_id": decision_id,
                }
                for decision_id in deduped_ids
            ],
        )
