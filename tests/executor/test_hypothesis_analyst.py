from __future__ import annotations

import asyncio
from uuid import UUID

from agents.executor import ExecutionRequest, ExecutionResult, ExecutorContext, ExecutorInput
from agents.executor.hypothesis_analyst.agent import HypothesisAnalyst
from schemas.artifacts import (
    Discovery,
    Evidence,
    EvidenceProvenance,
    EvidenceResultSummary,
    Hypothesis,
    Task,
)
from schemas.enums import DiscoveryEpistemicStatus, EvidenceType, TaskKind


def _task() -> Task:
    return Task(
        title="Assess treatment effect",
        description="Check whether the treatment increases the target metric.",
        task_kind=TaskKind.ANALYTICAL,
        profile_id=UUID("11111111-1111-1111-1111-111111111111"),
        variables=["treatment", "target_metric"],
        evidence_expectation="Treatment increases the target metric.",
    )


def test_hypothesis_analyst_runs_end_to_end_with_injected_boundaries() -> None:
    def mock_dispatcher_call(request: ExecutionRequest) -> ExecutionResult:
        hypothesis = Hypothesis(
            task_id=request.input.task.task_id,
            profile_id=request.input.task.profile_id,
            statement="The treatment increases the target metric.",
            scope=request.input.task.description,
            validation_method="mean comparison",
            evidence_expectation=request.input.task.evidence_expectation or "",
            variables=list(request.input.task.variables),
        )
        evidence = Evidence(
            hypothesis_id=hypothesis.hypothesis_id,
            profile_id=hypothesis.profile_id,
            analysis_frame_ref="analysis-frame:test",
            execution_run_ref="execution-run:test",
            evidence_type=EvidenceType.EXPERIMENT_RESULT,
            method="mean comparison",
            provenance=EvidenceProvenance(
                analysis_frame_ref="analysis-frame:test",
                execution_run_ref="execution-run:test",
            ),
            result_summary=EvidenceResultSummary(
                summary="The treatment increased the target metric by 12%.",
                key_findings=["Treatment increased the target metric."],
            ),
        )
        return ExecutionResult(
            evidence_drafts=[evidence],
            discovery_drafts=[],
            execution_run_ref="execution-run:test",
        )

    def mock_admission_call(draft: Discovery) -> bool:
        return bool(draft.evidence_ids)

    executor = HypothesisAnalyst(
        mock_dispatcher_call=mock_dispatcher_call,
        mock_admission_call=mock_admission_call,
    )

    result = asyncio.run(executor.run(input=ExecutorInput(task=_task()), context=ExecutorContext()))

    assert result.execution_logs == []
    assert result.evidence_drafts
    assert result.discovery_drafts
    assert result.evidence_refs
    assert result.final_result is not None
    assert result.final_result["evidence_refs"] == result.evidence_refs
