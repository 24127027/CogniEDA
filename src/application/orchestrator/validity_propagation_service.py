"""Atomic, authority-verified propagation of persisted source validity events."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid5

from sqlalchemy import update
from sqlmodel import Session

from application.orchestrator.discovery_admission_governance import (
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
    SessionFrameRecord,
    TaskRecord,
    ValidityEventRecord,
)
from repositories.validity_event_repository import ValidityEventRepository
from schemas.canonical import canonical_sha256
from schemas.enums import (
    AuthorizationClass,
    DataProfileLifecycleState,
    DiscoveryAdmissionClaimState,
    DiscoveryLifecycleState,
    EvaluationControlState,
    EvidenceLifecycleState,
    ExecutionRunStatus,
    HypothesisStatus,
    SessionFrameStatus,
    ValidityEventType,
    ValiditySourceState,
    ValiditySourceType,
)
from schemas.validity_propagation_contracts import (
    ValidityPropagationCommand,
    ValidityPropagationPlan,
    ValidityPropagationResult,
    ValidityTargetTransition,
)

_VALIDITY_EVENT_NAMESPACE = UUID("2aa2d86d-197b-5a73-b938-f2ac79e11057")
_ALLOWED_TRUSTED_PRODUCERS = {
    "system_integrity",
    "validity_propagation_service",
    "admission_service",
    "receiver_service",
}
_EVENT_AUTHORITY = {
    ValidityEventType.EVIDENCE_INVALIDATION: (
        "integrity_invalidation",
        "invalidate_source",
    ),
    ValidityEventType.EVIDENCE_SUPERSESSION: (
        "supersession_propagation",
        "supersede_source",
    ),
    ValidityEventType.EVIDENCE_CONFLICT: (
        "conflict_quarantine",
        "quarantine_source",
    ),
    ValidityEventType.DATA_PROFILE_INVALIDATION: (
        "integrity_invalidation",
        "invalidate_source",
    ),
    ValidityEventType.DATA_PROFILE_SUPERSESSION: (
        "supersession_propagation",
        "supersede_source",
    ),
    ValidityEventType.ANALYSIS_FRAME_INVALIDITY: (
        "integrity_invalidation",
        "invalidate_source",
    ),
    ValidityEventType.EXECUTION_RUN_CONFLICT: (
        "conflict_quarantine",
        "quarantine_source",
    ),
    ValidityEventType.PROVENANCE_CORRUPTION: (
        "integrity_invalidation",
        "invalidate_source",
    ),
}
_EVENT_SOURCE_ALLOWLIST = {
    ValidityEventType.EVIDENCE_INVALIDATION: {ValiditySourceType.EVIDENCE},
    ValidityEventType.EVIDENCE_SUPERSESSION: {ValiditySourceType.EVIDENCE},
    ValidityEventType.EVIDENCE_CONFLICT: {ValiditySourceType.EVIDENCE},
    ValidityEventType.DATA_PROFILE_INVALIDATION: {ValiditySourceType.DATA_PROFILE},
    ValidityEventType.DATA_PROFILE_SUPERSESSION: {ValiditySourceType.DATA_PROFILE},
    ValidityEventType.ANALYSIS_FRAME_INVALIDITY: {ValiditySourceType.ANALYSIS_FRAME},
    ValidityEventType.EXECUTION_RUN_CONFLICT: {ValiditySourceType.EXECUTION_RUN},
    ValidityEventType.PROVENANCE_CORRUPTION: set(ValiditySourceType),
}
_ACTIVE_EVALUATION_STATES = {
    EvaluationControlState.PENDING,
    EvaluationControlState.CLAIMED,
    EvaluationControlState.PROPOSAL_READY,
    EvaluationControlState.RETRYABLE_FAILED,
    EvaluationControlState.COMMITTED,
}


def validity_authority_scope(
    *,
    event_type: ValidityEventType,
    source_type: ValiditySourceType,
    source_id: UUID,
    replacement_id: UUID | None = None,
) -> tuple[str, str]:
    """Return the exact durable capability scope for one source event."""

    purpose, operation = _EVENT_AUTHORITY[event_type]
    source_scope = f"{source_type.value}:{source_id}"
    if replacement_id is not None:
        source_scope = f"{source_scope}:{replacement_id}"
    return purpose, f"{operation}:{source_scope}"


class StaleValidityPropagationError(RuntimeError):
    """Raised when a source or dependent loses an expected-state fence."""


class PartialValidityPropagationError(RuntimeError):
    """Raised when an event exists without proof of its complete committed effects."""


class AtomicValidityPropagationService:
    """Own the one transaction allowed to propagate supported validity events."""

    def __init__(
        self,
        session: Session,
        *,
        failure_injector: Callable[[str], None] | None = None,
    ) -> None:
        self.session = session
        self.repo = ValidityEventRepository(session)
        self._failure_injector = failure_injector

    def load_source_guard(
        self,
        source_type: ValiditySourceType,
        source_id: UUID,
    ) -> tuple[str, str]:
        """Return the current state and server-computed immutable-core fingerprint."""

        self._require_clean_unit_of_work()
        record = self._load_source(source_type, source_id)
        return self._source_state(source_type, record), self._source_fingerprint(
            source_type,
            record,
        )

    def plan_propagation(self, command: ValidityPropagationCommand) -> ValidityPropagationPlan:
        """Build a detached plan; the plan itself is never write authority."""

        self._require_clean_unit_of_work()
        authority = self._verify_authority(command, require_active=True)
        plan, _ = self._build_plan(command, authority)
        return plan

    def execute_propagation(
        self,
        command: ValidityPropagationCommand,
    ) -> ValidityPropagationResult:
        """Execute every applicable transition and the event in one commit."""

        self._require_clean_unit_of_work()
        existing = self.repo.get_by_idempotency_key(command.idempotency_key)
        authority = self._verify_authority(
            command,
            require_active=existing is None,
        )
        request_fingerprint = command.derive_request_fingerprint(
            authority_identity=authority.actor_identity,
            authority_class=authority.authority_class,
            authority_purpose=authority.purpose,
            authority_operation=authority.operation_type,
        )
        if existing is not None:
            return self._replay_existing(existing, request_fingerprint)

        plan, dependencies = self._build_plan(command, authority)
        try:
            self._apply_plan(plan, command, dependencies)
            event = ValidityEventRecord(
                event_id=plan.event_id,
                source_type=plan.source_type,
                source_id=plan.source_id,
                source_fingerprint=plan.source_fingerprint,
                event_type=plan.event_type,
                reason=plan.reason,
                authority_id=plan.authority_id,
                authority_identity=plan.authority_identity,
                authority_class=plan.authority_class,
                workspace_id=plan.workspace_id,
                session_id=plan.session_id,
                replacement_id=plan.replacement_id,
                replacement_fingerprint=plan.replacement_fingerprint,
                expected_source_state=plan.expected_source_state,
                source_post_state=plan.source_post_state,
                idempotency_key=plan.idempotency_key,
                event_fingerprint=plan.request_fingerprint,
                plan_fingerprint=plan.plan_fingerprint,
                affected_targets=[
                    transition.model_dump(mode="json") for transition in plan.transitions
                ],
                processing_state="COMMITTED",
            )
            self.repo.stage_event(event)
            self.session.flush()
            self._inject("validity_event")
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            winner = self.repo.get_by_idempotency_key(command.idempotency_key)
            if winner is not None and winner.event_fingerprint == request_fingerprint:
                return self._replay_existing(winner, request_fingerprint)
            raise exc

        return self._result_from_event(event, replayed=False)

    def _build_plan(
        self,
        command: ValidityPropagationCommand,
        authority: GovernanceAuthorityRecord,
    ) -> tuple[ValidityPropagationPlan, dict[str, dict[UUID, object]]]:
        self._validate_event_source_pair(command)
        source = self._load_source(command.source_type, command.source_id)
        source_state = self._source_state(command.source_type, source)
        source_fingerprint = self._source_fingerprint(command.source_type, source)
        if source_state != command.expected_source_state:
            raise StaleValidityPropagationError(
                f"Source state changed: expected {command.expected_source_state!r}, "
                f"got {source_state!r}."
            )
        if source_fingerprint != command.expected_source_fingerprint:
            raise StaleValidityPropagationError("Source immutable-core fingerprint changed.")
        self._validate_source_is_eligible(command, source)

        replacement_fingerprint = self._validate_replacement(command, source)
        dependencies = self.repo.discover_dependents(command.source_type, command.source_id)
        source_post_state = self._source_post_state(command)
        request_fingerprint = command.derive_request_fingerprint(
            authority_identity=authority.actor_identity,
            authority_class=authority.authority_class,
            authority_purpose=authority.purpose,
            authority_operation=authority.operation_type,
        )
        event_id = uuid5(
            _VALIDITY_EVENT_NAMESPACE,
            f"{command.idempotency_key}:{request_fingerprint}",
        )
        transitions = self._build_transitions(
            command,
            source,
            source_state,
            source_fingerprint,
            source_post_state,
            dependencies,
        )
        plan = ValidityPropagationPlan(
            event_id=event_id,
            idempotency_key=command.idempotency_key,
            request_fingerprint=request_fingerprint,
            source_type=command.source_type,
            source_id=command.source_id,
            source_fingerprint=source_fingerprint,
            expected_source_state=source_state,
            source_post_state=source_post_state,
            event_type=command.event_type,
            reason=command.reason,
            authority_id=authority.authority_id,
            authority_identity=authority.actor_identity,
            authority_class=authority.authority_class,
            authority_purpose=authority.purpose,
            authority_operation=authority.operation_type,
            workspace_id=command.workspace_id,
            session_id=command.session_id,
            replacement_id=command.replacement_id,
            replacement_fingerprint=replacement_fingerprint,
            transitions=transitions,
        )
        return plan.model_copy(update={"plan_fingerprint": plan.derive_fingerprint()}), dependencies

    def _build_transitions(
        self,
        command: ValidityPropagationCommand,
        source: object,
        source_state: str,
        source_fingerprint: str,
        source_post_state: str,
        dependencies: dict[str, dict[UUID, object]],
    ) -> tuple[ValidityTargetTransition, ...]:
        transitions = [
            ValidityTargetTransition(
                target_type="source",
                target_id=command.source_id,
                expected_state=source_state,
                target_state=source_post_state,
                expected_fingerprint=source_fingerprint,
            )
        ]

        for evidence_id, evidence in sorted(dependencies["evidence"].items()):
            if (
                command.source_type == ValiditySourceType.EVIDENCE
                and evidence_id == command.source_id
            ):
                continue
            if evidence.lifecycle_state in {
                EvidenceLifecycleState.SUPERSEDED,
                EvidenceLifecycleState.INVALIDATED,
            }:
                continue
            transitions.append(
                self._transition(
                    "evidence",
                    evidence_id,
                    evidence.lifecycle_state.value,
                    EvidenceLifecycleState.INVALIDATED.value,
                    evidence,
                )
            )

        for evaluation_id, control in sorted(dependencies["evaluations"].items()):
            if control.state not in _ACTIVE_EVALUATION_STATES:
                continue
            transitions.append(
                self._transition(
                    "evaluation",
                    evaluation_id,
                    control.state.value,
                    EvaluationControlState.INVALIDATED.value,
                    control,
                )
            )

        for claim_id, claim in sorted(dependencies["admission_claims"].items()):
            if claim.state not in {
                DiscoveryAdmissionClaimState.PENDING,
                DiscoveryAdmissionClaimState.CLAIMED,
            }:
                continue
            transitions.append(
                self._transition(
                    "admission_claim",
                    claim_id,
                    claim.state.value,
                    DiscoveryAdmissionClaimState.INVALIDATED.value,
                    claim,
                )
            )

        for discovery_id, discovery in sorted(dependencies["discoveries"].items()):
            if discovery.lifecycle_state == DiscoveryLifecycleState.DEPRECATED:
                continue
            transitions.append(
                self._transition(
                    "discovery",
                    discovery_id,
                    discovery.lifecycle_state.value,
                    DiscoveryLifecycleState.INVALIDATED.value,
                    discovery,
                )
            )

        discovery_hypotheses = {item.hypothesis_id for item in dependencies["discoveries"].values()}
        for hypothesis_id, hypothesis in sorted(dependencies["hypotheses"].items()):
            target = hypothesis.status
            if (
                hypothesis.status == HypothesisStatus.READY_FOR_EVALUATION
                and hypothesis_id not in discovery_hypotheses
            ):
                target = HypothesisStatus.AWAITING_ADDITIONAL_EVIDENCE
            transitions.append(
                self._transition(
                    "hypothesis",
                    hypothesis_id,
                    hypothesis.status.value,
                    target.value,
                    hypothesis,
                )
            )

        for task_id, task in sorted(dependencies["tasks"].items()):
            transitions.append(
                self._transition(
                    "task",
                    task_id,
                    task.lifecycle_state.value,
                    task.lifecycle_state.value,
                    task,
                )
            )

        for frame_id, frame in sorted(dependencies["session_frames"].items()):
            if frame.frame_status == SessionFrameStatus.ARCHIVED:
                continue
            transitions.append(
                self._transition(
                    "session_frame",
                    frame_id,
                    frame.frame_status.value,
                    SessionFrameStatus.SUPERSEDED.value,
                    frame,
                )
            )
        return tuple(transitions)

    @staticmethod
    def _transition(
        target_type: str,
        target_id: UUID,
        expected_state: str,
        target_state: str,
        record: object,
    ) -> ValidityTargetTransition:
        return ValidityTargetTransition(
            target_type=target_type,  # type: ignore[arg-type]
            target_id=target_id,
            expected_state=expected_state,
            target_state=target_state,
            expected_fingerprint=AtomicValidityPropagationService._mutable_fingerprint(
                target_type,
                record,
            ),
        )

    def _apply_plan(
        self,
        plan: ValidityPropagationPlan,
        command: ValidityPropagationCommand,
        dependencies: dict[str, dict[UUID, object]],
    ) -> None:
        note = self._event_note(plan)
        for transition in plan.transitions:
            if transition.target_type == "source":
                self._apply_source_transition(plan, command, transition, note)
            elif transition.target_type == "evidence":
                evidence = dependencies["evidence"][transition.target_id]
                self._cas_evidence(evidence, transition, note)
            elif transition.target_type == "evaluation":
                control = dependencies["evaluations"][transition.target_id]
                self._cas_evaluation(control, transition, note)
            elif transition.target_type == "admission_claim":
                claim = dependencies["admission_claims"][transition.target_id]
                self._cas_admission_claim(claim, transition, note)
            elif transition.target_type == "discovery":
                discovery = dependencies["discoveries"][transition.target_id]
                self._cas_discovery(
                    discovery,
                    transition,
                    note,
                    affected_evidence_ids=tuple(dependencies["evidence"]),
                )
            elif transition.target_type == "hypothesis":
                hypothesis = dependencies["hypotheses"][transition.target_id]
                self._cas_hypothesis(hypothesis, transition, note)
            elif transition.target_type == "task":
                task = dependencies["tasks"][transition.target_id]
                self._cas_task(task, transition, note)
            elif transition.target_type == "session_frame":
                frame = dependencies["session_frames"][transition.target_id]
                self._cas_session_frame(frame, transition, plan, note)
            self._inject(f"{transition.target_type}:{transition.target_id}")

    def _apply_source_transition(
        self,
        plan: ValidityPropagationPlan,
        command: ValidityPropagationCommand,
        transition: ValidityTargetTransition,
        note: str,
    ) -> None:
        if command.source_type == ValiditySourceType.DATA_PROFILE:
            target = DataProfileLifecycleState(transition.target_state)
            result = self.session.exec(
                update(DataProfileRecord)
                .where(DataProfileRecord.profile_id == command.source_id)
                .where(
                    DataProfileRecord.lifecycle_state
                    == DataProfileLifecycleState(transition.expected_state)
                )
                .values(
                    lifecycle_state=target,
                    superseded_by_data_profile_id=command.replacement_id,
                    lifecycle_reason=note,
                )
            )
        elif command.source_type == ValiditySourceType.EVIDENCE:
            target = EvidenceLifecycleState(transition.target_state)
            result = self.session.exec(
                update(EvidenceRecord)
                .where(EvidenceRecord.evidence_id == command.source_id)
                .where(
                    EvidenceRecord.lifecycle_state
                    == EvidenceLifecycleState(transition.expected_state)
                )
                .values(
                    lifecycle_state=target,
                    superseded_by_evidence_id=command.replacement_id,
                    lifecycle_reason=note,
                )
            )
        elif command.source_type == ValiditySourceType.ANALYSIS_FRAME:
            result = self.session.exec(
                update(AnalysisFrameRecord)
                .where(AnalysisFrameRecord.analysis_frame_id == command.source_id)
                .where(
                    AnalysisFrameRecord.validity_state
                    == ValiditySourceState(transition.expected_state)
                )
                .values(
                    validity_state=ValiditySourceState(transition.target_state),
                    validity_reason=note,
                )
            )
        else:
            result = self.session.exec(
                update(ExecutionRunRecord)
                .where(ExecutionRunRecord.execution_run_id == command.source_id)
                .where(
                    ExecutionRunRecord.validity_state
                    == ValiditySourceState(transition.expected_state)
                )
                .values(
                    validity_state=ValiditySourceState(transition.target_state),
                    validity_reason=note,
                )
            )
        self._expect_one(result, f"source {plan.source_type.value}:{plan.source_id}")

    def _cas_evidence(
        self,
        evidence: EvidenceRecord,
        transition: ValidityTargetTransition,
        note: str,
    ) -> None:
        result = self.session.exec(
            update(EvidenceRecord)
            .where(EvidenceRecord.evidence_id == evidence.evidence_id)
            .where(EvidenceRecord.lifecycle_state == evidence.lifecycle_state)
            .where(EvidenceRecord.lifecycle_reason == evidence.lifecycle_reason)
            .values(
                lifecycle_state=EvidenceLifecycleState(transition.target_state),
                superseded_by_evidence_id=None,
                lifecycle_reason=note,
            )
        )
        self._expect_one(result, f"Evidence {evidence.evidence_id}")

    def _cas_evaluation(
        self,
        control: EvaluationControlRecord,
        transition: ValidityTargetTransition,
        note: str,
    ) -> None:
        result = self.session.exec(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == control.evaluation_id)
            .where(EvaluationControlRecord.state == control.state)
            .where(EvaluationControlRecord.invalidation_reason == control.invalidation_reason)
            .values(
                state=EvaluationControlState(transition.target_state),
                invalidation_reason=note,
                updated_at=datetime.now(UTC),
            )
        )
        self._expect_one(result, f"EvaluationControl {control.evaluation_id}")

    def _cas_admission_claim(
        self,
        claim: DiscoveryAdmissionClaimRecord,
        transition: ValidityTargetTransition,
        note: str,
    ) -> None:
        result = self.session.exec(
            update(DiscoveryAdmissionClaimRecord)
            .where(DiscoveryAdmissionClaimRecord.claim_id == claim.claim_id)
            .where(DiscoveryAdmissionClaimRecord.state == claim.state)
            .where(DiscoveryAdmissionClaimRecord.fencing_epoch == claim.fencing_epoch)
            .values(
                state=DiscoveryAdmissionClaimState(transition.target_state),
                invalidation_reason=note,
                updated_at=datetime.now(UTC),
            )
        )
        self._expect_one(result, f"DiscoveryAdmissionClaim {claim.claim_id}")

    def _cas_discovery(
        self,
        discovery: DiscoveryRecord,
        transition: ValidityTargetTransition,
        note: str,
        *,
        affected_evidence_ids: tuple[UUID, ...],
    ) -> None:
        reasons = list(discovery.review_reasons or [])
        if note not in reasons:
            reasons.append(note)
        flagged = list(discovery.flagged_by_evidence_ids or [])
        for evidence_id in sorted(affected_evidence_ids):
            evidence_ref = str(evidence_id)
            if evidence_ref in discovery.evidence_ids and evidence_ref not in flagged:
                flagged.append(evidence_ref)
        result = self.session.exec(
            update(DiscoveryRecord)
            .where(DiscoveryRecord.discovery_id == discovery.discovery_id)
            .where(DiscoveryRecord.lifecycle_state == discovery.lifecycle_state)
            .where(DiscoveryRecord.review_reasons == discovery.review_reasons)
            .where(DiscoveryRecord.flagged_by_evidence_ids == discovery.flagged_by_evidence_ids)
            .values(
                lifecycle_state=DiscoveryLifecycleState(transition.target_state),
                review_reasons=reasons,
                flagged_by_evidence_ids=flagged,
            )
        )
        self._expect_one(result, f"Discovery {discovery.discovery_id}")

    def _cas_hypothesis(
        self,
        hypothesis: HypothesisRecord,
        transition: ValidityTargetTransition,
        note: str,
    ) -> None:
        reasons = list(hypothesis.review_reasons or [])
        if note not in reasons:
            reasons.append(note)
        result = self.session.exec(
            update(HypothesisRecord)
            .where(HypothesisRecord.hypothesis_id == hypothesis.hypothesis_id)
            .where(HypothesisRecord.status == hypothesis.status)
            .where(HypothesisRecord.review_reasons == hypothesis.review_reasons)
            .values(
                status=HypothesisStatus(transition.target_state),
                review_reasons=reasons,
                updated_at=datetime.now(UTC),
            )
        )
        self._expect_one(result, f"Hypothesis {hypothesis.hypothesis_id}")

    def _cas_task(
        self,
        task: TaskRecord,
        transition: ValidityTargetTransition,
        note: str,
    ) -> None:
        reasons = list(task.review_reasons or [])
        if note not in reasons:
            reasons.append(note)
        result = self.session.exec(
            update(TaskRecord)
            .where(TaskRecord.task_id == task.task_id)
            .where(TaskRecord.lifecycle_state == task.lifecycle_state)
            .where(TaskRecord.review_reasons == task.review_reasons)
            .values(
                review_reasons=reasons,
                updated_at=datetime.now(UTC),
            )
        )
        self._expect_one(result, f"Task {task.task_id}")

    def _cas_session_frame(
        self,
        frame: SessionFrameRecord,
        transition: ValidityTargetTransition,
        plan: ValidityPropagationPlan,
        note: str,
    ) -> None:
        stale = list(frame.stale_context or [])
        stale.append(
            {
                "artifact_type": f"validity_event:{plan.event_id}",
                "ref_id": str(plan.source_id),
                "replacement_ref_id": (
                    str(plan.replacement_id) if plan.replacement_id is not None else None
                ),
                "reason": note,
            }
        )
        result = self.session.exec(
            update(SessionFrameRecord)
            .where(SessionFrameRecord.session_frame_id == frame.session_frame_id)
            .where(SessionFrameRecord.frame_status == frame.frame_status)
            .where(SessionFrameRecord.stale_context == frame.stale_context)
            .values(
                frame_status=SessionFrameStatus(transition.target_state),
                stale_context=stale,
            )
        )
        self._expect_one(result, f"SessionFrame {frame.session_frame_id}")

    def _verify_authority(
        self,
        command: ValidityPropagationCommand,
        *,
        require_active: bool,
    ) -> GovernanceAuthorityRecord:
        authority = self.session.get(GovernanceAuthorityRecord, command.authority_id)
        if authority is None:
            raise PermissionError(f"Validity authority grant not found: {command.authority_id}.")
        expected_fingerprint = compute_governance_authority_fingerprint(
            authority_id=authority.authority_id,
            actor_identity=authority.actor_identity,
            authority_class=authority.authority_class,
            workspace_id=authority.workspace_id,
            session_id=authority.session_id,
            purpose=authority.purpose,
            operation_type=authority.operation_type,
            issued_by=authority.issued_by,
            issued_at=authority.issued_at,
            expires_at=authority.expires_at,
        )
        if authority.authority_fingerprint != expected_fingerprint:
            raise PermissionError("Validity authority fingerprint is invalid.")
        if require_active and (
            not authority.active
            or (authority.expires_at is not None and self._is_expired(authority.expires_at))
        ):
            raise PermissionError("Validity authority grant is inactive or expired.")
        if authority.authority_class == AuthorizationClass.UNAUTHORIZED:
            raise PermissionError("Unauthorized authority class cannot propagate validity.")
        if authority.workspace_id != command.workspace_id:
            raise PermissionError("Validity authority workspace mismatch.")
        if authority.authority_class == AuthorizationClass.USER_GOVERNED:
            if (
                authority.session_id is None
                or command.session_id is None
                or authority.session_id != command.session_id
            ):
                raise PermissionError("User-governed validity authority requires exact session.")
        elif authority.authority_class == AuthorizationClass.TRUSTED_INTERNAL:
            if authority.actor_identity not in _ALLOWED_TRUSTED_PRODUCERS:
                raise PermissionError("Trusted validity producer is not allow-listed.")
            if command.session_id != authority.session_id:
                raise PermissionError("Trusted validity authority session mismatch.")
        expected_pair = validity_authority_scope(
            event_type=command.event_type,
            source_type=command.source_type,
            source_id=command.source_id,
            replacement_id=command.replacement_id,
        )
        if (authority.purpose, authority.operation_type) != expected_pair:
            raise PermissionError(
                "Validity authority purpose/operation does not authorize this event type."
            )
        return authority

    @staticmethod
    def _validate_event_source_pair(command: ValidityPropagationCommand) -> None:
        if command.source_type not in _EVENT_SOURCE_ALLOWLIST[command.event_type]:
            raise ValueError(
                f"{command.event_type.value} is not allowed for {command.source_type.value}."
            )

    def _validate_source_is_eligible(
        self,
        command: ValidityPropagationCommand,
        source: object,
    ) -> None:
        state = self._source_state(command.source_type, source)
        if state != "active":
            raise StaleValidityPropagationError(f"Validity source must be active, got {state!r}.")
        if (
            command.source_type == ValiditySourceType.EXECUTION_RUN
            and source.status != ExecutionRunStatus.EVIDENCE_ADMITTED
        ):
            raise ValueError(
                "ExecutionRun validity conflict is supported only after Evidence admission."
            )

    def _validate_replacement(
        self,
        command: ValidityPropagationCommand,
        source: object,
    ) -> str | None:
        if command.replacement_id is None:
            return None
        replacement = self._load_source(command.source_type, command.replacement_id)
        replacement_state = self._source_state(command.source_type, replacement)
        replacement_fingerprint = self._source_fingerprint(
            command.source_type,
            replacement,
        )
        if replacement_state != "active":
            raise ValueError("Replacement validity source must be active.")
        if replacement_fingerprint != command.expected_replacement_fingerprint:
            raise StaleValidityPropagationError("Replacement source fingerprint changed.")
        if command.source_type == ValiditySourceType.EVIDENCE and (
            replacement.hypothesis_id != source.hypothesis_id
            or replacement.profile_id != source.profile_id
        ):
            raise ValueError(
                "Replacement Evidence must preserve Hypothesis and DataProfile lineage."
            )
        if command.source_type == ValiditySourceType.DATA_PROFILE and (
            replacement.dataset_path != source.dataset_path
        ):
            raise ValueError("Replacement DataProfile must describe the same dataset path.")
        return replacement_fingerprint

    def _load_source(self, source_type: ValiditySourceType, source_id: UUID) -> object:
        model = {
            ValiditySourceType.DATA_PROFILE: DataProfileRecord,
            ValiditySourceType.EVIDENCE: EvidenceRecord,
            ValiditySourceType.ANALYSIS_FRAME: AnalysisFrameRecord,
            ValiditySourceType.EXECUTION_RUN: ExecutionRunRecord,
        }[source_type]
        record = self.session.get(model, source_id)
        if record is None:
            raise ValueError(f"Validity source not found: {source_type.value}:{source_id}.")
        return record

    @staticmethod
    def _source_state(source_type: ValiditySourceType, record: object) -> str:
        if source_type == ValiditySourceType.DATA_PROFILE:
            return record.lifecycle_state.value
        if source_type == ValiditySourceType.EVIDENCE:
            return record.lifecycle_state.value
        return record.validity_state.value

    @staticmethod
    def _source_post_state(command: ValidityPropagationCommand) -> str:
        if command.event_type == ValidityEventType.DATA_PROFILE_SUPERSESSION:
            return DataProfileLifecycleState.SUPERSEDED.value
        if command.source_type == ValiditySourceType.DATA_PROFILE:
            return DataProfileLifecycleState.INVALIDATED.value
        if command.event_type == ValidityEventType.EVIDENCE_SUPERSESSION:
            return EvidenceLifecycleState.SUPERSEDED.value
        if command.source_type == ValiditySourceType.EVIDENCE:
            return EvidenceLifecycleState.INVALIDATED.value
        if command.source_type == ValiditySourceType.EXECUTION_RUN:
            return ValiditySourceState.CONFLICT.value
        return ValiditySourceState.INVALIDATED.value

    @staticmethod
    def _source_fingerprint(source_type: ValiditySourceType, record: object) -> str:
        excluded = {
            ValiditySourceType.DATA_PROFILE: {
                "created_at",
                "lifecycle_state",
                "superseded_by_data_profile_id",
                "lifecycle_reason",
            },
            ValiditySourceType.EVIDENCE: {
                "created_at",
                "lifecycle_state",
                "superseded_by_evidence_id",
                "lifecycle_reason",
            },
            ValiditySourceType.ANALYSIS_FRAME: {
                "created_at",
                "validity_state",
                "validity_reason",
            },
            ValiditySourceType.EXECUTION_RUN: {
                "created_at",
                "validity_state",
                "validity_reason",
                "worker_id",
                "lease_epoch",
                "lease_acquired_at",
                "lease_expires_at",
                "finalizer_owner_id",
                "finalization_fencing_epoch",
                "finalization_claimed_at",
                "finalization_expires_at",
                "recovery_status",
            },
        }[source_type]
        return canonical_sha256(record.model_dump(mode="python", exclude=excluded))

    @staticmethod
    def _mutable_fingerprint(target_type: str, record: object) -> str:
        fields = {
            "evidence": (
                "lifecycle_state",
                "superseded_by_evidence_id",
                "lifecycle_reason",
            ),
            "evaluation": (
                "state",
                "invalidation_reason",
                "owner",
                "fencing_epoch",
            ),
            "admission_claim": (
                "state",
                "invalidation_reason",
                "owner",
                "fencing_epoch",
                "claim_token_digest",
            ),
            "discovery": (
                "lifecycle_state",
                "review_reasons",
                "flagged_by_evidence_ids",
            ),
            "hypothesis": ("status", "review_reasons"),
            "task": ("lifecycle_state", "review_reasons"),
            "session_frame": ("frame_status", "stale_context"),
        }[target_type]
        return canonical_sha256({field: getattr(record, field) for field in fields})

    def _replay_existing(
        self,
        event: ValidityEventRecord,
        request_fingerprint: str,
    ) -> ValidityPropagationResult:
        if event.event_fingerprint != request_fingerprint:
            raise ValueError(
                f"Idempotency key {event.idempotency_key!r} is bound to another event."
            )
        self._assert_committed_effects(event)
        return self._result_from_event(event, replayed=True)

    def _assert_committed_effects(self, event: ValidityEventRecord) -> None:
        if event.processing_state != "COMMITTED" or not event.plan_fingerprint:
            raise PartialValidityPropagationError("Validity event is not completely committed.")
        authority = self.session.get(GovernanceAuthorityRecord, event.authority_id)
        if authority is None:
            raise PartialValidityPropagationError("Validity event authority is missing.")
        transitions = tuple(
            ValidityTargetTransition.model_validate(payload) for payload in event.affected_targets
        )
        persisted_plan = ValidityPropagationPlan(
            event_id=event.event_id,
            idempotency_key=event.idempotency_key,
            request_fingerprint=event.event_fingerprint,
            source_type=event.source_type,
            source_id=event.source_id,
            source_fingerprint=event.source_fingerprint,
            expected_source_state=event.expected_source_state,
            source_post_state=event.source_post_state,
            event_type=event.event_type,
            reason=event.reason,
            authority_id=event.authority_id,
            authority_identity=event.authority_identity,
            authority_class=event.authority_class,
            authority_purpose=authority.purpose,
            authority_operation=authority.operation_type,
            workspace_id=event.workspace_id,
            session_id=event.session_id,
            replacement_id=event.replacement_id,
            replacement_fingerprint=event.replacement_fingerprint,
            transitions=transitions,
        )
        if persisted_plan.derive_fingerprint() != event.plan_fingerprint:
            raise PartialValidityPropagationError("Validity event plan fingerprint is invalid.")
        expected_event_id = uuid5(
            _VALIDITY_EVENT_NAMESPACE,
            f"{event.idempotency_key}:{event.event_fingerprint}",
        )
        if event.event_id != expected_event_id:
            raise PartialValidityPropagationError("Validity event identity is invalid.")

        event_marker = str(event.event_id)
        for transition in transitions:
            if transition.target_type == "source":
                record = self._load_source(event.source_type, transition.target_id)
                if self._source_state(event.source_type, record) != transition.target_state:
                    raise PartialValidityPropagationError("Source transition is missing.")
                reason = getattr(record, "lifecycle_reason", None) or getattr(
                    record,
                    "validity_reason",
                    None,
                )
                if event_marker not in (reason or ""):
                    raise PartialValidityPropagationError("Source event provenance is missing.")
            elif transition.target_type == "evidence":
                record = self.session.get(EvidenceRecord, transition.target_id)
                self._require_effect(
                    record,
                    record is not None
                    and record.lifecycle_state.value == transition.target_state
                    and event_marker in (record.lifecycle_reason or ""),
                    transition,
                )
            elif transition.target_type == "evaluation":
                record = self.session.get(EvaluationControlRecord, transition.target_id)
                self._require_effect(
                    record,
                    record is not None
                    and record.state.value == transition.target_state
                    and event_marker in (record.invalidation_reason or ""),
                    transition,
                )
            elif transition.target_type == "admission_claim":
                record = self.session.get(
                    DiscoveryAdmissionClaimRecord,
                    transition.target_id,
                )
                self._require_effect(
                    record,
                    record is not None
                    and record.state.value == transition.target_state
                    and event_marker in (record.invalidation_reason or ""),
                    transition,
                )
            elif transition.target_type == "discovery":
                record = self.session.get(DiscoveryRecord, transition.target_id)
                self._require_effect(
                    record,
                    record is not None
                    and record.lifecycle_state.value == transition.target_state
                    and any(event_marker in item for item in record.review_reasons),
                    transition,
                )
            elif transition.target_type == "hypothesis":
                record = self.session.get(HypothesisRecord, transition.target_id)
                self._require_effect(
                    record,
                    record is not None
                    and record.status.value == transition.target_state
                    and any(event_marker in item for item in record.review_reasons),
                    transition,
                )
            elif transition.target_type == "task":
                record = self.session.get(TaskRecord, transition.target_id)
                self._require_effect(
                    record,
                    record is not None
                    and record.lifecycle_state.value == transition.target_state
                    and any(event_marker in item for item in record.review_reasons),
                    transition,
                )
            else:
                record = self.session.get(SessionFrameRecord, transition.target_id)
                self._require_effect(
                    record,
                    record is not None
                    and record.frame_status.value == transition.target_state
                    and any(
                        item.get("artifact_type") == f"validity_event:{event_marker}"
                        for item in record.stale_context
                    ),
                    transition,
                )

    @staticmethod
    def _require_effect(
        record: object | None,
        condition: bool,
        transition: ValidityTargetTransition,
    ) -> None:
        if record is None or not condition:
            raise PartialValidityPropagationError(
                f"Committed effect is missing for {transition.target_type}:{transition.target_id}."
            )

    @staticmethod
    def _result_from_event(
        event: ValidityEventRecord,
        *,
        replayed: bool,
    ) -> ValidityPropagationResult:
        transitions = [
            ValidityTargetTransition.model_validate(payload) for payload in event.affected_targets
        ]

        def count(target_type: str) -> int:
            return sum(item.target_type == target_type for item in transitions)

        evidence_count = count("evidence")
        if event.source_type == ValiditySourceType.EVIDENCE:
            evidence_count += 1
        return ValidityPropagationResult(
            event_id=event.event_id,
            idempotency_key=event.idempotency_key,
            plan_fingerprint=event.plan_fingerprint,
            replayed=replayed,
            affected_evidence_count=evidence_count,
            affected_evaluation_count=count("evaluation"),
            affected_admission_claim_count=count("admission_claim"),
            affected_discovery_count=count("discovery"),
            affected_hypothesis_count=count("hypothesis"),
            affected_task_count=count("task"),
            affected_session_frame_count=count("session_frame"),
            committed_at=event.committed_at,
        )

    @staticmethod
    def _event_note(plan: ValidityPropagationPlan) -> str:
        return (
            f"Validity event {plan.event_id} ({plan.event_type.value}) "
            f"from {plan.source_type.value}:{plan.source_id}: {plan.reason}"
        )

    @staticmethod
    def _expect_one(result: object, label: str) -> None:
        if getattr(result, "rowcount", None) != 1:
            raise StaleValidityPropagationError(f"Validity transition lost its fence for {label}.")

    def _inject(self, stage: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(stage)

    def _require_clean_unit_of_work(self) -> None:
        if self.session.new or self.session.dirty or self.session.deleted:
            raise RuntimeError("Validity propagation requires a clean application unit of work.")

    @staticmethod
    def _is_expired(expiry: datetime) -> bool:
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        return expiry <= datetime.now(UTC)
