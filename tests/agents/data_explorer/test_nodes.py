from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pandas as pd
import pytest

from cognieda.agents.data_explorer.context import Context, DEInput
from cognieda.agents.data_explorer.model import DataExplorerDecisionModel
from cognieda.agents.data_explorer.nodes import _MAX_STEP_RETRIES, check_result, execute, planning
from cognieda.agents.data_explorer.types import (
    AnalysisStep,
    DEErrorCode,
    EvaluationOutput,
    EvaluationVerdict,
    ExecutionType,
    PlanningOutput,
    State,
    StepResult,
    StepStatus,
)
from cognieda.schemas.artifacts import DataProfile
from cognieda.schemas.common import (
    ColumnProfile,
    ContinuousColumnSummary,
    VariableType,
)


class FakeDataExplorerModel:
    def __init__(self, planning_output: PlanningOutput | Exception | None = None, evaluation_output: EvaluationOutput | Exception | None = None):
        self.planning_output = planning_output
        self.evaluation_output = evaluation_output
        self.plan_called_with: list[tuple[str, pd.DataFrame]] = []
        self.evaluate_called_with: list[tuple[str, pd.DataFrame | None]] = []

    async def plan(self, prompt: str, df: pd.DataFrame, *, deps: Any | None = None) -> PlanningOutput:
        self.plan_called_with.append((prompt, df))
        if isinstance(self.planning_output, Exception):
            raise self.planning_output
        if self.planning_output is None:
            raise NotImplementedError("planning_output not provided")
        return self.planning_output

    async def evaluate(self, prompt: str, df: pd.DataFrame | None, *, deps: Any | None = None) -> EvaluationOutput:
        self.evaluate_called_with.append((prompt, df))
        if isinstance(self.evaluation_output, Exception):
            raise self.evaluation_output
        if self.evaluation_output is None:
            raise NotImplementedError("evaluation_output not provided")
        return self.evaluation_output


class FakeRuntime:
    def __init__(self, context: Context):
        self.context = context


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


def create_dummy_state(instruction: str = "Test task") -> State:
    profile = create_dummy_profile()
    return State(
        task_id=uuid4(),
        task_instruction=instruction,
        dataset_path="dummy.csv",
        dataset_digest="sha256:dummy",
        data_profile=profile,
        max_iterations=3,
    )


def create_dummy_context(model: DataExplorerDecisionModel, df: pd.DataFrame | None = None, profile: DataProfile | None = None) -> Context:
    return Context(
        de_model=model,
        de_input=DEInput(
            task_instruction="Test task",
            dataset_path="dummy.csv",
            dataset_digest="sha256:dummy",
            data_profile=profile,
            dataframe=df,
        ),
    )


@pytest.mark.anyio
async def test_planning_node_success():
    state = create_dummy_state()
    model_output = PlanningOutput(
        steps=[
            AnalysisStep(
                step_id="step1",
                description="desc",
                target_columns=["age"],
                execution_type=ExecutionType.BUILTIN_TOOL,
                builtin_tool_name="row_count",
                expected_output_type="dict",
            )
        ],
        rationale="because",
    )
    model = FakeDataExplorerModel(planning_output=model_output)
    context = create_dummy_context(model, profile=state.data_profile)
    runtime = FakeRuntime(context)

    new_state = await planning(state, runtime)

    assert new_state.workflow_status == "pending"
    assert new_state.plan == model_output.steps
    assert len(model.plan_called_with) == 1
    prompt, df = model.plan_called_with[0]
    assert state.task_instruction in prompt


@pytest.mark.anyio
async def test_planning_node_failure():
    state = create_dummy_state()
    model = FakeDataExplorerModel(planning_output=RuntimeError("LLM failed"))
    context = create_dummy_context(model, profile=state.data_profile)
    runtime = FakeRuntime(context)

    new_state = await planning(state, runtime)

    assert new_state.workflow_status == "failed"
    assert new_state.failure_reason is not None
    assert "LLM failed" in new_state.failure_reason


