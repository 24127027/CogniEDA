"""Build compact session frames from active analytical artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from schemas.artifacts import (
    Assumption,
    DataProfile,
    DatasetAsset,
    DecisionLog,
    Evidence,
    Hypothesis,
    Project,
    SessionFrame,
)
from schemas.common import (
    AssumptionContextSummary,
    ContextProvenance,
    DatasetContextSummary,
    DeadEndSummary,
    DecisionContextSummary,
    EvidenceContextSummary,
    HypothesisContextSummary,
    InvalidationRule,
    StaleContextMarker,
    ToolResultCacheSummary,
)
from schemas.enums import (
    AssumptionStatus,
    ContextMode,
    DecisionStatus,
    HypothesisStatus,
    InvalidationTrigger,
    MemorySourceType,
    MemoryStatus,
    ProjectStatus,
    QualityFlagSeverity,
    SessionFrameStatus,
)

ACTIVE_HYPOTHESIS_STATUSES = {
    HypothesisStatus.PROPOSED,
    HypothesisStatus.PLANNED,
    HypothesisStatus.VALIDATING,
    HypothesisStatus.INCONCLUSIVE,
}

PLANNING_MEMORY_STATUSES = {
    MemoryStatus.ACTIVE,
    MemoryStatus.PINNED,
    MemoryStatus.TENTATIVE,
    MemoryStatus.VALIDATED,
    MemoryStatus.NEEDS_REVIEW,
    MemoryStatus.UNRESOLVED,
}

CONCLUSION_MEMORY_STATUSES = {
    MemoryStatus.ACTIVE,
    MemoryStatus.PINNED,
    MemoryStatus.VALIDATED,
}


@dataclass(frozen=True, slots=True)
class SessionFrameBuildOptions:
    """Deterministic limits for compact session frame assembly."""

    max_datasets: int = 3
    max_assumptions: int = 5
    max_hypotheses: int = 5
    max_evidence: int = 5
    max_decisions: int = 5
    max_warnings: int = 8
    max_pending_tasks: int = 8
    max_open_questions: int = 5


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """A typed, non-persistent view over a `SessionFrame` for one reasoning mode."""

    mode: ContextMode
    session_frame_id: UUID
    project_id: UUID
    objective_snapshot: str
    dataset_summaries: tuple[DatasetContextSummary, ...] = ()
    active_dataset_refs: tuple[UUID, ...] = ()
    assumptions: tuple[AssumptionContextSummary, ...] = ()
    assumption_refs: tuple[UUID, ...] = ()
    hypotheses: tuple[HypothesisContextSummary, ...] = ()
    hypothesis_refs: tuple[UUID, ...] = ()
    evidence: tuple[EvidenceContextSummary, ...] = ()
    evidence_refs: tuple[UUID, ...] = ()
    decisions: tuple[DecisionContextSummary, ...] = ()
    decision_refs: tuple[UUID, ...] = ()
    pending_tasks: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    key_warnings: tuple[str, ...] = ()
    stale_context: tuple[StaleContextMarker, ...] = ()
    dead_ends: tuple[DeadEndSummary, ...] = ()
    cached_tool_results: tuple[ToolResultCacheSummary, ...] = ()
    exclusion_notes: tuple[str, ...] = ()


class SessionContextBuilder:
    """Project `SessionFrame` snapshots into mode-specific context bundles."""

    def build(
        self,
        session_frame: SessionFrame,
        *,
        mode: ContextMode,
    ) -> ContextBundle:
        """Build a mode-specific context view without mutating the frame."""

        if mode == ContextMode.PLANNING:
            return self._planning_context(session_frame)
        if mode == ContextMode.CONCLUSION:
            return self._conclusion_context(session_frame)
        raise ValueError(f"Unsupported context mode: {mode}")

    def _planning_context(self, session_frame: SessionFrame) -> ContextBundle:
        dataset_summaries = tuple(
            item
            for item in session_frame.dataset_summaries
            if item.memory_status in PLANNING_MEMORY_STATUSES
        )
        assumptions = tuple(
            item
            for item in session_frame.active_assumptions
            if item.memory_status in PLANNING_MEMORY_STATUSES
        )
        hypotheses = tuple(
            item
            for item in session_frame.active_hypotheses
            if item.memory_status in PLANNING_MEMORY_STATUSES
            and item.status in ACTIVE_HYPOTHESIS_STATUSES
        )
        evidence = tuple(
            item
            for item in session_frame.strongest_evidence
            if item.memory_status in PLANNING_MEMORY_STATUSES
        )
        decisions = tuple(
            item
            for item in session_frame.recent_decisions
            if item.memory_status in PLANNING_MEMORY_STATUSES
            and item.status == DecisionStatus.ACTIVE
        )

        return ContextBundle(
            mode=ContextMode.PLANNING,
            session_frame_id=session_frame.session_frame_id,
            project_id=session_frame.project_id,
            objective_snapshot=session_frame.objective_snapshot,
            dataset_summaries=dataset_summaries,
            active_dataset_refs=tuple(item.dataset_id for item in dataset_summaries),
            assumptions=assumptions,
            assumption_refs=tuple(item.assumption_id for item in assumptions),
            hypotheses=hypotheses,
            hypothesis_refs=tuple(item.hypothesis_id for item in hypotheses),
            evidence=evidence,
            evidence_refs=tuple(item.evidence_id for item in evidence),
            decisions=decisions,
            decision_refs=tuple(item.decision_id for item in decisions),
            pending_tasks=tuple(session_frame.pending_tasks),
            open_questions=tuple(session_frame.open_questions),
            key_warnings=tuple(session_frame.key_warnings),
            stale_context=tuple(session_frame.stale_context),
            dead_ends=tuple(session_frame.dead_ends),
            cached_tool_results=tuple(
                item
                for item in session_frame.cached_tool_results
                if item.status in PLANNING_MEMORY_STATUSES
            ),
        )

    def _conclusion_context(self, session_frame: SessionFrame) -> ContextBundle:
        dataset_summaries = tuple(
            item
            for item in session_frame.dataset_summaries
            if item.memory_status in CONCLUSION_MEMORY_STATUSES
        )
        hypotheses = tuple(
            item
            for item in session_frame.active_hypotheses
            if item.memory_status in CONCLUSION_MEMORY_STATUSES
            and item.status in ACTIVE_HYPOTHESIS_STATUSES
        )
        evidence = tuple(
            item
            for item in session_frame.strongest_evidence
            if item.memory_status in CONCLUSION_MEMORY_STATUSES
        )

        return ContextBundle(
            mode=ContextMode.CONCLUSION,
            session_frame_id=session_frame.session_frame_id,
            project_id=session_frame.project_id,
            objective_snapshot=session_frame.objective_snapshot,
            dataset_summaries=dataset_summaries,
            active_dataset_refs=tuple(item.dataset_id for item in dataset_summaries),
            hypotheses=hypotheses,
            hypothesis_refs=tuple(item.hypothesis_id for item in hypotheses),
            evidence=evidence,
            evidence_refs=tuple(item.evidence_id for item in evidence),
            key_warnings=tuple(session_frame.key_warnings),
            exclusion_notes=(
                "Assumptions are excluded from Conclusion Context.",
                "Decision logs, pending tasks, stale context, dead ends, and cached tool "
                "summaries are excluded from Conclusion Context.",
            ),
        )


class SessionFrameBuilder:
    """Build a compact working-context frame from current analytical artifacts."""

    def __init__(self, options: SessionFrameBuildOptions | None = None) -> None:
        self._options = options or SessionFrameBuildOptions()

    def build(
        self,
        *,
        project: Project,
        frame_topic: str | None = None,
        frame_status: SessionFrameStatus = SessionFrameStatus.ACTIVE,
        frame_outcome: str | None = None,
        branch_key: str | None = None,
        checkpoint_label: str | None = None,
        parent_session_frame_id: UUID | None = None,
        datasets: Sequence[DatasetAsset] = (),
        profiles: Sequence[DataProfile] = (),
        assumptions: Sequence[Assumption] = (),
        hypotheses: Sequence[Hypothesis] = (),
        evidence: Sequence[Evidence] = (),
        decisions: Sequence[DecisionLog] = (),
        pending_tasks: Sequence[str] = (),
        open_questions: Sequence[str] = (),
        stale_context: Sequence[StaleContextMarker] = (),
        dead_ends: Sequence[DeadEndSummary] = (),
        cached_tool_results: Sequence[ToolResultCacheSummary] = (),
        frame_invalidation_rules: Sequence[InvalidationRule] = (),
        handoff_summary: str | None = None,
    ) -> SessionFrame:
        """Build a deterministic compact `SessionFrame` from active artifacts."""

        active_assumptions = self._active_assumptions(assumptions)
        active_hypotheses = self._active_hypotheses(hypotheses)
        assumption_evidence_counts = self._linked_evidence_counts(
            evidence,
            relation_name="assumption_ids",
        )
        hypothesis_evidence_counts = self._hypothesis_evidence_counts(evidence)
        active_dataset_ids = self._active_dataset_ids(
            datasets,
            active_assumptions,
            active_hypotheses,
            evidence,
        )
        latest_profiles = self._latest_profiles_by_dataset(profiles)
        selected_datasets = self._select_datasets(datasets, active_dataset_ids)
        selected_evidence = self._select_evidence(evidence, active_assumptions, active_hypotheses)
        selected_decisions = self._select_decisions(decisions)
        key_warnings = self._collect_warnings(selected_datasets, latest_profiles, selected_evidence)

        return SessionFrame(
            project_id=project.project_id,
            frame_topic=frame_topic or project.name,
            frame_status=frame_status,
            objective_snapshot=project.objective,
            frame_outcome=frame_outcome,
            project_summary=self._project_summary(project),
            branch_key=branch_key,
            checkpoint_label=checkpoint_label,
            parent_session_frame_id=parent_session_frame_id,
            handoff_summary=handoff_summary,
            dataset_summaries=[
                self._dataset_summary(dataset, latest_profiles.get(dataset.dataset_id))
                for dataset in selected_datasets
            ],
            active_dataset_refs=[dataset.dataset_id for dataset in selected_datasets],
            active_assumptions=[
                self._assumption_summary(
                    assumption,
                    linked_evidence_count=assumption_evidence_counts.get(
                        assumption.assumption_id,
                        0,
                    ),
                )
                for assumption in active_assumptions[: self._options.max_assumptions]
            ],
            active_assumption_refs=[
                assumption.assumption_id
                for assumption in active_assumptions[: self._options.max_assumptions]
            ],
            active_hypotheses=[
                self._hypothesis_summary(
                    hypothesis,
                    linked_evidence_count=hypothesis_evidence_counts.get(
                        hypothesis.hypothesis_id,
                        0,
                    ),
                )
                for hypothesis in active_hypotheses[: self._options.max_hypotheses]
            ],
            active_hypothesis_refs=[
                hypothesis.hypothesis_id
                for hypothesis in active_hypotheses[: self._options.max_hypotheses]
            ],
            strongest_evidence=[
                self._evidence_summary(item)
                for item in selected_evidence
            ],
            strongest_evidence_refs=[item.evidence_id for item in selected_evidence],
            recent_decisions=[
                self._decision_summary(decision)
                for decision in selected_decisions
            ],
            recent_decision_refs=[decision.decision_id for decision in selected_decisions],
            pending_tasks=self._pending_tasks(
                pending_tasks=pending_tasks,
                active_hypotheses=active_hypotheses,
                active_assumptions=active_assumptions,
            ),
            open_questions=list(open_questions[: self._options.max_open_questions]),
            key_warnings=key_warnings[: self._options.max_warnings],
            stale_context=list(stale_context),
            dead_ends=list(dead_ends),
            cached_tool_results=list(cached_tool_results),
            frame_invalidation_rules=list(frame_invalidation_rules),
        )

    @staticmethod
    def _project_summary(project: Project) -> str | None:
        if project.status == ProjectStatus.ARCHIVED:
            return f"{project.name} is archived."
        if project.research_questions:
            return f"{project.name}: {len(project.research_questions)} active research questions."
        return project.name

    @staticmethod
    def _active_assumptions(assumptions: Sequence[Assumption]) -> list[Assumption]:
        return sorted(
            [item for item in assumptions if item.status == AssumptionStatus.ACTIVE],
            key=lambda item: item.updated_at,
            reverse=True,
        )

    @staticmethod
    def _active_hypotheses(hypotheses: Sequence[Hypothesis]) -> list[Hypothesis]:
        return sorted(
            [item for item in hypotheses if item.status in ACTIVE_HYPOTHESIS_STATUSES],
            key=lambda item: item.updated_at,
            reverse=True,
        )

    @staticmethod
    def _linked_evidence_counts(
        evidence: Sequence[Evidence],
        *,
        relation_name: str,
    ) -> dict[UUID, int]:
        counts: dict[UUID, int] = {}
        for item in evidence:
            for related_id in getattr(item, relation_name):
                counts[related_id] = counts.get(related_id, 0) + 1
        return counts

    @staticmethod
    def _hypothesis_evidence_counts(evidence: Sequence[Evidence]) -> dict[UUID, int]:
        counts: dict[UUID, int] = {}
        for item in evidence:
            for evaluation in item.hypothesis_evaluations:
                counts[evaluation.hypothesis_id] = counts.get(evaluation.hypothesis_id, 0) + 1
        return counts

    def _active_dataset_ids(
        self,
        datasets: Sequence[DatasetAsset],
        active_assumptions: Sequence[Assumption],
        active_hypotheses: Sequence[Hypothesis],
        evidence: Sequence[Evidence],
    ) -> set[UUID]:
        dataset_ids = {
            item.dataset_id
            for item in active_assumptions
            if item.dataset_id is not None
        }
        dataset_ids.update(
            dataset_id
            for hypothesis in active_hypotheses
            for dataset_id in hypothesis.dataset_ids
        )
        if dataset_ids:
            return dataset_ids

        evidence_dataset_ids = {item.dataset_id for item in evidence}
        if evidence_dataset_ids:
            return evidence_dataset_ids

        primary_datasets = [dataset for dataset in datasets if dataset.role.value == "primary"]
        if primary_datasets:
            return {dataset.dataset_id for dataset in primary_datasets}
        return {dataset.dataset_id for dataset in datasets}

    @staticmethod
    def _latest_profiles_by_dataset(profiles: Sequence[DataProfile]) -> dict[UUID, DataProfile]:
        latest: dict[UUID, DataProfile] = {}
        for profile in sorted(profiles, key=lambda item: item.created_at, reverse=True):
            latest.setdefault(profile.dataset_id, profile)
        return latest

    def _select_datasets(
        self,
        datasets: Sequence[DatasetAsset],
        active_dataset_ids: set[UUID],
    ) -> list[DatasetAsset]:
        selected = [dataset for dataset in datasets if dataset.dataset_id in active_dataset_ids]
        selected.sort(
            key=lambda item: (
                item.role.value == "primary",
                item.updated_at,
            ),
            reverse=True,
        )
        return selected[: self._options.max_datasets]

    def _select_evidence(
        self,
        evidence: Sequence[Evidence],
        active_assumptions: Sequence[Assumption],
        active_hypotheses: Sequence[Hypothesis],
    ) -> list[Evidence]:
        active_assumption_ids = {item.assumption_id for item in active_assumptions}
        active_hypothesis_ids = {item.hypothesis_id for item in active_hypotheses}
        ranked = sorted(
            evidence,
            key=lambda item: (
                len(active_hypothesis_ids.intersection(self._evidence_hypothesis_ids(item))),
                len(active_assumption_ids.intersection(item.assumption_ids)),
                item.created_at,
            ),
            reverse=True,
        )
        relevant = [
            item
            for item in ranked
            if active_hypothesis_ids.intersection(self._evidence_hypothesis_ids(item))
            or active_assumption_ids.intersection(item.assumption_ids)
        ]
        if relevant:
            return relevant[: self._options.max_evidence]
        return ranked[: self._options.max_evidence]

    def _select_decisions(self, decisions: Sequence[DecisionLog]) -> list[DecisionLog]:
        active_decisions = [item for item in decisions if item.status == DecisionStatus.ACTIVE]
        active_decisions.sort(key=lambda item: item.updated_at, reverse=True)
        return active_decisions[: self._options.max_decisions]

    def _collect_warnings(
        self,
        selected_datasets: Sequence[DatasetAsset],
        latest_profiles: dict[UUID, DataProfile],
        selected_evidence: Sequence[Evidence],
    ) -> list[str]:
        warnings: list[str] = []
        selected_dataset_ids = {dataset.dataset_id for dataset in selected_datasets}

        for dataset_id in selected_dataset_ids:
            profile = latest_profiles.get(dataset_id)
            if profile is None:
                continue
            for quality_flag in profile.quality_flags:
                if quality_flag.severity in {
                    QualityFlagSeverity.WARNING,
                    QualityFlagSeverity.ERROR,
                }:
                    prefix = quality_flag.column_name or "dataset"
                    warnings.append(f"{prefix}: {quality_flag.message}")

        for item in selected_evidence:
            for limitation in item.limitations:
                warnings.append(f"evidence:{item.evidence_id} {limitation}")

        deduped: list[str] = []
        for warning in warnings:
            if warning not in deduped:
                deduped.append(warning)
        return deduped

    @staticmethod
    def _evidence_hypothesis_ids(evidence: Evidence) -> set[UUID]:
        return {evaluation.hypothesis_id for evaluation in evidence.hypothesis_evaluations}

    def _dataset_summary(
        self,
        dataset: DatasetAsset,
        profile: DataProfile | None,
    ) -> DatasetContextSummary:
        warning_count = 0
        row_count = None
        column_count = None
        if profile is not None:
            warning_count = sum(
                1
                for quality_flag in profile.quality_flags
                if quality_flag.severity in {QualityFlagSeverity.WARNING, QualityFlagSeverity.ERROR}
            )
            row_count = profile.row_count
            column_count = profile.column_count
        provenance: list[ContextProvenance] = []
        if profile is not None:
            provenance.append(
                ContextProvenance(
                    source_type=MemorySourceType.DATA_PROFILE,
                    reference=str(profile.profile_id),
                    note="Counts and warnings derive from the latest available data profile.",
                )
            )
        invalidation_rules = [
            InvalidationRule(
                trigger=InvalidationTrigger.DATASET_VERSION_CHANGE,
                detail=f"Refresh if dataset {dataset.name} moves beyond version {dataset.version}.",
            ),
            InvalidationRule(
                trigger=InvalidationTrigger.SCHEMA_CHANGE,
                detail=f"Refresh if dataset {dataset.name} changes shape or inferred schema.",
            ),
        ]
        return DatasetContextSummary(
            dataset_id=dataset.dataset_id,
            name=dataset.name,
            version=dataset.version,
            kind=dataset.kind,
            role=dataset.role,
            row_count=row_count,
            column_count=column_count,
            warning_count=warning_count,
            provenance=provenance,
            invalidation_rules=invalidation_rules,
        )

    @staticmethod
    def _assumption_summary(
        assumption: Assumption,
        *,
        linked_evidence_count: int,
    ) -> AssumptionContextSummary:
        provenance: list[ContextProvenance] = []
        if assumption.profile_id is not None:
            provenance.append(
                ContextProvenance(
                    source_type=MemorySourceType.DATA_PROFILE,
                    reference=str(assumption.profile_id),
                    note="Assumption was linked to a data profile when captured.",
                )
            )
        invalidation_rules: list[InvalidationRule] = []
        if assumption.dataset_id is not None:
            invalidation_rules.append(
                InvalidationRule(
                    trigger=InvalidationTrigger.DATASET_VERSION_CHANGE,
                    detail="Review the assumption if the linked dataset version changes.",
                )
            )
        return AssumptionContextSummary(
            assumption_id=assumption.assumption_id,
            statement=assumption.statement,
            confidence=assumption.confidence,
            linked_evidence_count=linked_evidence_count,
            provenance=provenance,
            invalidation_rules=invalidation_rules,
        )

    @staticmethod
    def _hypothesis_summary(
        hypothesis: Hypothesis,
        *,
        linked_evidence_count: int,
    ) -> HypothesisContextSummary:
        invalidation_rules: list[InvalidationRule] = []
        if hypothesis.assumption_ids:
            invalidation_rules.append(
                InvalidationRule(
                    trigger=InvalidationTrigger.ASSUMPTION_REJECTED,
                    detail="Re-evaluate the hypothesis if any supporting assumption is rejected.",
                )
            )
        if hypothesis.dataset_ids:
            invalidation_rules.append(
                InvalidationRule(
                    trigger=InvalidationTrigger.DATASET_VERSION_CHANGE,
                    detail="Re-evaluate the hypothesis if any linked dataset version changes.",
                )
            )
        return HypothesisContextSummary(
            hypothesis_id=hypothesis.hypothesis_id,
            statement=hypothesis.statement,
            status=hypothesis.status,
            validation_method=hypothesis.validation_method,
            linked_evidence_count=linked_evidence_count,
            invalidation_rules=invalidation_rules,
        )

    @staticmethod
    def _evidence_summary(evidence: Evidence) -> EvidenceContextSummary:
        return EvidenceContextSummary(
            evidence_id=evidence.evidence_id,
            evidence_type=evidence.evidence_type,
            method=evidence.method,
            summary=evidence.result_summary.summary,
            created_at=evidence.created_at,
            memory_status=MemoryStatus.VALIDATED,
            provenance=[
                ContextProvenance(
                    source_type=MemorySourceType.VALIDATION_RESULT,
                    reference=evidence.provenance.execution_label,
                    note="Evidence was captured as a reproducible validation result.",
                )
            ],
            invalidation_rules=[
                InvalidationRule(
                    trigger=InvalidationTrigger.DATASET_VERSION_CHANGE,
                    detail="Re-check the evidence if the evaluated dataset version changes.",
                )
            ],
        )

    @staticmethod
    def _decision_summary(decision: DecisionLog) -> DecisionContextSummary:
        return DecisionContextSummary(
            decision_id=decision.decision_id,
            decision_type=decision.decision_type,
            decision=decision.decision,
            status=decision.status,
            created_at=decision.created_at,
        )

    def _pending_tasks(
        self,
        *,
        pending_tasks: Sequence[str],
        active_hypotheses: Sequence[Hypothesis],
        active_assumptions: Sequence[Assumption],
    ) -> list[str]:
        explicit = list(pending_tasks[: self._options.max_pending_tasks])
        if explicit:
            return explicit

        inferred: list[str] = []
        for hypothesis in active_hypotheses:
            if hypothesis.status in {HypothesisStatus.PROPOSED, HypothesisStatus.PLANNED}:
                inferred.append(f"Plan validation for hypothesis: {hypothesis.statement}")
            elif hypothesis.status == HypothesisStatus.VALIDATING:
                inferred.append(f"Continue validation for hypothesis: {hypothesis.statement}")
            elif hypothesis.status == HypothesisStatus.INCONCLUSIVE:
                inferred.append(f"Refine or branch inconclusive hypothesis: {hypothesis.statement}")

        if not inferred:
            for assumption in active_assumptions:
                inferred.append(f"Review active assumption: {assumption.statement}")

        deduped: list[str] = []
        for item in inferred:
            if item not in deduped:
                deduped.append(item)
        return deduped[: self._options.max_pending_tasks]
