"""Application service for atomic Discovery admission cutover."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID, uuid5

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from application.evaluation import (
    SynthesisBundleError,
    build_synthesis_bundle,
    compute_evaluation_key,
    compute_evidence_set_digest,
)
from application.execution.transition_service import (
    ExecutionAttemptTransitionService,
)
from application.governance import (
    DiscoveryAdmissionGovernanceService,
    compute_decision_fingerprint,
    compute_governance_authority_fingerprint,
)
from db.models import (
    AnalysisFrameRecord,
    DataProfileRecord,
    DiscoveryAdmissionClaimRecord,
    DiscoveryRecord,
    EvaluationControlRecord,
    EvidenceRecord,
    ExecutionRunRecord,
    GovernanceAuthorityRecord,
    HypothesisRecord,
    ObjectiveRecord,
    ProposalDecisionRecord,
    SessionFrameRecord,
    TaskRecord,
    utc_now,
)
from memory.session_frame import SessionFrameBuilder
from repositories.common import record_to_schema, schema_to_record_payload
from repositories.discovery_admission_claim_repository import DiscoveryAdmissionClaimRepository
from repositories.discovery_repository import DiscoveryRepository
from repositories.session_frame_repository import SESSION_FRAME_JSON_FIELDS
from schemas.artifacts import DataProfile, Discovery, Evidence, Objective, SessionFrame
from schemas.canonical import canonical_sha256
from schemas.common import ImmutableCogniEDABaseModel, NonEmptyStr
from schemas.discovery_admission_contracts import (
    DiscoveryAdmissionPlan,
)
from schemas.enums import (
    DataProfileLifecycleState,
    DiscoveryAdmissionClaimState,
    DiscoveryAdmissionReplayDisposition,
    DiscoveryLifecycleState,
    EvaluationControlState,
    EvidenceLifecycleState,
    GovernanceDecisionOutcome,
    HypothesisStatus,
    ObjectiveStatus,
    TaskKind,
    TaskLifecycleState,
    ValiditySourceState,
)
from schemas.evaluation import (
    DiscoveryProposal,
    DiscoverySynthesisBundle,
    compute_proposal_digest,
    validate_proposal_against_bundle,
)

_CONCLUSION_FRAME_NAMESPACE = UUID("373fed23-80ef-43cc-9e5e-2c379dcfa8c8")


class DiscoveryAdmissionError(ValueError):
    """Base exception raised when Discovery admission eligibility or verification fails."""


class DiscoveryAdmissionConflictError(DiscoveryAdmissionError):
    """Raised when an admission conflict or partial state mismatch is detected."""


AtomicDiscoveryAdmissionError = DiscoveryAdmissionError
AtomicDiscoveryAdmissionConflictError = DiscoveryAdmissionConflictError


class AtomicDiscoveryAdmissionResult(ImmutableCogniEDABaseModel):
    """Result envelope for an atomic Discovery admission transaction."""

    disposition: DiscoveryAdmissionReplayDisposition
    discovery_id: UUID
    evaluation_id: UUID
    decision_id: UUID
    hypothesis_id: UUID
    task_id: UUID
    session_frame_id: UUID
    admission_fingerprint: NonEmptyStr
    committed_at: datetime


class DiscoveryAdmissionLease(ImmutableCogniEDABaseModel):
    """Opaque, expiring authority for one claimed admission attempt."""

    claim_id: UUID
    evaluation_id: UUID
    decision_id: UUID
    owner: NonEmptyStr
    fencing_epoch: int
    claim_token: NonEmptyStr
    claim_expiry: datetime


class AtomicDiscoveryAdmissionService:
    """Sole supported production service for atomic Discovery admission cutover."""

    def __init__(
        self,
        session: Session,
        *,
        workspace_id: str,
        session_id: str | None = None,
        failure_injector: Callable[[str], None] | None = None,
    ) -> None:
        if not workspace_id.strip():
            raise ValueError("Atomic Discovery admission requires a non-empty workspace identity.")
        if session_id is not None and not session_id.strip():
            raise ValueError("Session identity must be non-empty when supplied.")
        self._session = session
        self._workspace_id = workspace_id
        self._session_id = session_id
        self._failure_injector = failure_injector
        self._governance_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id=workspace_id,
            session_id=session_id,
        )
        self._claim_repo = DiscoveryAdmissionClaimRepository(session)

    def execute_admission(
        self,
        *,
        evaluation_id: UUID,
        decision_id: UUID,
        claim_owner: str = "system:admission_worker",
        lease_duration_seconds: int = 300,
    ) -> AtomicDiscoveryAdmissionResult:
        """Durably enqueue and claim, then execute the sole atomic write transaction."""

        self._require_clean_unit_of_work()
        existing_claim = self._claim_repo.get_by_evaluation_id(evaluation_id)
        if (
            existing_claim is not None
            and existing_claim.state == DiscoveryAdmissionClaimState.COMMITTED
        ):
            reconstruction = self._reconstruct_and_verify_authority(
                evaluation_id=evaluation_id,
                decision_id=decision_id,
            )
            existing_discovery = self._session.get(
                DiscoveryRecord,
                existing_claim.discovery_id,
            )
            if existing_discovery is None:
                raise DiscoveryAdmissionConflictError(
                    "Committed admission claim has no exact Discovery."
                )
            return self._handle_existing_discovery(
                existing_discovery,
                reconstruction=reconstruction,
            )

        self.enqueue_admission(
            evaluation_id=evaluation_id,
            decision_id=decision_id,
        )
        lease = self.claim_admission(
            evaluation_id=evaluation_id,
            decision_id=decision_id,
            claim_owner=claim_owner,
            lease_duration_seconds=lease_duration_seconds,
        )
        return self.execute_claimed_admission(lease)

    def enqueue_admission(
        self,
        *,
        evaluation_id: UUID,
        decision_id: UUID,
    ) -> DiscoveryAdmissionClaimRecord:
        """Persist exact admission identity before any worker may claim it."""

        self._require_clean_unit_of_work()
        reconstruction = self._reconstruct_and_verify_authority(
            evaluation_id=evaluation_id,
            decision_id=decision_id,
        )
        self._verify_admission_preconditions(reconstruction)
        try:
            claim = self._claim_repo.stage_enqueue(
                evaluation_id=evaluation_id,
                decision_id=decision_id,
                proposal_digest=reconstruction.proposal_digest,
                bundle_digest=reconstruction.bundle.input_digest,
                admission_fingerprint=reconstruction.plan.admission_fingerprint,
            )
            self._session.commit()
            self._session.refresh(claim)
            return claim
        except IntegrityError as exc:
            self._session.rollback()
            winner = self._claim_repo.get_by_evaluation_id(evaluation_id)
            if winner is not None and self._claim_matches_reconstruction(
                winner,
                reconstruction,
            ):
                return winner
            raise DiscoveryAdmissionConflictError(
                "Concurrent admission enqueue produced incompatible authority."
            ) from exc

    def claim_admission(
        self,
        *,
        evaluation_id: UUID,
        decision_id: UUID,
        claim_owner: str,
        lease_duration_seconds: int = 300,
    ) -> DiscoveryAdmissionLease:
        """Claim or reclaim one durable admission control with a higher fence."""

        self._require_clean_unit_of_work()
        if not claim_owner.strip():
            raise DiscoveryAdmissionError("Admission claim owner cannot be empty.")
        if lease_duration_seconds <= 0:
            raise DiscoveryAdmissionError("Admission lease duration must be positive.")
        claim = self._claim_repo.get_by_evaluation_id(evaluation_id)
        if claim is None:
            raise DiscoveryAdmissionError(
                f"Admission has not been durably enqueued for evaluation {evaluation_id}."
            )
        if claim.decision_id != decision_id:
            raise DiscoveryAdmissionConflictError("Admission claim decision binding mismatch.")
        now = utc_now()
        claim_expiry = now + timedelta(seconds=lease_duration_seconds)
        claim_token = token_urlsafe(32)
        token_digest = self._claim_token_digest(claim_token)
        success = self._claim_repo.stage_claim(
            claim.claim_id,
            owner=claim_owner,
            claim_time=now,
            claim_expiry=claim_expiry,
            claim_token_digest=token_digest,
            current_epoch=claim.fencing_epoch,
        )
        if not success:
            self._session.rollback()
            raise DiscoveryAdmissionConflictError(
                f"Admission claim for evaluation {evaluation_id} is live, terminal, or stale."
            )
        self._session.commit()
        refreshed = self._claim_repo.get_by_id(claim.claim_id)
        if refreshed is None:
            raise DiscoveryAdmissionConflictError("Claim disappeared after durable claim commit.")
        return DiscoveryAdmissionLease(
            claim_id=refreshed.claim_id,
            evaluation_id=refreshed.evaluation_id,
            decision_id=refreshed.decision_id,
            owner=claim_owner,
            fencing_epoch=refreshed.fencing_epoch,
            claim_token=claim_token,
            claim_expiry=claim_expiry,
        )

    def execute_claimed_admission(
        self,
        lease: DiscoveryAdmissionLease,
    ) -> AtomicDiscoveryAdmissionResult:
        """Reconstruct current authority after claim and atomically commit the complete chain."""

        self._require_clean_unit_of_work()
        claim = self._load_and_verify_live_claim(lease)
        reconstruction = self._reconstruct_and_verify_authority(
            evaluation_id=lease.evaluation_id,
            decision_id=lease.decision_id,
        )
        if not self._claim_matches_reconstruction(claim, reconstruction):
            self._invalidate_stale_claim(
                claim.claim_id, "admission authority changed after enqueue"
            )
            raise DiscoveryAdmissionConflictError(
                "Admission claim no longer matches reconstructed authority."
            )
        existing_discovery = self._session.exec(
            select(DiscoveryRecord).where(
                DiscoveryRecord.hypothesis_id == reconstruction.hypothesis.hypothesis_id
            )
        ).first()
        if existing_discovery is not None:
            return self._handle_existing_discovery(
                existing_discovery,
                reconstruction=reconstruction,
            )
        self._verify_admission_preconditions(reconstruction)

        try:
            committed_at = utc_now()
            self._stage_lineage_guards(reconstruction, committed_at=committed_at)
            # SQLite's first guarded write holds the database writer lock. Rebuild
            # the complete authority under that lock so no detached pre-lock plan
            # or bundle snapshot supplies scientific content to persistence.
            reconstruction = self._reconstruct_and_verify_authority(
                evaluation_id=lease.evaluation_id,
                decision_id=lease.decision_id,
            )
            if not self._claim_matches_reconstruction(claim, reconstruction):
                raise DiscoveryAdmissionConflictError(
                    "Admission authority changed while acquiring write-time guards."
                )
            self._verify_admission_preconditions(reconstruction)
            self._inject("lineage_guards")

            deterministic_discovery_id = reconstruction.plan.deterministic_discovery_id
            discovery, discovery_schema, discovery_fingerprint = self._stage_discovery_insert(
                discovery_id=deterministic_discovery_id,
                reconstruction=reconstruction,
                created_at=committed_at,
            )
            self._session.flush()
            self._inject("discovery")

            session_frame, session_frame_fingerprint = self._stage_conclusion_session_frame(
                discovery=discovery_schema,
                reconstruction=reconstruction,
                created_at=committed_at,
            )
            self._session.flush()
            self._inject("session_frame")

            self._stage_hypothesis_transition(
                hypothesis_id=reconstruction.hypothesis.hypothesis_id,
            )
            self._inject("hypothesis")

            self._stage_task_transition(
                task_id=reconstruction.task.task_id,
            )
            self._inject("task")

            self._stage_evaluation_control_commit(
                evaluation_id=lease.evaluation_id,
                expected_proposal_digest=reconstruction.proposal_digest,
                expected_bundle_digest=reconstruction.bundle.input_digest,
                expected_fencing_epoch=reconstruction.evaluation_record.fencing_epoch,
            )
            self._inject("evaluation")

            self._stage_claim_commit(
                claim_id=claim.claim_id,
                lease=lease,
                discovery_id=deterministic_discovery_id,
                discovery_fingerprint=discovery_fingerprint,
                session_frame_id=session_frame.session_frame_id,
                session_frame_fingerprint=session_frame_fingerprint,
                committed_at=committed_at,
            )
            self._inject("claim")

            self._stage_decision_consumption(
                decision_id=lease.decision_id,
                evaluation_id=lease.evaluation_id,
                hypothesis_id=reconstruction.hypothesis.hypothesis_id,
                proposal_digest=reconstruction.proposal_digest,
                consuming_discovery_id=deterministic_discovery_id,
                consumed_at=committed_at,
            )
            self._inject("decision")

            self._session.flush()
            self._inject("pre_commit")
            self._session.commit()

            return AtomicDiscoveryAdmissionResult(
                disposition=DiscoveryAdmissionReplayDisposition.NEW,
                discovery_id=deterministic_discovery_id,
                evaluation_id=lease.evaluation_id,
                decision_id=lease.decision_id,
                hypothesis_id=reconstruction.hypothesis.hypothesis_id,
                task_id=reconstruction.task.task_id,
                session_frame_id=session_frame.session_frame_id,
                admission_fingerprint=reconstruction.plan.admission_fingerprint,
                committed_at=committed_at,
            )
        except Exception as exc:
            self._session.rollback()
            if isinstance(exc, DiscoveryAdmissionError):
                raise
            raise DiscoveryAdmissionError(
                f"Atomic Discovery admission transaction failed: {exc}"
            ) from exc

    def reclaim_expired_admission(
        self,
        *,
        evaluation_id: UUID,
        decision_id: UUID,
        claim_owner: str,
        lease_duration_seconds: int = 300,
    ) -> DiscoveryAdmissionLease:
        """Reclaim an expired admission with a new token and strictly higher fence."""

        return self.claim_admission(
            evaluation_id=evaluation_id,
            decision_id=decision_id,
            claim_owner=claim_owner,
            lease_duration_seconds=lease_duration_seconds,
        )

    def cancel_claimed_admission(
        self,
        lease: DiscoveryAdmissionLease,
        *,
        reason: str,
    ) -> None:
        """Durably cancel the exact live claim; stale owners cannot cancel."""

        if not reason.strip():
            raise DiscoveryAdmissionError("Admission cancellation reason cannot be empty.")
        claim = self._load_and_verify_live_claim(lease)
        if not self._claim_repo.stage_cancel(
            claim.claim_id,
            owner=lease.owner,
            fencing_epoch=lease.fencing_epoch,
            claim_token_digest=self._claim_token_digest(lease.claim_token),
            reason=reason.strip(),
        ):
            self._session.rollback()
            raise DiscoveryAdmissionConflictError("Admission cancellation lost its fence.")
        self._session.commit()

    def _reconstruct_and_verify_authority(
        self,
        *,
        evaluation_id: UUID,
        decision_id: UUID,
    ) -> _AdmissionReconstruction:
        """Rebuild every durable authority component from primary repositories."""

        self._session.expire_all()

        # 1. Evaluation record
        eval_record = self._session.get(EvaluationControlRecord, evaluation_id)
        if eval_record is None:
            raise DiscoveryAdmissionError(f"EvaluationControlRecord not found: {evaluation_id}")
        if eval_record.state not in (
            EvaluationControlState.PROPOSAL_READY,
            EvaluationControlState.COMMITTED,
        ):
            raise DiscoveryAdmissionError(
                "Evaluation control state must be PROPOSAL_READY or COMMITTED, "
                f"got: {eval_record.state}"
            )
        if not eval_record.proposal_digest or not eval_record.serialized_proposal:
            raise DiscoveryAdmissionError("Evaluation record missing proposal provenance.")

        # 2. Decision record
        decision_record = self._session.get(ProposalDecisionRecord, decision_id)
        if decision_record is None:
            raise DiscoveryAdmissionError(f"ProposalDecisionRecord not found: {decision_id}")
        if decision_record.evaluation_id != evaluation_id:
            raise DiscoveryAdmissionError("Decision record evaluation_id mismatch.")
        if decision_record.decision != GovernanceDecisionOutcome.APPROVED:
            raise DiscoveryAdmissionError(
                f"Governance decision must be APPROVED, got: {decision_record.decision}"
            )
        if decision_record.consumed and eval_record.state != EvaluationControlState.COMMITTED:
            raise DiscoveryAdmissionError(f"Proposal decision {decision_id} is already consumed.")

        # 3. Governance authority grant
        authority_grant = self._session.get(GovernanceAuthorityRecord, decision_record.authority_id)
        if authority_grant is None:
            raise DiscoveryAdmissionError(
                f"GovernanceAuthorityRecord not found: {decision_record.authority_id}"
            )
        now = utc_now()
        if eval_record.state != EvaluationControlState.COMMITTED and (
            not authority_grant.active
            or (
                authority_grant.expires_at is not None
                and self._as_utc(authority_grant.expires_at) <= now
            )
        ):
            raise DiscoveryAdmissionError("Governance authority grant is inactive or expired.")
        if authority_grant.workspace_id != self._workspace_id:
            raise DiscoveryAdmissionError("Governance authority workspace mismatch.")

        expected_grant_fingerprint = compute_governance_authority_fingerprint(
            authority_id=authority_grant.authority_id,
            actor_identity=authority_grant.actor_identity,
            authority_class=authority_grant.authority_class,
            workspace_id=authority_grant.workspace_id,
            session_id=authority_grant.session_id,
            purpose=authority_grant.purpose,
            operation_type=authority_grant.operation_type,
            issued_by=authority_grant.issued_by,
            issued_at=authority_grant.issued_at,
            expires_at=authority_grant.expires_at,
        )
        if authority_grant.authority_fingerprint != expected_grant_fingerprint:
            raise DiscoveryAdmissionError("Governance authority grant fingerprint is invalid.")

        expected_decision_fingerprint = compute_decision_fingerprint(
            decision_id=decision_record.decision_id,
            authority_id=decision_record.authority_id,
            evaluation_id=decision_record.evaluation_id,
            evaluation_key=decision_record.evaluation_key,
            hypothesis_id=decision_record.hypothesis_id,
            task_id=decision_record.task_id,
            proposal_digest=decision_record.proposal_digest,
            bundle_digest=decision_record.bundle_digest,
            evidence_set_digest=decision_record.evidence_set_digest,
            decision=decision_record.decision,
            actor=decision_record.actor,
            actor_authority_type=decision_record.actor_authority_type,
            workspace_id=decision_record.workspace_id,
            session_id=decision_record.session_id,
            purpose=decision_record.purpose,
            operation_type=decision_record.operation_type,
            decision_timestamp=decision_record.decision_timestamp,
            reason=decision_record.reason,
        )
        if decision_record.decision_fingerprint != expected_decision_fingerprint:
            raise DiscoveryAdmissionError("Proposal decision fingerprint is invalid.")

        # 4. Hypothesis & Task
        hypothesis = self._session.get(HypothesisRecord, eval_record.hypothesis_id)
        if hypothesis is None:
            raise DiscoveryAdmissionError(
                f"HypothesisRecord not found: {eval_record.hypothesis_id}"
            )
        if eval_record.state == EvaluationControlState.PROPOSAL_READY:
            if hypothesis.status != HypothesisStatus.READY_FOR_EVALUATION:
                raise DiscoveryAdmissionError(
                    f"Hypothesis status must be READY_FOR_EVALUATION, got: {hypothesis.status}"
                )
        elif hypothesis.status not in (
            HypothesisStatus.READY_FOR_EVALUATION,
            HypothesisStatus.EVALUATED,
        ):
            raise DiscoveryAdmissionError(
                "Hypothesis status must be READY_FOR_EVALUATION or EVALUATED, "
                f"got: {hypothesis.status}"
            )

        task = self._session.get(TaskRecord, hypothesis.task_id)
        if task is None:
            raise DiscoveryAdmissionError(f"TaskRecord not found: {hypothesis.task_id}")
        if task.task_kind != TaskKind.ANALYTICAL:
            raise DiscoveryAdmissionError(
                f"Task must be ANALYTICAL for Discovery admission, got: {task.task_kind}"
            )
        if eval_record.state == EvaluationControlState.PROPOSAL_READY:
            if task.lifecycle_state != TaskLifecycleState.ACTIVE:
                raise DiscoveryAdmissionError(
                    f"Task lifecycle state must be ACTIVE, got: {task.lifecycle_state}"
                )
        elif task.lifecycle_state not in (TaskLifecycleState.ACTIVE, TaskLifecycleState.COMPLETED):
            raise DiscoveryAdmissionError(
                f"Task lifecycle state must be ACTIVE or COMPLETED, got: {task.lifecycle_state}"
            )

        # Verify task is terminal analytical (no child tasks)
        child_task = self._session.exec(
            select(TaskRecord).where(TaskRecord.parent_task_id == task.task_id)
        ).first()
        if child_task is not None:
            raise DiscoveryAdmissionError(
                f"Task {task.task_id} has child tasks and is not a terminal analytical Task."
            )

        # 5. Package 2 protected bundle reconstruction
        try:
            bundle, manifest = build_synthesis_bundle(
                self._session,
                hypothesis.hypothesis_id,
                contract_version=eval_record.contract_version,
                allow_evaluated=True,
            )
        except SynthesisBundleError as exc:
            raise DiscoveryAdmissionError(f"Failed to reconstruct synthesis bundle: {exc}") from exc

        if eval_record.bundle_digest != bundle.input_digest:
            raise DiscoveryAdmissionError("Persisted bundle_digest does not match current bundle.")
        if eval_record.evidence_set_digest != compute_evidence_set_digest(bundle):
            raise DiscoveryAdmissionError(
                "Persisted evidence_set_digest does not match current bundle."
            )
        if eval_record.evaluation_key != compute_evaluation_key(bundle):
            raise DiscoveryAdmissionError("Persisted evaluation_key does not match current bundle.")

        # 6. Proposal validation against bundle
        try:
            proposal = DiscoveryProposal.model_validate(eval_record.serialized_proposal)
            validate_proposal_against_bundle(proposal, bundle)
        except ValueError as exc:
            raise DiscoveryAdmissionError(f"Proposal validation failed: {exc}") from exc

        proposal_digest = compute_proposal_digest(proposal, bundle.input_digest)
        if eval_record.proposal_digest != proposal_digest:
            raise DiscoveryAdmissionError("Persisted proposal_digest mismatch.")
        if decision_record.proposal_digest != proposal_digest:
            raise DiscoveryAdmissionError("Decision proposal_digest mismatch.")

        # 7. Package 4 validity revalidation of all lineage nodes
        for item in bundle.admitted_evidence:
            ev_rec = self._session.get(EvidenceRecord, item.evidence_id)
            if ev_rec is None or ev_rec.lifecycle_state != EvidenceLifecycleState.ACTIVE:
                raise DiscoveryAdmissionError(
                    f"Admitted Evidence {item.evidence_id} is not ACTIVE."
                )

        for frame in bundle.analysis_frames:
            af_rec = self._session.get(AnalysisFrameRecord, frame.analysis_frame_id)
            if af_rec is None or af_rec.validity_state != ValiditySourceState.ACTIVE:
                raise DiscoveryAdmissionError(
                    f"AnalysisFrame {frame.analysis_frame_id} validity is not ACTIVE."
                )

        for run in bundle.execution_runs:
            run_rec = self._session.get(ExecutionRunRecord, run.execution_run_id)
            if run_rec is None or run_rec.validity_state != ValiditySourceState.ACTIVE:
                raise DiscoveryAdmissionError(
                    f"ExecutionRun {run.execution_run_id} validity is not ACTIVE."
                )

        dp_rec = self._session.get(DataProfileRecord, bundle.data_profile.data_profile_id)
        if dp_rec is None or not dp_rec.accepted_as_ground_truth:
            raise DiscoveryAdmissionError(
                f"DataProfile {bundle.data_profile.data_profile_id} is not active ground truth."
            )

        # 8. Reconstruct Package 3 deterministic plan
        plan = self._governance_service.create_admission_plan(evaluation_id, decision_id)

        return _AdmissionReconstruction(
            evaluation_record=eval_record,
            decision_record=decision_record,
            authority_grant=authority_grant,
            hypothesis=hypothesis,
            task=task,
            bundle=bundle,
            proposal=proposal,
            proposal_digest=proposal_digest,
            plan=plan,
        )

    def _verify_admission_preconditions(self, reconstruction: _AdmissionReconstruction) -> None:
        """Verify explicit admission eligibility invariants before executing transaction."""

        if reconstruction.evaluation_record.state != EvaluationControlState.PROPOSAL_READY:
            raise DiscoveryAdmissionError(
                "Evaluation control state must be PROPOSAL_READY for admission, "
                f"got: {reconstruction.evaluation_record.state}"
            )
        if reconstruction.decision_record.consumed:
            raise DiscoveryAdmissionError(
                f"Proposal decision {reconstruction.decision_record.decision_id} "
                "is already consumed."
            )
        if (
            reconstruction.proposal.validity_basis.hypothesis_id
            != reconstruction.hypothesis.hypothesis_id
        ):
            raise DiscoveryAdmissionError("Proposal hypothesis_id mismatch.")
        if (
            reconstruction.proposal.validity_basis.data_profile_id
            != reconstruction.bundle.data_profile.data_profile_id
        ):
            raise DiscoveryAdmissionError("Proposal profile_id mismatch.")

    def _stage_discovery_insert(
        self,
        *,
        discovery_id: UUID,
        reconstruction: _AdmissionReconstruction,
        created_at: datetime,
    ) -> tuple[DiscoveryRecord, Discovery, str]:
        proposal = reconstruction.proposal
        discovery = Discovery(
            discovery_id=discovery_id,
            hypothesis_id=reconstruction.hypothesis.hypothesis_id,
            evidence_ids=list(proposal.evidence_ids),
            claim=proposal.claim,
            epistemic_status=proposal.epistemic_status,
            analysis_intent=reconstruction.hypothesis.analysis_intent,
            uncertainty=proposal.validity_basis.uncertainty,
            scope=proposal.scope,
            validity_basis=proposal.validity_basis,
            limitations=list(proposal.limitations),
            invalidators=list(proposal.validity_basis.invalidators),
            lifecycle_state=DiscoveryLifecycleState.ACTIVE,
            review_reasons=[],
            flagged_by_evidence_ids=[],
            created_at=created_at,
        )
        record = DiscoveryRepository(self._session)._stage_create_from_atomic_admission(discovery)
        return record, discovery, self._discovery_fingerprint(discovery)

    def _stage_lineage_guards(
        self,
        reconstruction: _AdmissionReconstruction,
        *,
        committed_at: datetime,
    ) -> None:
        """Acquire the write transaction while proving every validity source is still active."""

        authority = reconstruction.authority_grant
        authority_statement = (
            update(GovernanceAuthorityRecord)
            .where(GovernanceAuthorityRecord.authority_id == authority.authority_id)
            .where(GovernanceAuthorityRecord.active == True)  # noqa: E712
            .where(
                GovernanceAuthorityRecord.authority_fingerprint == authority.authority_fingerprint
            )
        )
        if authority.expires_at is not None:
            authority_statement = authority_statement.where(
                GovernanceAuthorityRecord.expires_at > committed_at
            )
        authority_result = self._session.exec(
            authority_statement.values(active=GovernanceAuthorityRecord.active).execution_options(
                synchronize_session=False
            )
        )
        self._expect_one(authority_result, f"GovernanceAuthority {authority.authority_id}")

        profile_id = reconstruction.bundle.data_profile.data_profile_id
        profile_result = self._session.exec(
            update(DataProfileRecord)
            .where(DataProfileRecord.profile_id == profile_id)
            .where(DataProfileRecord.accepted_as_ground_truth == True)  # noqa: E712
            .where(DataProfileRecord.lifecycle_state == DataProfileLifecycleState.ACTIVE)
            .values(lifecycle_state=DataProfileRecord.lifecycle_state)
            .execution_options(synchronize_session=False)
        )
        self._expect_one(profile_result, f"DataProfile {profile_id}")

        for frame in reconstruction.bundle.analysis_frames:
            result = self._session.exec(
                update(AnalysisFrameRecord)
                .where(AnalysisFrameRecord.analysis_frame_id == frame.analysis_frame_id)
                .where(AnalysisFrameRecord.validity_state == ValiditySourceState.ACTIVE)
                .values(validity_state=AnalysisFrameRecord.validity_state)
                .execution_options(synchronize_session=False)
            )
            self._expect_one(result, f"AnalysisFrame {frame.analysis_frame_id}")

        for run in reconstruction.bundle.execution_runs:
            if not ExecutionAttemptTransitionService(self._session).stage_assert_validity_active(
                run.execution_run_id
            ):
                raise DiscoveryAdmissionConflictError(
                    f"Admission lost its fence for ExecutionRun {run.execution_run_id}."
                )

        for evidence in reconstruction.bundle.admitted_evidence:
            result = self._session.exec(
                update(EvidenceRecord)
                .where(EvidenceRecord.evidence_id == evidence.evidence_id)
                .where(EvidenceRecord.lifecycle_state == EvidenceLifecycleState.ACTIVE)
                .values(lifecycle_state=EvidenceRecord.lifecycle_state)
                .execution_options(synchronize_session=False)
            )
            self._expect_one(result, f"Evidence {evidence.evidence_id}")

    def _stage_hypothesis_transition(self, *, hypothesis_id: UUID) -> None:
        statement = (
            update(HypothesisRecord)
            .where(HypothesisRecord.hypothesis_id == hypothesis_id)
            .where(HypothesisRecord.status == HypothesisStatus.READY_FOR_EVALUATION)
            .values(
                status=HypothesisStatus.EVALUATED,
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.exec(statement)
        if result.rowcount != 1:
            raise DiscoveryAdmissionConflictError(
                "Hypothesis transition READY_FOR_EVALUATION -> EVALUATED failed "
                f"for {hypothesis_id}."
            )

    def _stage_task_transition(self, *, task_id: UUID) -> None:
        statement = (
            update(TaskRecord)
            .where(TaskRecord.task_id == task_id)
            .where(TaskRecord.lifecycle_state == TaskLifecycleState.ACTIVE)
            .values(
                lifecycle_state=TaskLifecycleState.COMPLETED,
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.exec(statement)
        if result.rowcount != 1:
            raise DiscoveryAdmissionConflictError(
                f"Task transition ACTIVE -> COMPLETED failed for {task_id}."
            )

    def _stage_evaluation_control_commit(
        self,
        *,
        evaluation_id: UUID,
        expected_proposal_digest: str,
        expected_bundle_digest: str,
        expected_fencing_epoch: int,
    ) -> None:
        statement = (
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == evaluation_id)
            .where(EvaluationControlRecord.state == EvaluationControlState.PROPOSAL_READY)
            .where(EvaluationControlRecord.proposal_digest == expected_proposal_digest)
            .where(EvaluationControlRecord.bundle_digest == expected_bundle_digest)
            .where(EvaluationControlRecord.fencing_epoch == expected_fencing_epoch)
            .values(
                state=EvaluationControlState.COMMITTED,
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.exec(statement)
        if result.rowcount != 1:
            raise DiscoveryAdmissionConflictError(
                f"Evaluation control commit failed for evaluation {evaluation_id}."
            )

    def _stage_decision_consumption(
        self,
        *,
        decision_id: UUID,
        evaluation_id: UUID,
        hypothesis_id: UUID,
        proposal_digest: str,
        consuming_discovery_id: UUID,
        consumed_at: datetime,
    ) -> None:
        statement = (
            update(ProposalDecisionRecord)
            .where(ProposalDecisionRecord.decision_id == decision_id)
            .where(ProposalDecisionRecord.evaluation_id == evaluation_id)
            .where(ProposalDecisionRecord.hypothesis_id == hypothesis_id)
            .where(ProposalDecisionRecord.proposal_digest == proposal_digest)
            .where(ProposalDecisionRecord.decision == GovernanceDecisionOutcome.APPROVED)
            .where(ProposalDecisionRecord.consumed == False)  # noqa: E712
            .values(
                consumed=True,
                consumed_at=consumed_at,
                consumed_by=str(consuming_discovery_id),
                updated_at=consumed_at,
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.exec(statement)
        if result.rowcount != 1:
            raise DiscoveryAdmissionConflictError(
                f"Decision consumption failed for decision {decision_id}."
            )

    def _stage_claim_commit(
        self,
        *,
        claim_id: UUID,
        lease: DiscoveryAdmissionLease,
        discovery_id: UUID,
        discovery_fingerprint: str,
        session_frame_id: UUID,
        session_frame_fingerprint: str,
        committed_at: datetime,
    ) -> None:
        success = self._claim_repo.stage_commit(
            claim_id,
            owner=lease.owner,
            fencing_epoch=lease.fencing_epoch,
            claim_token_digest=self._claim_token_digest(lease.claim_token),
            discovery_id=discovery_id,
            discovery_fingerprint=discovery_fingerprint,
            session_frame_id=session_frame_id,
            session_frame_fingerprint=session_frame_fingerprint,
            committed_at=committed_at,
        )
        if not success:
            raise DiscoveryAdmissionConflictError(
                f"Admission claim commit failed for claim {claim_id}."
            )

    def _stage_conclusion_session_frame(
        self,
        *,
        discovery: Discovery,
        reconstruction: _AdmissionReconstruction,
        created_at: datetime,
    ) -> tuple[SessionFrameRecord, str]:
        profile_rec = self._session.get(
            DataProfileRecord, reconstruction.bundle.data_profile.data_profile_id
        )
        if profile_rec is None:
            raise DiscoveryAdmissionError("DataProfile Record missing for SessionFrame.")
        objective_rec = self._session.exec(
            select(ObjectiveRecord).where(ObjectiveRecord.status == ObjectiveStatus.ACTIVE)
        ).one_or_none()
        if objective_rec is None:
            raise DiscoveryAdmissionError(
                "Exactly one active Objective is required for conclusion SessionFrame."
            )
        evidence_records = [
            self._session.get(EvidenceRecord, evidence_id)
            for evidence_id in reconstruction.proposal.evidence_ids
        ]
        if any(record is None for record in evidence_records):
            raise DiscoveryAdmissionError("Evidence disappeared while building SessionFrame.")
        frame_id = uuid5(
            _CONCLUSION_FRAME_NAMESPACE,
            f"conclusion-frame/v1:{discovery.discovery_id}",
        )
        frame = (
            SessionFrameBuilder()
            .build(
                objective=record_to_schema(Objective, objective_rec),
                frame_topic=f"Discovery: {reconstruction.hypothesis.statement[:80]}",
                frame_outcome=discovery.claim.statement,
                data_profiles=[record_to_schema(DataProfile, profile_rec)],
                discoveries=[discovery],
                evidence=[
                    record_to_schema(Evidence, record)
                    for record in evidence_records
                    if record is not None
                ],
                key_warnings=[
                    "Assumptions were excluded from Discovery synthesis context.",
                    *list(discovery.limitations),
                ],
            )
            .model_copy(
                update={
                    "session_frame_id": frame_id,
                    "created_at": created_at,
                }
            )
        )
        frame_record = SessionFrameRecord(
            **schema_to_record_payload(frame, json_fields=SESSION_FRAME_JSON_FIELDS)
        )
        self._session.add(frame_record)
        return frame_record, self._session_frame_fingerprint(frame)

    def _handle_existing_discovery(
        self,
        existing: DiscoveryRecord,
        *,
        reconstruction: _AdmissionReconstruction,
    ) -> AtomicDiscoveryAdmissionResult:
        """Verify idempotent replay or raise conflict error."""

        expected_discovery_id = reconstruction.plan.deterministic_discovery_id
        if existing.discovery_id != expected_discovery_id:
            raise DiscoveryAdmissionConflictError(
                f"Existing Discovery {existing.discovery_id} does not match expected "
                f"deterministic ID {expected_discovery_id} for Hypothesis."
            )

        claim = self._claim_repo.get_by_evaluation_id(
            reconstruction.evaluation_record.evaluation_id
        )
        if (
            claim is None
            or claim.state != DiscoveryAdmissionClaimState.COMMITTED
            or not self._claim_matches_reconstruction(claim, reconstruction)
            or claim.discovery_id != existing.discovery_id
            or claim.discovery_fingerprint
            != self._discovery_fingerprint(record_to_schema(Discovery, existing))
            or claim.session_frame_id is None
            or claim.session_frame_fingerprint is None
            or claim.committed_at is None
        ):
            raise DiscoveryAdmissionConflictError(
                "Committed admission claim does not prove the exact Discovery chain."
            )

        expected_discovery = Discovery(
            discovery_id=expected_discovery_id,
            hypothesis_id=reconstruction.hypothesis.hypothesis_id,
            evidence_ids=list(reconstruction.proposal.evidence_ids),
            claim=reconstruction.proposal.claim,
            epistemic_status=reconstruction.proposal.epistemic_status,
            analysis_intent=reconstruction.hypothesis.analysis_intent,
            uncertainty=reconstruction.proposal.validity_basis.uncertainty,
            scope=reconstruction.proposal.scope,
            validity_basis=reconstruction.proposal.validity_basis,
            limitations=list(reconstruction.proposal.limitations),
            invalidators=list(reconstruction.proposal.validity_basis.invalidators),
            lifecycle_state=existing.lifecycle_state,
            review_reasons=list(existing.review_reasons),
            flagged_by_evidence_ids=[UUID(item) for item in existing.flagged_by_evidence_ids],
            created_at=existing.created_at,
        )
        if self._discovery_fingerprint(expected_discovery) != claim.discovery_fingerprint:
            raise DiscoveryAdmissionConflictError(
                "Existing Discovery scientific content does not match the persisted proposal."
            )

        if (
            reconstruction.hypothesis.status != HypothesisStatus.EVALUATED
            or reconstruction.task.lifecycle_state != TaskLifecycleState.COMPLETED
            or reconstruction.evaluation_record.state != EvaluationControlState.COMMITTED
            or not reconstruction.decision_record.consumed
            or reconstruction.decision_record.consumed_by != str(expected_discovery_id)
            or reconstruction.decision_record.consumed_at != claim.committed_at
        ):
            raise DiscoveryAdmissionConflictError(
                "Partial or inconsistent lifecycle state for existing Discovery "
                f"{existing.discovery_id}."
            )

        session_frame = self._session.get(SessionFrameRecord, claim.session_frame_id)
        if (
            session_frame is None
            or str(existing.discovery_id) not in session_frame.relevant_discovery_refs
            or self._session_frame_fingerprint(record_to_schema(SessionFrame, session_frame))
            != claim.session_frame_fingerprint
        ):
            raise DiscoveryAdmissionConflictError(
                "Conclusion SessionFrame is missing or does not match the committed chain."
            )

        return AtomicDiscoveryAdmissionResult(
            disposition=DiscoveryAdmissionReplayDisposition.IDEMPOTENT,
            discovery_id=existing.discovery_id,
            evaluation_id=reconstruction.evaluation_record.evaluation_id,
            decision_id=reconstruction.decision_record.decision_id,
            hypothesis_id=reconstruction.hypothesis.hypothesis_id,
            task_id=reconstruction.task.task_id,
            session_frame_id=session_frame.session_frame_id,
            admission_fingerprint=reconstruction.plan.admission_fingerprint,
            committed_at=claim.committed_at,
        )

    def _load_and_verify_live_claim(
        self,
        lease: DiscoveryAdmissionLease,
    ) -> DiscoveryAdmissionClaimRecord:
        self._session.expire_all()
        claim = self._claim_repo.get_by_id(lease.claim_id)
        now = utc_now()
        if (
            claim is None
            or claim.evaluation_id != lease.evaluation_id
            or claim.decision_id != lease.decision_id
            or claim.state != DiscoveryAdmissionClaimState.CLAIMED
            or claim.owner != lease.owner
            or claim.fencing_epoch != lease.fencing_epoch
            or claim.claim_token_digest != self._claim_token_digest(lease.claim_token)
            or claim.claim_expiry is None
            or self._as_utc(claim.claim_expiry) <= now
        ):
            raise DiscoveryAdmissionConflictError(
                "Admission lease is stale, expired, or does not own the current fence."
            )
        return claim

    @staticmethod
    def _claim_matches_reconstruction(
        claim: DiscoveryAdmissionClaimRecord,
        reconstruction: _AdmissionReconstruction,
    ) -> bool:
        return (
            claim.evaluation_id == reconstruction.evaluation_record.evaluation_id
            and claim.decision_id == reconstruction.decision_record.decision_id
            and claim.proposal_digest == reconstruction.proposal_digest
            and claim.bundle_digest == reconstruction.bundle.input_digest
            and claim.admission_fingerprint == reconstruction.plan.admission_fingerprint
        )

    def _invalidate_stale_claim(self, claim_id: UUID, reason: str) -> None:
        self._session.rollback()
        if not self._claim_repo.stage_invalidate(claim_id, reason=reason):
            self._session.rollback()
            return
        self._session.commit()

    @staticmethod
    def _claim_token_digest(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _discovery_fingerprint(discovery: Discovery) -> str:
        return canonical_sha256(
            discovery.model_dump(
                mode="json",
                exclude={
                    "created_at",
                    "lifecycle_state",
                    "review_reasons",
                    "flagged_by_evidence_ids",
                },
            )
        )

    @staticmethod
    def _session_frame_fingerprint(frame: SessionFrame) -> str:
        return canonical_sha256(
            frame.model_dump(
                mode="json",
                exclude={"created_at", "frame_status", "stale_context"},
            )
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _expect_one(result: object, label: str) -> None:
        if getattr(result, "rowcount", None) != 1:
            raise DiscoveryAdmissionConflictError(f"Admission lost its fence for {label}.")

    def _inject(self, stage: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(stage)

    def _require_clean_unit_of_work(self) -> None:
        if self._session.new or self._session.dirty or self._session.deleted:
            raise DiscoveryAdmissionError(
                "Atomic Discovery admission requires a clean unit of work and "
                "will not flush caller changes."
            )


class _AdmissionReconstruction(ImmutableCogniEDABaseModel):
    """Internal container for reconstructed admission authority state."""

    evaluation_record: EvaluationControlRecord
    decision_record: ProposalDecisionRecord
    authority_grant: GovernanceAuthorityRecord
    hypothesis: HypothesisRecord
    task: TaskRecord
    bundle: DiscoverySynthesisBundle
    proposal: DiscoveryProposal
    proposal_digest: NonEmptyStr
    plan: DiscoveryAdmissionPlan
