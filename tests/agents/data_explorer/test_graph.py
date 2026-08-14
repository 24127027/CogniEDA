from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from cognieda.agents.data_explorer.context import Context, DEInput
from cognieda.agents.data_explorer.graph import build_graph
from cognieda.agents.data_explorer.model import DataExplorerDecisionModel
from cognieda.agents.data_explorer.types import (
    AnalysisStep,
    EvaluationOutput,
    EvaluationVerdict,
    ExecutionType,
    PlanningOutput,
    State,
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



def test_build_graph_compiles_successfully():
    graph = build_graph()
    assert graph is not None


@pytest.mark.anyio
async def test_graph_happy_path():
    graph = build_graph()

    profile = create_dummy_profile()
    state = State(
        task_id=uuid4(),
        task_instruction="Count rows",
        dataset_path="dummy.csv",
        dataset_digest="sha256:dummy",
        data_profile=profile,
        max_iterations=3,
    )

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
    context = create_dummy_context(model, profile=profile)

    # In LangGraph, we can pass state dict and get dict back.
    result = await graph.ainvoke(state, config={"configurable": {}}, context=context)
    final_state = State.model_validate(result)

    assert final_state.workflow_status == "succeeded"
    assert final_state.emitted_evidence is not None
    assert final_state.emitted_evidence.content == {"step1": {"row_count": 0}} # dummy builtin tool returns 0 or actually error because df is None?
    # Wait, the dummy df in create_dummy_context is None! _load_df returns empty DataFrame.
    # empty DataFrame row_count tool returns 0 rows.
    # The tool exists. Let's assert it succeeded and we have content.
    assert "step1" in final_state.emitted_evidence.content


@pytest.mark.anyio
async def test_graph_unfeasible_path():
    graph = build_graph()

    profile = create_dummy_profile()
    state = State(
        task_id=uuid4(),
        task_instruction="Do impossible thing",
        dataset_path="dummy.csv",
        dataset_digest="sha256:dummy",
        data_profile=profile,
        max_iterations=3,
    )

    plan_out = PlanningOutput(
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
    )
    eval_out = EvaluationOutput(
        verdict=EvaluationVerdict.UNFEASIBLE,
        summary="Cannot do it",
    )
    model = FakeDataExplorerModel(planning_output=plan_out, evaluation_output=eval_out)
    context = create_dummy_context(model, profile=profile)

    result = await graph.ainvoke(state, config={"configurable": {}}, context=context)
    final_state = State.model_validate(result)

    assert final_state.workflow_status == "blocked"
    assert final_state.failure_reason == "Cannot do it"


@pytest.mark.anyio
async def test_graph_max_iterations_exceeded():
    graph = build_graph()

    profile = create_dummy_profile()
    state = State(
        task_id=uuid4(),
        task_instruction="Loop forever",
        dataset_path="dummy.csv",
        dataset_digest="sha256:dummy",
        data_profile=profile,
        max_iterations=2, # short budget
    )

    plan_out = PlanningOutput(
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
    )
    eval_out = EvaluationOutput(
        verdict=EvaluationVerdict.NEEDS_REVISION,
        summary="Needs more work",
        revision_feedback="Do more",
    )
    model = FakeDataExplorerModel(planning_output=plan_out, evaluation_output=eval_out)
    context = create_dummy_context(model, profile=profile)

    result = await graph.ainvoke(state, config={"configurable": {}}, context=context)
    final_state = State.model_validate(result)

    assert final_state.workflow_status == "failed"
    assert final_state.iteration == 2
    assert "exhausted 2 planning iterations" in str(final_state.failure_reason)
