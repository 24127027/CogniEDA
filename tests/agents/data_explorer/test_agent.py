from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from cognieda.agents.data_explorer.agent import DataExplorer
from cognieda.agents.data_explorer.context import DEInput
from cognieda.agents.data_explorer.types import (
    AnalysisStep,
    DEErrorCode,
    EvaluationOutput,
    EvaluationVerdict,
    ExecutionType,
    PlanningOutput,
)

import pandas as pd
from cognieda.schemas.artifacts import DataProfile
from cognieda.schemas.common import ColumnProfile, ContinuousColumnSummary, VariableType

class FakeDataExplorerModel:
    def __init__(self, planning_output: PlanningOutput | Exception | None = None, evaluation_output: EvaluationOutput | Exception | None = None):
        self.planning_output = planning_output
        self.evaluation_output = evaluation_output
        self.plan_called_with: list[tuple[str, pd.DataFrame]] = []
        self.evaluate_called_with: list[tuple[str, pd.DataFrame | None]] = []

    async def plan(self, prompt: str, df: pd.DataFrame) -> PlanningOutput:
        self.plan_called_with.append((prompt, df))
        if isinstance(self.planning_output, Exception):
            raise self.planning_output
        if self.planning_output is None:
            raise NotImplementedError("planning_output not provided")
        return self.planning_output

    async def evaluate(self, prompt: str, df: pd.DataFrame | None) -> EvaluationOutput:
        self.evaluate_called_with.append((prompt, df))
        if isinstance(self.evaluation_output, Exception):
            raise self.evaluation_output
        if self.evaluation_output is None:
            raise NotImplementedError("evaluation_output not provided")
        return self.evaluation_output

def create_dummy_profile() -> DataProfile:
    return DataProfile(
        data_profile_id=uuid4(),
        row_count=10,
        column_count=1,
        columns=(
            ColumnProfile(
                name="age",
                dtype="int64",
                variable_type=VariableType.CONTINUOUS,
                distinct_count=10,
                missing_count=0,
                summary=ContinuousColumnSummary(min=1, max=10, mean=5, median=5, std=1, p25=3, p75=8),
            ),
        ),
    )


@pytest.mark.anyio
async def test_data_explorer_run_success():
    # Setup
    profile = create_dummy_profile()
    plan_out = PlanningOutput(
        steps=[
            AnalysisStep(
                step_id="step1",
                description="Row count",
                execution_type=ExecutionType.BUILTIN_TOOL,
                builtin_tool_name="row_count",
                expected_output_type="dict",
            )
        ],
        rationale="because",
    )
    eval_out = EvaluationOutput(
        verdict=EvaluationVerdict.SATISFIED,
        summary="Done",
    )
    model = FakeDataExplorerModel(planning_output=plan_out, evaluation_output=eval_out)
    
    de = DataExplorer(de_model=model)
    task_id = uuid4()
    de_input = DEInput(
        task_instruction="Count rows",
        dataset_path="dummy.csv",
        dataset_digest="sha256:dummy",
        data_profile=profile,
    )

    # Execute
    output = await de.run(task_id, de_input)

    # Assert
    assert output.task_id == task_id
    assert output.error is None
    assert output.evidence is not None
    assert output.data_profile is None
    assert output.summary == "Data Explorer completed analysis and admitted Evidence."
    assert "step1" in output.evidence.content


@pytest.mark.anyio
async def test_data_explorer_run_blocked():
    profile = create_dummy_profile()
    model = FakeDataExplorerModel(
        planning_output=PlanningOutput(
            steps=[
                AnalysisStep(
                    step_id="step1",
                    description="Try",
                    execution_type=ExecutionType.BUILTIN_TOOL,
                    builtin_tool_name="row_count",
                    expected_output_type="dict",
                )
            ],
            rationale="because",
        ),
        evaluation_output=EvaluationOutput(
            verdict=EvaluationVerdict.UNFEASIBLE,
            summary="Cannot be done",
        ),
    )
    
    de = DataExplorer(de_model=model)
    task_id = uuid4()
    de_input = DEInput(
        task_instruction="Impossible",
        dataset_path="dummy.csv",
        dataset_digest="sha256:dummy",
        data_profile=profile,
    )

    output = await de.run(task_id, de_input)

    assert output.task_id == task_id
    assert output.evidence is None
    assert output.data_profile is None
    assert output.error is not None
    assert output.error.code == DEErrorCode.UNFEASIBLE_REQUEST
    assert output.summary == "Cannot be done"


@pytest.mark.anyio
async def test_data_explorer_run_planning_failed():
    profile = create_dummy_profile()
    model = FakeDataExplorerModel(planning_output=RuntimeError("LLM broke"))
    
    de = DataExplorer(de_model=model)
    task_id = uuid4()
    de_input = DEInput(
        task_instruction="Crash",
        dataset_path="dummy.csv",
        dataset_digest="sha256:dummy",
        data_profile=profile,
    )

    output = await de.run(task_id, de_input)

    assert output.task_id == task_id
    assert output.evidence is None
    assert output.data_profile is None
    assert output.error is not None
    assert output.error.code == DEErrorCode.EXECUTION_FAILED
    assert "LLM broke" in output.error.message
