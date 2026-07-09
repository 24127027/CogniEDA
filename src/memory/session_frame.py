"""SessionFrame helpers for type-safe active-context assembly."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from schemas.artifacts import (
    Assumption,
    DataProfile,
    Discovery,
    Evidence,
    Hypothesis,
    Objective,
    SessionFrame,
    Task,
    UserDecision,
)
from schemas.common import (
    AssumptionContextSummary,
    ContextProvenance,
    DataProfileContextSummary,
    DeadEndSummary,
    DiscoveryContextSummary,
    EvidenceContextSummary,
    HypothesisContextSummary,
    InvalidationRule,
    StaleContextMarker,
    TaskContextSummary,
    ToolResultCacheSummary,
    UserDecisionContextSummary,
)
from schemas.enums import (
    AssumptionStatus,
    ContextMode,
    FirstClassObjectType,
    HypothesisStatus,
    InvalidationTrigger,
    MemorySourceType,
    MemoryStatus,
    SessionFrameStatus,
    TaskLifecycleState,
    UserDecisionStatus,
)

from .retrieval_policy import exclusion_reason, is_allowed_in_context

_CONCLUSION_SAFE_MEMORY_STATUSES = {
    MemoryStatus.ACTIVE,
    MemoryStatus.PINNED,
    MemoryStatus.VALIDATED,
}

_PLANNING_TASK_STATES = {
    TaskLifecycleState.PROPOSED,
    TaskLifecycleState.ACTIVE,
    TaskLifecycleState.PAUSED,
}


@dataclass(frozen=True, slots=True)
class SessionFrameBuildOptions:
    """Selection limits for compact session-frame snapshots."""

    max_profiles: int = 5
    max_tasks: int = 10
    max_assumptions: int = 5
    max_hypotheses: int = 5
    max_discoveries: int = 8
    max_evidence: int = 8
    max_user_decisions: int = 5


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """Mode-specific projection from a SessionFrame."""

    mode: ContextMode
    objective_snapshot: str
    data_profile_summaries: tuple[DataProfileContextSummary, ...] = ()
    data_profile_refs: tuple[UUID, ...] = ()
    tasks: tuple[TaskContextSummary, ...] = ()
    task_refs: tuple[UUID, ...] = ()
    assumptions: tuple[AssumptionContextSummary, ...] = ()
    assumption_refs: tuple[UUID, ...] = ()
    hypotheses: tuple[HypothesisContextSummary, ...] = ()
    hypothesis_refs: tuple[UUID, ...] = ()
    discoveries: tuple[DiscoveryContextSummary, ...] = ()
    discovery_refs: tuple[UUID, ...] = ()
    evidence: tuple[EvidenceContextSummary, ...] = ()
    evidence_refs: tuple[UUID, ...] = ()
    user_decisions: tuple[UserDecisionContextSummary, ...] = ()
    user_decision_refs: tuple[UUID, ...] = ()
    pending_tasks: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    key_warnings: tuple[str, ...] = ()
    stale_context: tuple[StaleContextMarker, ...] = ()
    dead_ends: tuple[DeadEndSummary, ...] = ()
    cached_tool_results: tuple[ToolResultCacheSummary, ...] = ()
    exclusion_notes: tuple[str, ...] = ()


class SessionContextBuilder:
    """Map active-context snapshots into planning or conclusion context."""

    def build(self, session_frame: SessionFrame, *, mode: ContextMode) -> ContextBundle:
        """Build a typed context projection for the requested mode."""

        if mode == ContextMode.PLANNING:
            return self._planning_context(session_frame)
        if mode == ContextMode.ANSWER:
            return self._answer_context(session_frame)
        if mode in {ContextMode.CONCLUSION, ContextMode.DISCOVERY_SYNTHESIS}:
            return self._discovery_synthesis_context(session_frame, mode=mode)
        raise ValueError(f"Unsupported context mode: {mode}")

    def _planning_context(self, session_frame: SessionFrame) -> ContextBundle:
        profiles = tuple(
            item
            for item in session_frame.data_profile_summaries
            if is_allowed_in_context(
                FirstClassObjectType.DATA_PROFILE,
                item.lifecycle_state,
                ContextMode.PLANNING,
            )
        )
        tasks = tuple(
            item
            for item in session_frame.active_tasks
            if is_allowed_in_context(
                FirstClassObjectType.TASK,
                item.lifecycle_state,
                ContextMode.PLANNING,
            )
        )
        assumptions = tuple(
            item
            for item in session_frame.active_assumptions
            if item.memory_status in _CONCLUSION_SAFE_MEMORY_STATUSES
            and is_allowed_in_context(
                FirstClassObjectType.ASSUMPTION,
                AssumptionStatus.ACTIVE,
                ContextMode.PLANNING,
            )
        )
        hypotheses = tuple(
            item
            for item in session_frame.active_hypotheses
            if item.memory_status in _CONCLUSION_SAFE_MEMORY_STATUSES
            and is_allowed_in_context(
                FirstClassObjectType.HYPOTHESIS,
                item.status,
                ContextMode.PLANNING,
            )
        )
        discoveries, discovery_exclusion_notes = self._project_discoveries(
            session_frame.relevant_discoveries,
            mode=ContextMode.PLANNING,
        )
        evidence = tuple(
            item
            for item in session_frame.supporting_evidence
            if is_allowed_in_context(
                FirstClassObjectType.EVIDENCE,
                item.lifecycle_state,
                ContextMode.PLANNING,
            )
        )
        return ContextBundle(
            mode=ContextMode.PLANNING,
            objective_snapshot=session_frame.objective_snapshot,
            data_profile_summaries=profiles,
            data_profile_refs=tuple(item.profile_id for item in profiles),
            tasks=tasks,
            task_refs=tuple(item.task_id for item in tasks),
            assumptions=assumptions,
            assumption_refs=tuple(item.assumption_id for item in assumptions),
            hypotheses=hypotheses,
            hypothesis_refs=tuple(item.hypothesis_id for item in hypotheses),
            discoveries=discoveries,
            discovery_refs=tuple(item.discovery_id for item in discoveries),
            evidence=evidence,
            evidence_refs=tuple(item.evidence_id for item in evidence),
            user_decisions=tuple(session_frame.recent_user_decisions),
            user_decision_refs=tuple(session_frame.recent_user_decision_refs),
            pending_tasks=tuple(session_frame.pending_tasks),
            open_questions=tuple(session_frame.open_questions),
            key_warnings=tuple(session_frame.key_warnings),
            stale_context=tuple(session_frame.stale_context),
            dead_ends=tuple(session_frame.dead_ends),
            cached_tool_results=(),
            exclusion_notes=discovery_exclusion_notes,
        )

    def _discovery_synthesis_context(
        self,
        session_frame: SessionFrame,
        *,
        mode: ContextMode,
    ) -> ContextBundle:
        profiles = tuple(
            item
            for item in session_frame.data_profile_summaries
            if item.memory_status in _CONCLUSION_SAFE_MEMORY_STATUSES
            and is_allowed_in_context(
                FirstClassObjectType.DATA_PROFILE,
                item.lifecycle_state,
                mode,
            )
            and item.accepted_as_ground_truth
        )
        hypotheses = tuple(
            item
            for item in session_frame.active_hypotheses
            if item.memory_status in _CONCLUSION_SAFE_MEMORY_STATUSES
            and is_allowed_in_context(
                FirstClassObjectType.HYPOTHESIS,
                item.status,
                mode,
            )
        )
        evidence = tuple(
            item
            for item in session_frame.supporting_evidence
            if item.memory_status in _CONCLUSION_SAFE_MEMORY_STATUSES
            and is_allowed_in_context(
                FirstClassObjectType.EVIDENCE,
                item.lifecycle_state,
                mode,
            )
        )
        return ContextBundle(
            mode=mode,
            objective_snapshot=session_frame.objective_snapshot,
            data_profile_summaries=profiles,
            data_profile_refs=tuple(item.profile_id for item in profiles),
            hypotheses=hypotheses,
            hypothesis_refs=tuple(item.hypothesis_id for item in hypotheses),
            evidence=evidence,
            evidence_refs=tuple(item.evidence_id for item in evidence),
            key_warnings=tuple(session_frame.key_warnings),
            exclusion_notes=(
                "Assumptions are excluded from Discovery Synthesis Context.",
                "Existing Discoveries are excluded so new Discoveries must be "
                "synthesized from Hypothesis, accepted DataProfile, provenance, and "
                "active Evidence.",
                "Tasks, user decisions, pending questions, dead ends, stale context, "
                "and caches are excluded from Discovery Synthesis Context.",
            ),
        )

    def _answer_context(self, session_frame: SessionFrame) -> ContextBundle:
        profiles = tuple(
            item
            for item in session_frame.data_profile_summaries
            if item.memory_status in _CONCLUSION_SAFE_MEMORY_STATUSES
            and is_allowed_in_context(
                FirstClassObjectType.DATA_PROFILE,
                item.lifecycle_state,
                ContextMode.ANSWER,
            )
        )
        hypotheses = tuple(
            item
            for item in session_frame.active_hypotheses
            if item.memory_status in _CONCLUSION_SAFE_MEMORY_STATUSES
            and is_allowed_in_context(
                FirstClassObjectType.HYPOTHESIS,
                item.status,
                ContextMode.ANSWER,
            )
        )
        discoveries, discovery_exclusion_notes = self._project_discoveries(
            session_frame.relevant_discoveries,
            mode=ContextMode.ANSWER,
        )
        evidence = tuple(
            item
            for item in session_frame.supporting_evidence
            if item.memory_status in _CONCLUSION_SAFE_MEMORY_STATUSES
            and is_allowed_in_context(
                FirstClassObjectType.EVIDENCE,
                item.lifecycle_state,
                ContextMode.ANSWER,
            )
        )
        return ContextBundle(
            mode=ContextMode.ANSWER,
            objective_snapshot=session_frame.objective_snapshot,
            data_profile_summaries=profiles,
            data_profile_refs=tuple(item.profile_id for item in profiles),
            hypotheses=hypotheses,
            hypothesis_refs=tuple(item.hypothesis_id for item in hypotheses),
            discoveries=discoveries,
            discovery_refs=tuple(item.discovery_id for item in discoveries),
            evidence=evidence,
            evidence_refs=tuple(item.evidence_id for item in evidence),
            key_warnings=tuple(session_frame.key_warnings),
            exclusion_notes=(
                "Answer Context may include existing Discoveries for user Q&A.",
                "Assumptions remain excluded from answer synthesis unless explicitly requested.",
                *discovery_exclusion_notes,
            ),
        )

    @staticmethod
    def _project_discoveries(
        summaries: Sequence[DiscoveryContextSummary],
        *,
        mode: ContextMode,
    ) -> tuple[tuple[DiscoveryContextSummary, ...], tuple[str, ...]]:
        projected: list[DiscoveryContextSummary] = []
        exclusion_notes: list[str] = []

        for summary in summaries:
            reason = exclusion_reason(
                FirstClassObjectType.DISCOVERY,
                summary.memory_status,
                mode,
            )
            if reason is None:
                reason = exclusion_reason(
                    FirstClassObjectType.DISCOVERY,
                    summary.lifecycle_state,
                    mode,
                )
            if reason is None:
                projected.append(summary)
                continue
            exclusion_notes.append(
                SessionContextBuilder._discovery_exclusion_note(
                    summary,
                    mode=mode,
                    reason=reason,
                )
            )

        return tuple(projected), tuple(exclusion_notes)

    @staticmethod
    def _discovery_exclusion_note(
        summary: DiscoveryContextSummary,
        *,
        mode: ContextMode,
        reason: str,
    ) -> str:
        return (
            f"Discovery {summary.discovery_id} excluded from {mode.value} context: "
            f"memory_status={summary.memory_status.value}; "
            f"lifecycle_state={summary.lifecycle_state.value}; {reason}"
        )


class SessionFrameBuilder:
    """Build compact SessionFrame snapshots from typed FCOs and provenance."""

    def __init__(self, options: SessionFrameBuildOptions | None = None) -> None:
        self._options = options or SessionFrameBuildOptions()

    def build(
        self,
        *,
        objective: Objective,
        frame_topic: str | None = None,
        frame_status: SessionFrameStatus = SessionFrameStatus.ACTIVE,
        frame_outcome: str | None = None,
        data_profiles: tuple[DataProfile, ...] | list[DataProfile] = (),
        tasks: tuple[Task, ...] | list[Task] = (),
        assumptions: tuple[Assumption, ...] | list[Assumption] = (),
        hypotheses: tuple[Hypothesis, ...] | list[Hypothesis] = (),
        discoveries: tuple[Discovery, ...] | list[Discovery] = (),
        evidence: tuple[Evidence, ...] | list[Evidence] = (),
        user_decisions: tuple[UserDecision, ...] | list[UserDecision] = (),
        pending_tasks: list[str] | None = None,
        open_questions: list[str] | None = None,
        key_warnings: list[str] | None = None,
        stale_context: list[StaleContextMarker] | None = None,
        dead_ends: list[DeadEndSummary] | None = None,
        cached_tool_results: list[ToolResultCacheSummary] | None = None,
        parent_session_frame_id: UUID | None = None,
    ) -> SessionFrame:
        """Build a SessionFrame snapshot without promoting summaries to knowledge."""

        selected_profiles = list(data_profiles)[: self._options.max_profiles]
        active_tasks = [
            task for task in tasks if task.lifecycle_state in _PLANNING_TASK_STATES
        ][: self._options.max_tasks]
        active_assumptions = [
            assumption
            for assumption in assumptions
            if assumption.status == AssumptionStatus.ACTIVE
        ][: self._options.max_assumptions]
        active_hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if hypothesis.status in {HypothesisStatus.PROPOSED, HypothesisStatus.TESTING}
        ][: self._options.max_hypotheses]
        selected_discoveries = list(discoveries)[: self._options.max_discoveries]
        selected_evidence = list(evidence)[: self._options.max_evidence]
        selected_user_decisions = [
            decision
            for decision in user_decisions
            if decision.status == UserDecisionStatus.ACTIVE
        ][: self._options.max_user_decisions]

        warnings = list(key_warnings or [])
        warnings.extend(
            limitation
            for evidence_item in selected_evidence
            for limitation in evidence_item.limitations
        )

        return SessionFrame(
            frame_topic=frame_topic or objective.title,
            frame_status=frame_status,
            objective_snapshot=objective.statement,
            frame_outcome=frame_outcome,
            objective_summary=self._objective_summary(objective),
            parent_session_frame_id=parent_session_frame_id,
            data_profile_summaries=[
                self._profile_summary(profile) for profile in selected_profiles
            ],
            active_data_profile_refs=[profile.profile_id for profile in selected_profiles],
            active_tasks=[self._task_summary(task) for task in active_tasks],
            active_task_refs=[task.task_id for task in active_tasks],
            active_assumptions=[
                self._assumption_summary(assumption) for assumption in active_assumptions
            ],
            active_assumption_refs=[
                assumption.assumption_id for assumption in active_assumptions
            ],
            active_hypotheses=[
                self._hypothesis_summary(
                    hypothesis,
                    linked_evidence_count=self._evidence_count_for_hypothesis(
                        selected_evidence,
                        hypothesis.hypothesis_id,
                    ),
                )
                for hypothesis in active_hypotheses
            ],
            active_hypothesis_refs=[
                hypothesis.hypothesis_id for hypothesis in active_hypotheses
            ],
            relevant_discoveries=[
                self._discovery_summary(discovery) for discovery in selected_discoveries
            ],
            relevant_discovery_refs=[
                discovery.discovery_id for discovery in selected_discoveries
            ],
            supporting_evidence=[
                self._evidence_summary(evidence_item) for evidence_item in selected_evidence
            ],
            supporting_evidence_refs=[
                evidence_item.evidence_id for evidence_item in selected_evidence
            ],
            recent_user_decisions=[
                self._user_decision_summary(decision) for decision in selected_user_decisions
            ],
            recent_user_decision_refs=[
                decision.decision_id for decision in selected_user_decisions
            ],
            pending_tasks=pending_tasks or self._infer_pending_tasks(
                active_tasks,
                active_assumptions,
            ),
            open_questions=open_questions or [],
            key_warnings=warnings,
            stale_context=stale_context or [],
            dead_ends=dead_ends or [],
            cached_tool_results=cached_tool_results or [],
        )

    @staticmethod
    def _objective_summary(objective: Objective) -> str | None:
        if objective.status.value in {"completed", "archived"}:
            return f"Objective is {objective.status.value}: {objective.title}"
        return None

    @staticmethod
    def _profile_summary(profile: DataProfile) -> DataProfileContextSummary:
        return DataProfileContextSummary(
            profile_id=profile.profile_id,
            dataset_path=profile.dataset_path,
            dvc_hash=profile.dvc_hash,
            dvc_version_label=profile.dvc_version_label,
            row_count=profile.row_count,
            column_count=profile.column_count,
            warning_count=len(profile.quality_flags),
            lifecycle_state=profile.lifecycle_state,
            accepted_as_ground_truth=profile.accepted_as_ground_truth,
            provenance=[
                ContextProvenance(
                    source_type=MemorySourceType.DATA_PROFILE,
                    reference=str(profile.profile_id),
                )
            ],
            invalidation_rules=[
                InvalidationRule(
                    trigger=InvalidationTrigger.DATA_PROFILE_SUPERSEDED,
                    detail="Refresh context if this DataProfile is superseded.",
                )
            ],
        )

    @staticmethod
    def _task_summary(task: Task) -> TaskContextSummary:
        return TaskContextSummary(
            task_id=task.task_id,
            title=task.title,
            lifecycle_state=task.lifecycle_state.value,
            parent_task_id=task.parent_task_id,
        )

    @staticmethod
    def _assumption_summary(assumption: Assumption) -> AssumptionContextSummary:
        return AssumptionContextSummary(
            assumption_id=assumption.assumption_id,
            statement=assumption.statement,
            confidence=assumption.confidence,
            provenance=[
                ContextProvenance(
                    source_type=MemorySourceType.USER_CONFIRMATION,
                    reference=(
                        str(assumption.scoped_data_profile_ids[0])
                        if assumption.scoped_data_profile_ids
                        else None
                    ),
                    note="Assumption may guide planning but not conclusion inference.",
                )
            ],
        )

    @staticmethod
    def _hypothesis_summary(
        hypothesis: Hypothesis,
        *,
        linked_evidence_count: int,
    ) -> HypothesisContextSummary:
        return HypothesisContextSummary(
            hypothesis_id=hypothesis.hypothesis_id,
            statement=hypothesis.statement,
            status=hypothesis.status,
            validation_method=hypothesis.validation_method,
            linked_evidence_count=linked_evidence_count,
            provenance=[
                ContextProvenance(
                    source_type=MemorySourceType.VALIDATION_RESULT,
                    reference=str(hypothesis.task_id),
                )
            ],
        )

    @staticmethod
    def _discovery_summary(discovery: Discovery) -> DiscoveryContextSummary:
        return DiscoveryContextSummary(
            discovery_id=discovery.discovery_id,
            claim_statement=discovery.claim.statement,
            epistemic_status=discovery.epistemic_status,
            scope=discovery.scope,
            evidence_ids=discovery.evidence_ids,
            lifecycle_state=discovery.lifecycle_state,
            provenance=[
                ContextProvenance(
                    source_type=MemorySourceType.VALIDATION_RESULT,
                    reference=str(discovery.hypothesis_id),
                )
            ],
        )

    @staticmethod
    def _evidence_summary(evidence: Evidence) -> EvidenceContextSummary:
        return EvidenceContextSummary(
            evidence_id=evidence.evidence_id,
            evidence_type=evidence.evidence_type,
            method=evidence.method,
            summary=evidence.result_summary.summary,
            created_at=evidence.created_at,
            lifecycle_state=evidence.lifecycle_state,
            provenance=[
                ContextProvenance(
                    source_type=MemorySourceType.EXECUTION_RUN,
                    reference=evidence.execution_run_ref,
                ),
                ContextProvenance(
                    source_type=MemorySourceType.ANALYSIS_FRAME,
                    reference=evidence.analysis_frame_ref,
                ),
            ],
        )

    @staticmethod
    def _user_decision_summary(decision: UserDecision) -> UserDecisionContextSummary:
        return UserDecisionContextSummary(
            decision_id=decision.decision_id,
            decision_type=decision.decision_type,
            decision=decision.decision,
            status=decision.status,
            created_at=decision.created_at,
            provenance=[
                ContextProvenance(
                    source_type=MemorySourceType.USER_CONFIRMATION,
                    reference=str(decision.decision_id),
                )
            ],
        )

    @staticmethod
    def _evidence_count_for_hypothesis(
        evidence: list[Evidence],
        hypothesis_id: UUID,
    ) -> int:
        return sum(1 for item in evidence if item.hypothesis_id == hypothesis_id)

    @staticmethod
    def _infer_pending_tasks(
        tasks: list[Task],
        active_assumptions: list[Assumption],
    ) -> list[str]:
        pending = [
            f"Continue active task: {task.title}"
            for task in tasks
            if task.lifecycle_state == TaskLifecycleState.ACTIVE
        ]
        pending.extend(
            f"Review active assumption for planning: {assumption.statement}"
            for assumption in active_assumptions
        )
        return pending
