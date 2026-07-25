"""Repository for durable proposal governance decision records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from db.models import GovernanceAuthorityRecord, ProposalDecisionRecord


class ProposalDecisionRepository:
    """Persistence access for ProposalDecisionRecord entities."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def stage_create(self, record: ProposalDecisionRecord) -> ProposalDecisionRecord:
        """Add a decision record without committing the session."""

        self._session.add(record)
        return record

    def create(self, record: ProposalDecisionRecord) -> ProposalDecisionRecord:
        """Persist and commit a new proposal decision record."""

        self._session.add(record)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise
        self._session.refresh(record)
        return record

    def get_by_id(self, decision_id: UUID) -> ProposalDecisionRecord | None:
        """Return a decision record by primary id if it exists."""

        return self._session.get(ProposalDecisionRecord, decision_id)

    def get_for_proposal(
        self, evaluation_id: UUID, proposal_digest: str
    ) -> ProposalDecisionRecord | None:
        """Return the durable decision record for a specific proposal if it exists."""

        statement = (
            select(ProposalDecisionRecord)
            .where(ProposalDecisionRecord.evaluation_id == evaluation_id)
            .where(ProposalDecisionRecord.proposal_digest == proposal_digest)
        )
        return self._session.exec(statement).first()

    def get_authority(self, authority_id: UUID) -> GovernanceAuthorityRecord | None:
        """Return an independently persisted governance authority grant."""

        return self._session.get(GovernanceAuthorityRecord, authority_id)

    def get_by_fingerprint(self, fingerprint: str) -> ProposalDecisionRecord | None:
        """Return a decision record by its immutable decision fingerprint."""

        statement = select(ProposalDecisionRecord).where(
            ProposalDecisionRecord.decision_fingerprint == fingerprint
        )
        return self._session.exec(statement).first()

    def list_for_hypothesis(self, hypothesis_id: UUID) -> list[ProposalDecisionRecord]:
        """List decision records bound to a given Hypothesis."""

        statement = (
            select(ProposalDecisionRecord)
            .where(ProposalDecisionRecord.hypothesis_id == hypothesis_id)
            .order_by(ProposalDecisionRecord.decision_timestamp)
        )
        return list(self._session.exec(statement).all())
