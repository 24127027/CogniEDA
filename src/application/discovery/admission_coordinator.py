"""Supported service coordinator for Discovery admission attempts and recovery."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from application.discovery.admission_service import AtomicDiscoveryAdmissionService
from db.models import EvaluationControlRecord, ProposalDecisionRecord
from schemas.discovery import AtomicDiscoveryAdmissionResult
from schemas.enums import EvaluationControlState, GovernanceDecisionOutcome

__all__ = ["DiscoveryAdmissionCoordinator"]


class DiscoveryAdmissionCoordinator:
    """Supported coordinator for enqueueing, executing, and reclaiming Discovery admissions."""

    def __init__(
        self,
        session: Session,
        *,
        workspace_id: str,
        session_id: str | None = None,
    ) -> None:
        if not workspace_id.strip():
            raise ValueError("Coordinator requires a non-empty workspace identity.")
        if session_id is not None and not session_id.strip():
            raise ValueError("Session identity must be non-empty when supplied.")
        self._session = session
        self._workspace_id = workspace_id
        self._session_id = session_id
        self._admission_service = AtomicDiscoveryAdmissionService(
            session,
            workspace_id=workspace_id,
            session_id=session_id,
        )

    def process_eligible_admissions(
        self,
        *,
        claim_owner: str = "system:admission_coordinator",
        lease_duration_seconds: int = 300,
    ) -> list[AtomicDiscoveryAdmissionResult]:
        """Discover eligible approved decisions and execute their admissions."""

        eligible_pairs = self.find_eligible_evaluation_decisions()
        results: list[AtomicDiscoveryAdmissionResult] = []

        for eval_id, decision_id in eligible_pairs:
            result = self._admission_service.execute_admission(
                evaluation_id=eval_id,
                decision_id=decision_id,
                claim_owner=claim_owner,
                lease_duration_seconds=lease_duration_seconds,
            )
            results.append(result)

        return results

    def find_eligible_evaluation_decisions(self) -> list[tuple[UUID, UUID]]:
        """Return (evaluation_id, decision_id) pairs eligible for Discovery admission."""

        self._session.expire_all()
        evaluations = self._session.exec(
            select(EvaluationControlRecord).where(
                EvaluationControlRecord.state == EvaluationControlState.PROPOSAL_READY
            )
        ).all()

        eligible: list[tuple[UUID, UUID]] = []
        for eval_rec in evaluations:
            decision = self._session.exec(
                select(ProposalDecisionRecord).where(
                    ProposalDecisionRecord.evaluation_id == eval_rec.evaluation_id,
                    ProposalDecisionRecord.decision == GovernanceDecisionOutcome.APPROVED,
                    ProposalDecisionRecord.consumed == False,  # noqa: E712
                )
            ).first()
            if decision is not None:
                eligible.append((eval_rec.evaluation_id, decision.decision_id))

        return eligible

    def execute_single_admission(
        self,
        evaluation_id: UUID,
        decision_id: UUID,
        *,
        claim_owner: str = "system:admission_coordinator",
        lease_duration_seconds: int = 300,
    ) -> AtomicDiscoveryAdmissionResult:
        """Execute one specific authorized Discovery admission."""

        return self._admission_service.execute_admission(
            evaluation_id=evaluation_id,
            decision_id=decision_id,
            claim_owner=claim_owner,
            lease_duration_seconds=lease_duration_seconds,
        )
