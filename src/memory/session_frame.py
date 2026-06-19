"""Build compact session frames from active analytical artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

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
    DatasetContextSummary,
    DecisionContextSummary,
    EvidenceContextSummary,
    HypothesisContextSummary,
)
from schemas.enums import (
    AssumptionStatus,
    DecisionStatus,
    HypothesisStatus,
    ProjectStatus,
    QualityFlagSeverity,
)

ACTIVE_HYPOTHESIS_STATUSES = {
    HypothesisStatus.PROPOSED,
    HypothesisStatus.PLANNED,
    HypothesisStatus.VALIDATING,
    HypothesisStatus.INCONCLUSIVE,
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


class SessionFrameBuilder:
    """Build a compact working-context frame from current analytical artifacts."""

    def __init__(self, options: SessionFrameBuildOptions | None = None) -> None:
        self._options = options or SessionFrameBuildOptions()

    def build(
        self,
        *,
        project: Project,
        datasets: Sequence[DatasetAsset] = (),
        profiles: Sequence[DataProfile] = (),
        assumptions: Sequence[Assumption] = (),
        hypotheses: Sequence[Hypothesis] = (),
        evidence: Sequence[Evidence] = (),
        decisions: Sequence[DecisionLog] = (),
        pending_tasks: Sequence[str] = (),
        open_questions: Sequence[str] = (),
    ) -> SessionFrame:
        """Build a deterministic compact `SessionFrame` from active artifacts."""

        active_assumptions = self._active_assumptions(assumptions)
        active_hypotheses = self._active_hypotheses(hypotheses)
        assumption_evidence_counts = self._linked_evidence_counts(
            evidence,
            relation_name="assumption_ids",
        )
        hypothesis_evidence_counts = self._linked_evidence_counts(
            evidence,
            relation_name="hypothesis_ids",
        )
        active_dataset_ids = self._active_dataset_ids(
            datasets,
            active_assumptions,
            active_hypotheses,
        )
        latest_profiles = self._latest_profiles_by_dataset(profiles)
        selected_datasets = self._select_datasets(datasets, active_dataset_ids)
        selected_evidence = self._select_evidence(evidence, active_assumptions, active_hypotheses)
        selected_decisions = self._select_decisions(decisions)
        key_warnings = self._collect_warnings(selected_datasets, latest_profiles, selected_evidence)

        return SessionFrame(
            project_id=project.project_id,
            objective_snapshot=project.objective,
            project_summary=self._project_summary(project),
            dataset_summaries=[
                self._dataset_summary(dataset, latest_profiles.get(dataset.dataset_id))
                for dataset in selected_datasets
            ],
            active_dataset_refs=[dataset.dataset_id for dataset in selected_datasets],
            active_assumptions=[
                AssumptionContextSummary(
                    assumption_id=str(assumption.assumption_id),
                    statement=assumption.statement,
                    confidence=assumption.confidence.value,
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
                HypothesisContextSummary(
                    hypothesis_id=str(hypothesis.hypothesis_id),
                    statement=hypothesis.statement,
                    status=hypothesis.status.value,
                    validation_method=hypothesis.validation_method,
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
                EvidenceContextSummary(
                    evidence_id=str(item.evidence_id),
                    evidence_type=item.evidence_type.value,
                    method=item.method,
                    summary=item.result_summary.summary,
                    created_at=item.created_at,
                )
                for item in selected_evidence
            ],
            strongest_evidence_refs=[item.evidence_id for item in selected_evidence],
            recent_decisions=[
                DecisionContextSummary(
                    decision_id=str(decision.decision_id),
                    decision_type=decision.decision_type.value,
                    decision=decision.decision,
                    status=decision.status.value,
                    created_at=decision.created_at,
                )
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
    ) -> dict:
        counts: dict = {}
        for item in evidence:
            for related_id in getattr(item, relation_name):
                counts[related_id] = counts.get(related_id, 0) + 1
        return counts

    def _active_dataset_ids(
        self,
        datasets: Sequence[DatasetAsset],
        active_assumptions: Sequence[Assumption],
        active_hypotheses: Sequence[Hypothesis],
    ) -> set:
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

        primary_datasets = [dataset for dataset in datasets if dataset.role.value == "primary"]
        if primary_datasets:
            return {dataset.dataset_id for dataset in primary_datasets}
        return {dataset.dataset_id for dataset in datasets}

    @staticmethod
    def _latest_profiles_by_dataset(profiles: Sequence[DataProfile]) -> dict:
        latest: dict = {}
        for profile in sorted(profiles, key=lambda item: item.created_at, reverse=True):
            latest.setdefault(profile.dataset_id, profile)
        return latest

    def _select_datasets(
        self,
        datasets: Sequence[DatasetAsset],
        active_dataset_ids: set,
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
                len(active_hypothesis_ids.intersection(item.hypothesis_ids)),
                len(active_assumption_ids.intersection(item.assumption_ids)),
                item.created_at,
            ),
            reverse=True,
        )
        relevant = [
            item
            for item in ranked
            if active_hypothesis_ids.intersection(item.hypothesis_ids)
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
        latest_profiles: dict,
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
        return DatasetContextSummary(
            dataset_id=str(dataset.dataset_id),
            name=dataset.name,
            version=dataset.version,
            kind=dataset.kind.value,
            role=dataset.role.value,
            row_count=row_count,
            column_count=column_count,
            warning_count=warning_count,
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
