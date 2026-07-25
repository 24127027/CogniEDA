"""Atomic AnalysisFrame and Evidence admission transaction service."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from application.evidence.admission_plan import (
    EvidenceAdmissionPlan,
    EvidenceAdmissionReplayDisposition,
    classify_evidence_admission_replay,
    compute_analysis_frame_fingerprint,
    compute_evidence_fingerprint,
)
from schemas.evidence import AnalysisFrame, Evidence


def execute_evidence_admission_plan(
    session: Any,
    plan: EvidenceAdmissionPlan,
    test_hook: Callable[[str, Any], None] | None = None,
) -> bool:
    """Execute the atomic transaction for one validated EvidenceAdmissionPlan.

    Persists AnalysisFrameRecord, EvidenceRecord, transitions ExecutionRun to
    evidence_admitted, transitions Hypothesis to ready_for_evaluation, and consumes
    the pending inbox in one transaction.
    """
    from application.execution.transition_service import ExecutionAttemptTransitionService
    from db.models import AnalysisFrameRecord, EvidenceRecord, ExecutionRunRecord
    from repositories.evidence import AnalysisFrameRepository, EvidenceRepository

    session.expire_all()
    run = session.get(ExecutionRunRecord, plan.execution_run_id)
    if (
        run is None
        or run.status != plan.required_run_status
        or run.finalizer_owner_id != plan.finalization_owner
        or run.finalization_fencing_epoch != plan.finalization_fencing_epoch
        or run.attempt_version != plan.expected_attempt_version
    ):
        session.rollback()
        return False

    existing_frame = session.get(AnalysisFrameRecord, plan.analysis_frame_id)
    existing_evidence = session.get(EvidenceRecord, plan.evidence_id)
    attempt_evidence = session.exec(
        select(EvidenceRecord).where(
            EvidenceRecord.execution_run_ref == str(plan.execution_run_id)
        )
    ).all()
    artifact_identity_conflict = (
        run.analysis_frame_id not in {None, plan.analysis_frame_id}
        or len(attempt_evidence) > 1
        or (
            len(attempt_evidence) == 1
            and attempt_evidence[0].evidence_id != plan.evidence_id
        )
    )

    existing_frame_fp = (
        compute_analysis_frame_fingerprint(
            AnalysisFrame(
                analysis_frame_id=existing_frame.analysis_frame_id,
                data_profile_id=existing_frame.data_profile_id,
                frame_hash=existing_frame.frame_hash,
                frame_ref=existing_frame.frame_ref,
                column_refs=list(existing_frame.column_refs),
                row_filter_description=existing_frame.row_filter_description,
                created_at=existing_frame.created_at,
            )
        )
        if existing_frame
        else None
    )

    existing_evidence_fp = (
        _evidence_record_fingerprint(existing_evidence, plan) if existing_evidence else None
    )

    disposition = classify_evidence_admission_replay(
        plan,
        existing_analysis_frame_id=existing_frame.analysis_frame_id if existing_frame else None,
        existing_analysis_frame_fingerprint=existing_frame_fp,
        existing_evidence_id=existing_evidence.evidence_id if existing_evidence else None,
        existing_evidence_fingerprint=existing_evidence_fp,
    )
    if artifact_identity_conflict:
        disposition = EvidenceAdmissionReplayDisposition.CONFLICT

    if disposition == EvidenceAdmissionReplayDisposition.CONFLICT:
        transition_service = ExecutionAttemptTransitionService(session)
        if not transition_service.stage_quarantine_evidence_conflict(
            execution_run_id=plan.execution_run_id,
            finalizer_owner_id=plan.finalization_owner,
            finalization_fencing_epoch=plan.finalization_fencing_epoch,
            attempt_version=plan.expected_attempt_version,
            reason="evidence_admission_artifact_conflict",
        ) or not transition_service.stage_mark_authoritative_inbox_conflict(
            inbox_id=plan.inbox_id,
            execution_run_id=plan.execution_run_id,
            dispatch_idempotency_key=plan.dispatch_idempotency_key,
            result_digest=plan.inbox_result_digest,
        ):
            session.rollback()
            return False
        session.commit()
        return False

    transition_service = ExecutionAttemptTransitionService(session)
    try:
        if disposition == EvidenceAdmissionReplayDisposition.NEW:
            AnalysisFrameRepository(session)._stage_create_from_evidence_admission(
                plan.analysis_frame
            )
            session.flush()
            if test_hook:
                test_hook("after_analysis_frame", session)

            EvidenceRepository(
                session, strict_provenance_validation=True
            )._stage_create_from_evidence_admission(plan.evidence)
            session.flush()
            if test_hook:
                test_hook("after_evidence", session)

        if not transition_service.stage_admit_evidence(
            execution_run_id=plan.execution_run_id,
            finalizer_owner_id=plan.finalization_owner,
            finalization_fencing_epoch=plan.finalization_fencing_epoch,
            attempt_version=plan.expected_attempt_version,
            analysis_frame_id=plan.analysis_frame_id,
        ):
            session.rollback()
            return False
        if test_hook:
            test_hook("after_run_transition", session)

        if not transition_service.stage_hypothesis_ready_for_evaluation(plan.hypothesis_id):
            session.rollback()
            return False
        if test_hook:
            test_hook("after_hypothesis_transition", session)

        if not transition_service.stage_consume_authoritative_inbox(
            inbox_id=plan.inbox_id,
            execution_run_id=plan.execution_run_id,
            dispatch_idempotency_key=plan.dispatch_idempotency_key,
            result_digest=plan.inbox_result_digest,
        ):
            session.rollback()
            return False
        if test_hook:
            test_hook("after_inbox_consumption", session)

        if test_hook:
            test_hook("before_commit", session)

        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        if _committed_admission_matches(session, plan):
            return True
        raise
    except Exception:
        session.rollback()
        raise


def _committed_admission_matches(session: Any, plan: EvidenceAdmissionPlan) -> bool:
    """Recognize a concurrent identical winner without using lookup as write authority."""

    from db.models import (
        AnalysisFrameRecord,
        EvidenceRecord,
        ExecutionInboxRecord,
        ExecutionRunRecord,
        HypothesisRecord,
    )
    from schemas.enums import ExecutionRunStatus, HypothesisStatus

    session.expire_all()
    run = session.get(ExecutionRunRecord, plan.execution_run_id)
    hypothesis = session.get(HypothesisRecord, plan.hypothesis_id)
    inbox = session.get(ExecutionInboxRecord, plan.inbox_id)
    frame = session.get(AnalysisFrameRecord, plan.analysis_frame_id)
    evidence = session.get(EvidenceRecord, plan.evidence_id)
    if (
        run is None
        or run.status != ExecutionRunStatus.EVIDENCE_ADMITTED
        or run.analysis_frame_id != plan.analysis_frame_id
        or hypothesis is None
        or hypothesis.status != HypothesisStatus.READY_FOR_EVALUATION
        or inbox is None
        or inbox.status != "processed"
        or frame is None
        or evidence is None
    ):
        return False
    return (
        compute_analysis_frame_fingerprint(
            AnalysisFrame(
                analysis_frame_id=frame.analysis_frame_id,
                data_profile_id=frame.data_profile_id,
                frame_hash=frame.frame_hash,
                frame_ref=frame.frame_ref,
                column_refs=list(frame.column_refs),
                row_filter_description=frame.row_filter_description,
                created_at=frame.created_at,
            )
        )
        == plan.analysis_frame_fingerprint
        and _evidence_record_fingerprint(evidence, plan) == plan.evidence_fingerprint
    )


def _evidence_record_fingerprint(record: Any, plan: EvidenceAdmissionPlan) -> str:
    """Reconstruct the immutable Evidence schema from one persisted record."""

    from schemas.common import EvidenceProvenance, MethodParameter

    stored_provenance = record.provenance
    provenance = (
        EvidenceProvenance.model_validate(stored_provenance)
        if isinstance(stored_provenance, dict)
        else EvidenceProvenance(
            analysis_frame_ref=str(record.analysis_frame_ref),
            execution_run_ref=str(record.execution_run_ref),
            code_reference="",
            environment_reference="",
        )
    )
    stored_summary = record.result_summary
    result_summary = (
        stored_summary
        if hasattr(stored_summary, "statistical_metrics")
        else type(plan.evidence.result_summary).model_validate(stored_summary)
    )
    evidence = Evidence(
        evidence_id=record.evidence_id,
        hypothesis_id=record.hypothesis_id,
        profile_id=record.profile_id,
        analysis_frame_ref=str(record.analysis_frame_ref),
        execution_run_ref=str(record.execution_run_ref),
        evidence_type=record.evidence_type,
        method=record.method,
        parameters=[
            parameter
            if hasattr(parameter, "name")
            else MethodParameter.model_validate(parameter)
            for parameter in record.parameters
        ],
        provenance=provenance,
        result_summary=result_summary,
        artifact_refs=list(record.artifact_refs),
        limitations=list(record.limitations),
        created_at=record.created_at,
    )
    return compute_evidence_fingerprint(evidence)