@pytest.mark.anyio
async def test_execute_node_builtin_tool_success():
    state = create_dummy_state()
    state.plan = [
        AnalysisStep(
            step_id="step1",
            description="Row count",
            target_columns=[],
            execution_type=ExecutionType.BUILTIN_TOOL,
            builtin_tool_name="row_count",
            builtin_tool_kwargs={},
            expected_output_type="dict",
        )
    ]
    df = pd.DataFrame({"age": [1, 2, 3]})
    context = create_dummy_context(FakeDataExplorerModel(), df=df)
    runtime = FakeRuntime(context)

    new_state = await execute(state, runtime)

    assert len(new_state.execution_results) == 1
    result = new_state.execution_results[0]
    assert result.step_id == "step1"
    assert result.status == StepStatus.SUCCEEDED
    assert "row_count" in result.output_payload
    assert result.output_payload["row_count"] == 3


@pytest.mark.anyio
async def test_execute_node_retries_on_failure():
    state = create_dummy_state()
    state.plan = [
        AnalysisStep(
            step_id="bad_step",
            description="Fails",
            target_columns=[],
            execution_type=ExecutionType.BUILTIN_TOOL,
            builtin_tool_name="nonexistent_tool",
            expected_output_type="dict",
        )
    ]
    df = pd.DataFrame()
    context = create_dummy_context(FakeDataExplorerModel(), df=df)
    runtime = FakeRuntime(context)

    new_state = await execute(state, runtime)

    assert len(new_state.execution_results) == 1
    result = new_state.execution_results[0]
    assert result.step_id == "bad_step"
    assert result.status == StepStatus.FAILED
    assert result.retry_count == _MAX_STEP_RETRIES + 1
    assert "Unknown builtin tool" in str(result.error)


@pytest.mark.anyio
async def test_check_result_satisfied_emits_evidence():
    state = create_dummy_state()
    state.execution_results = [
        StepResult(
            step_id="step1",
            status=StepStatus.SUCCEEDED,
            output_payload={"row_count": 3},
            variables_accessed=[],
        )
    ]
    eval_output = EvaluationOutput(
        verdict=EvaluationVerdict.SATISFIED,
        summary="All good",
    )
    model = FakeDataExplorerModel(evaluation_output=eval_output)
    context = create_dummy_context(model, profile=state.data_profile)
    runtime = FakeRuntime(context)

    new_state = await check_result(state, runtime)

    assert new_state.workflow_status == "succeeded"
    assert new_state.emitted_evidence is not None
    assert new_state.emitted_evidence.content == {"step1": {"row_count": 3}}
    assert new_state.emitted_evidence.data_profile_id == state.data_profile.data_profile_id


@pytest.mark.anyio
async def test_check_result_needs_revision():
    state = create_dummy_state()
    state.iteration = 0
    eval_output = EvaluationOutput(
        verdict=EvaluationVerdict.NEEDS_REVISION,
        summary="Needs work",
        revision_feedback="Fix the things",
    )
    model = FakeDataExplorerModel(evaluation_output=eval_output)
    context = create_dummy_context(model, profile=state.data_profile)
    runtime = FakeRuntime(context)

    new_state = await check_result(state, runtime)

    assert new_state.workflow_status == "pending"
    assert new_state.iteration == 1
    assert new_state.revision_feedback == "Fix the things"


@pytest.mark.anyio
async def test_check_result_needs_revision_exhausts_budget():
    state = create_dummy_state()
    state.iteration = 2  # Max is 3, so next iteration hits limit
    eval_output = EvaluationOutput(
        verdict=EvaluationVerdict.NEEDS_REVISION,
        summary="Needs work",
        revision_feedback="Still bad",
    )
    model = FakeDataExplorerModel(evaluation_output=eval_output)
    context = create_dummy_context(model, profile=state.data_profile)
    runtime = FakeRuntime(context)

    new_state = await check_result(state, runtime)

    assert new_state.workflow_status == "failed"
    assert "exhausted 3 planning iterations" in str(new_state.failure_reason)


@pytest.mark.anyio
async def test_check_result_unfeasible():
    state = create_dummy_state()
    eval_output = EvaluationOutput(
        verdict=EvaluationVerdict.UNFEASIBLE,
        summary="Cannot be done",
        revision_feedback="We don't have the data",
    )
    model = FakeDataExplorerModel(evaluation_output=eval_output)
    context = create_dummy_context(model, profile=state.data_profile)
    runtime = FakeRuntime(context)

    new_state = await check_result(state, runtime)

    assert new_state.workflow_status == "blocked"
    assert new_state.failure_reason == "We don't have the data"
