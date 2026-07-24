"""Stage-only validity-event storage and deterministic dependency traversal."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, select

from db.models import (
    AnalysisFrameRecord,
    DiscoveryAdmissionClaimRecord,
    DiscoveryRecord,
    EvaluationControlRecord,
    EvidenceRecord,
    ExecutionRunRecord,
    HypothesisRecord,
    ProposalDecisionRecord,
    SessionFrameRecord,
    TaskRecord,
    ValidityEventRecord,
)
from schemas.enums import ValiditySourceType


class ValidityDependencyError(ValueError):
    """Raised when durable lineage is incomplete or internally contradictory."""


class ValidityEventRepository:
    """Repository primitives used only by the application-owned atomic service."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def stage_event(self, record: ValidityEventRecord) -> ValidityEventRecord:
        """Stage an event without committing the caller's transaction."""

        self.session.add(record)
        return record

    def get_by_idempotency_key(self, idempotency_key: str) -> ValidityEventRecord | None:
        """Find a validity event by its caller-stable idempotency key."""

        return self.session.exec(
            select(ValidityEventRecord).where(
                ValidityEventRecord.idempotency_key == idempotency_key
            )
        ).first()

    def get_by_event_id(self, event_id: UUID) -> ValidityEventRecord | None:
        """Find a validity event by ID."""

        return self.session.get(ValidityEventRecord, event_id)

    def discover_dependents(
        self,
        source_type: ValiditySourceType,
        source_id: UUID,
    ) -> dict[str, dict[UUID, Any]]:
        """Traverse every durable downstream reference from repository state.

        JSON reference columns are inspected from complete SQL result sets rather
        than ORM relationships or caller-provided dependent IDs.
        """

        affected_profile_ids: set[UUID] = set()
        affected_frame_ids: set[UUID] = set()
        affected_run_ids: set[UUID] = set()
        affected_evidence: dict[UUID, EvidenceRecord] = {}
        affected_hypothesis_ids: set[UUID] = set()
        affected_task_ids: set[UUID] = set()

        if source_type == ValiditySourceType.DATA_PROFILE:
            affected_profile_ids.add(source_id)
            frames = self.session.exec(
                select(AnalysisFrameRecord).where(AnalysisFrameRecord.data_profile_id == source_id)
            ).all()
            affected_frame_ids.update(frame.analysis_frame_id for frame in frames)
            hypotheses = self.session.exec(
                select(HypothesisRecord).where(HypothesisRecord.profile_id == source_id)
            ).all()
            affected_hypothesis_ids.update(item.hypothesis_id for item in hypotheses)
            tasks = self.session.exec(
                select(TaskRecord).where(TaskRecord.profile_id == source_id)
            ).all()
            affected_task_ids.update(item.task_id for item in tasks)
        elif source_type == ValiditySourceType.ANALYSIS_FRAME:
            affected_frame_ids.add(source_id)
        elif source_type == ValiditySourceType.EXECUTION_RUN:
            affected_run_ids.add(source_id)
        elif source_type == ValiditySourceType.EVIDENCE:
            evidence = self.session.get(EvidenceRecord, source_id)
            if evidence is not None:
                affected_evidence[evidence.evidence_id] = evidence

        if affected_frame_ids:
            runs = self.session.exec(
                select(ExecutionRunRecord).where(
                    ExecutionRunRecord.analysis_frame_id.in_(sorted(affected_frame_ids))
                )
            ).all()
            affected_run_ids.update(run.execution_run_id for run in runs)

        if affected_run_ids:
            runs = self.session.exec(
                select(ExecutionRunRecord).where(
                    ExecutionRunRecord.execution_run_id.in_(sorted(affected_run_ids))
                )
            ).all()
            for run in runs:
                if run.hypothesis_id is not None:
                    affected_hypothesis_ids.add(run.hypothesis_id)
                if run.task_id is not None:
                    affected_task_ids.add(run.task_id)

        evidence_predicates = []
        if affected_profile_ids:
            evidence_predicates.append(EvidenceRecord.profile_id.in_(sorted(affected_profile_ids)))
        if affected_frame_ids:
            evidence_predicates.append(
                EvidenceRecord.analysis_frame_ref.in_(
                    [str(item) for item in sorted(affected_frame_ids)]
                )
            )
        if affected_run_ids:
            evidence_predicates.append(
                EvidenceRecord.execution_run_ref.in_(
                    [str(item) for item in sorted(affected_run_ids)]
                )
            )
        if evidence_predicates:
            for evidence in self.session.exec(
                select(EvidenceRecord).where(or_(*evidence_predicates))
            ).all():
                affected_evidence[evidence.evidence_id] = evidence

        for evidence in affected_evidence.values():
            affected_hypothesis_ids.add(evidence.hypothesis_id)

        evidence_refs = {str(item) for item in affected_evidence}
        affected_evaluations: dict[UUID, EvaluationControlRecord] = {}
        for control in self.session.exec(select(EvaluationControlRecord)).all():
            if (
                evidence_refs.intersection(control.evidence_ids or [])
                or control.hypothesis_id in affected_hypothesis_ids
            ):
                affected_evaluations[control.evaluation_id] = control
                affected_hypothesis_ids.add(control.hypothesis_id)

        affected_decisions: dict[UUID, ProposalDecisionRecord] = {}
        affected_admission_claims: dict[UUID, DiscoveryAdmissionClaimRecord] = {}
        if affected_evaluations:
            decisions = self.session.exec(
                select(ProposalDecisionRecord).where(
                    ProposalDecisionRecord.evaluation_id.in_(sorted(affected_evaluations))
                )
            ).all()
            affected_decisions.update((decision.decision_id, decision) for decision in decisions)
            claims = self.session.exec(
                select(DiscoveryAdmissionClaimRecord).where(
                    DiscoveryAdmissionClaimRecord.evaluation_id.in_(sorted(affected_evaluations))
                )
            ).all()
            affected_admission_claims.update((claim.claim_id, claim) for claim in claims)

        affected_discoveries: dict[UUID, DiscoveryRecord] = {}
        profile_refs = {str(item) for item in affected_profile_ids}
        frame_refs = {str(item) for item in affected_frame_ids}
        for discovery in self.session.exec(select(DiscoveryRecord)).all():
            validity_basis = discovery.validity_basis or {}
            discovery_profile_ref = validity_basis.get("data_profile_id")
            discovery_frame_refs = set(
                validity_basis.get("analysis_frame_refs")
                or validity_basis.get("analysis_frame_ids")
                or []
            )
            if (
                evidence_refs.intersection(discovery.evidence_ids or [])
                or discovery_profile_ref in profile_refs
                or discovery_frame_refs.intersection(frame_refs)
            ):
                affected_discoveries[discovery.discovery_id] = discovery
                affected_hypothesis_ids.add(discovery.hypothesis_id)

        affected_hypotheses: dict[UUID, HypothesisRecord] = {}
        for hypothesis_id in sorted(affected_hypothesis_ids):
            hypothesis = self.session.get(HypothesisRecord, hypothesis_id)
            if hypothesis is None:
                raise ValidityDependencyError(f"Dependent Hypothesis is missing: {hypothesis_id}.")
            affected_hypotheses[hypothesis_id] = hypothesis
            affected_task_ids.add(hypothesis.task_id)

        discovery_refs = {str(item) for item in affected_discoveries}
        for task in self.session.exec(select(TaskRecord)).all():
            if discovery_refs.intersection(task.motivated_by_discovery_ids or []):
                affected_task_ids.add(task.task_id)

        affected_tasks: dict[UUID, TaskRecord] = {}
        for task_id in sorted(affected_task_ids):
            task = self.session.get(TaskRecord, task_id)
            if task is None:
                raise ValidityDependencyError(f"Dependent Task is missing: {task_id}.")
            affected_tasks[task_id] = task

        self._validate_lineage_completeness(
            affected_evaluations,
            affected_discoveries,
        )

        affected_session_frames: dict[UUID, SessionFrameRecord] = {}
        hypothesis_refs = {str(item) for item in affected_hypotheses}
        task_refs = {str(item) for item in affected_tasks}
        for frame in self.session.exec(select(SessionFrameRecord)).all():
            if (
                profile_refs.intersection(frame.active_data_profile_refs or [])
                or evidence_refs.intersection(frame.supporting_evidence_refs or [])
                or discovery_refs.intersection(frame.relevant_discovery_refs or [])
                or hypothesis_refs.intersection(frame.active_hypothesis_refs or [])
                or task_refs.intersection(frame.active_task_refs or [])
                or evidence_refs.intersection(
                    self._summary_ids(frame.supporting_evidence, "evidence_id")
                )
                or discovery_refs.intersection(
                    self._summary_ids(frame.relevant_discoveries, "discovery_id")
                )
            ):
                affected_session_frames[frame.session_frame_id] = frame

        return {
            "evidence": affected_evidence,
            "evaluations": affected_evaluations,
            "admission_claims": affected_admission_claims,
            "decisions": affected_decisions,
            "discoveries": affected_discoveries,
            "hypotheses": affected_hypotheses,
            "tasks": affected_tasks,
            "session_frames": affected_session_frames,
        }

    @staticmethod
    def _summary_ids(summaries: list[dict[str, Any]], field: str) -> set[str]:
        return {
            str(value)
            for summary in summaries or []
            if isinstance(summary, dict) and (value := summary.get(field)) is not None
        }

    def _validate_lineage_completeness(
        self,
        evaluations: dict[UUID, EvaluationControlRecord],
        discoveries: dict[UUID, DiscoveryRecord],
    ) -> None:
        for control in evaluations.values():
            missing = {
                reference
                for reference in control.evidence_ids or []
                if self._load_evidence_reference(reference) is None
            }
            if missing:
                raise ValidityDependencyError(
                    f"Affected EvaluationControl references missing Evidence: {sorted(missing)}."
                )
        for discovery in discoveries.values():
            missing = {
                reference
                for reference in discovery.evidence_ids or []
                if self._load_evidence_reference(reference) is None
            }
            if missing:
                raise ValidityDependencyError(
                    f"Affected Discovery references missing Evidence: {sorted(missing)}."
                )

    def _load_evidence_reference(self, reference: str) -> EvidenceRecord | None:
        try:
            evidence_id = UUID(reference)
        except ValueError as exc:
            raise ValidityDependencyError(
                f"Durable Evidence reference is not a UUID: {reference!r}."
            ) from exc
        return self.session.get(EvidenceRecord, evidence_id)
