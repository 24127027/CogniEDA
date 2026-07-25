"""Repository for stage-only Discovery admission claim records."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import update
from sqlmodel import Session, select

from db.models import DiscoveryAdmissionClaimRecord, utc_now
from schemas.enums import DiscoveryAdmissionClaimState

__all__ = ["DiscoveryAdmissionClaimRepository"]


class DiscoveryAdmissionClaimRepository:
    """Stage-only persistence for non-FCO Discovery admission claims."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, claim_id: UUID) -> DiscoveryAdmissionClaimRecord | None:
        """Return a claim record by primary key."""

        return self._session.get(DiscoveryAdmissionClaimRecord, claim_id)

    def get_by_evaluation_id(self, evaluation_id: UUID) -> DiscoveryAdmissionClaimRecord | None:
        """Return the active claim record for an evaluation control."""

        return self._session.exec(
            select(DiscoveryAdmissionClaimRecord).where(
                DiscoveryAdmissionClaimRecord.evaluation_id == evaluation_id
            )
        ).first()

    def _stage_enqueue_from_atomic_admission(
        self,
        *,
        evaluation_id: UUID,
        decision_id: UUID,
        proposal_digest: str,
        bundle_digest: str,
        admission_fingerprint: str,
    ) -> DiscoveryAdmissionClaimRecord:
        """Stage creation of a new pending admission claim record."""

        existing = self.get_by_evaluation_id(evaluation_id)
        if existing is not None:
            if (
                existing.decision_id == decision_id
                and existing.proposal_digest == proposal_digest
                and existing.bundle_digest == bundle_digest
                and existing.admission_fingerprint == admission_fingerprint
            ):
                return existing
            raise ValueError(f"Admission claim already exists for evaluation {evaluation_id}.")

        record = DiscoveryAdmissionClaimRecord(
            claim_id=uuid4(),
            evaluation_id=evaluation_id,
            decision_id=decision_id,
            proposal_digest=proposal_digest,
            bundle_digest=bundle_digest,
            admission_fingerprint=admission_fingerprint,
            owner=None,
            claim_time=None,
            claim_expiry=None,
            fencing_epoch=0,
            attempt_number=1,
            state=DiscoveryAdmissionClaimState.PENDING,
        )
        self._session.add(record)
        return record

    def _stage_claim_from_atomic_admission(
        self,
        claim_id: UUID,
        *,
        owner: str,
        claim_time: datetime,
        claim_expiry: datetime,
        claim_token_digest: str,
        current_epoch: int,
    ) -> bool:
        """CAS claim update from PENDING or expired CLAIMED state."""

        now = utc_now()
        statement = (
            update(DiscoveryAdmissionClaimRecord)
            .where(DiscoveryAdmissionClaimRecord.claim_id == claim_id)
            .where(DiscoveryAdmissionClaimRecord.fencing_epoch == current_epoch)
            .where(
                (DiscoveryAdmissionClaimRecord.state == DiscoveryAdmissionClaimState.PENDING)
                | (
                    (DiscoveryAdmissionClaimRecord.state == DiscoveryAdmissionClaimState.CLAIMED)
                    & (DiscoveryAdmissionClaimRecord.claim_expiry < now)
                )
            )
            .values(
                state=DiscoveryAdmissionClaimState.CLAIMED,
                owner=owner,
                claim_time=claim_time,
                claim_expiry=claim_expiry,
                claim_token_digest=claim_token_digest,
                fencing_epoch=current_epoch + 1,
                attempt_number=DiscoveryAdmissionClaimRecord.attempt_number + 1,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.exec(statement)
        return result.rowcount == 1

    def _stage_cancel_from_atomic_admission(
        self,
        claim_id: UUID,
        *,
        owner: str,
        fencing_epoch: int,
        claim_token_digest: str,
        reason: str,
    ) -> bool:
        """Cancel an active claim before commit."""

        statement = (
            update(DiscoveryAdmissionClaimRecord)
            .where(DiscoveryAdmissionClaimRecord.claim_id == claim_id)
            .where(DiscoveryAdmissionClaimRecord.owner == owner)
            .where(DiscoveryAdmissionClaimRecord.fencing_epoch == fencing_epoch)
            .where(DiscoveryAdmissionClaimRecord.claim_token_digest == claim_token_digest)
            .where(DiscoveryAdmissionClaimRecord.state == DiscoveryAdmissionClaimState.CLAIMED)
            .values(
                state=DiscoveryAdmissionClaimState.CANCELLED,
                invalidation_reason=reason,
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.exec(statement)
        return result.rowcount == 1

    def _stage_invalidate_from_atomic_admission(
        self,
        claim_id: UUID,
        *,
        reason: str,
    ) -> bool:
        """Invalidate an active or pending claim due to stale authority or invalidation."""

        statement = (
            update(DiscoveryAdmissionClaimRecord)
            .where(DiscoveryAdmissionClaimRecord.claim_id == claim_id)
            .where(
                DiscoveryAdmissionClaimRecord.state.in_(
                    [DiscoveryAdmissionClaimState.PENDING, DiscoveryAdmissionClaimState.CLAIMED]
                )
            )
            .values(
                state=DiscoveryAdmissionClaimState.INVALIDATED,
                invalidation_reason=reason,
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.exec(statement)
        return result.rowcount == 1

    def _stage_commit_from_atomic_admission(
        self,
        claim_id: UUID,
        *,
        owner: str,
        fencing_epoch: int,
        claim_token_digest: str,
        discovery_id: UUID,
        discovery_fingerprint: str,
        session_frame_id: UUID,
        session_frame_fingerprint: str,
        committed_at: datetime,
    ) -> bool:
        """Commit an active claim as part of the atomic Discovery transaction."""

        statement = (
            update(DiscoveryAdmissionClaimRecord)
            .where(DiscoveryAdmissionClaimRecord.claim_id == claim_id)
            .where(DiscoveryAdmissionClaimRecord.owner == owner)
            .where(DiscoveryAdmissionClaimRecord.fencing_epoch == fencing_epoch)
            .where(DiscoveryAdmissionClaimRecord.claim_token_digest == claim_token_digest)
            .where(DiscoveryAdmissionClaimRecord.state == DiscoveryAdmissionClaimState.CLAIMED)
            .where(DiscoveryAdmissionClaimRecord.claim_expiry > committed_at)
            .values(
                state=DiscoveryAdmissionClaimState.COMMITTED,
                discovery_id=discovery_id,
                discovery_fingerprint=discovery_fingerprint,
                session_frame_id=session_frame_id,
                session_frame_fingerprint=session_frame_fingerprint,
                committed_at=committed_at,
                updated_at=committed_at,
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.exec(statement)
        return result.rowcount == 1
