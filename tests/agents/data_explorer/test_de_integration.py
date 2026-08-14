from __future__ import annotations

import asyncio
from typing import Any, Sequence
from uuid import uuid4

import pandas as pd
import pytest
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.test import TestModel

from cognieda.agents.data_explorer.agent import DataExplorer
from cognieda.agents.data_explorer.context import DEInput
from cognieda.agents.data_explorer.types import (
    AnalysisStep,
    EvaluationOutput,
    EvaluationVerdict,
    ExecutionType,
    PlanningOutput,
)
from cognieda.application.ports.llm import AgentFactoryPort, ModelConfig
from cognieda.schemas.artifacts import DataProfile

from cognieda.schemas.common import ColumnProfile, ContinuousColumnSummary, VariableType

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


class MockAgentFactory(AgentFactoryPort):
    def create_agent(
        self,
        *,
        worker: str,
        config: ModelConfig,
        deps_type: type[Any],
        builtin_tools: Sequence[Any],
    ) -> Agent[Any]:
        # Return a pydantic_ai agent using the TestModel so no real API calls are made.
        return Agent(
            TestModel(),
            deps_type=deps_type,
            system_prompt="You are a test agent.",
        )

    def reload_tooling(self) -> None:
        pass


@pytest.mark.anyio
async def test_de_integration_with_planner_mock():
    # Setup
    profile = create_dummy_profile()
    df = pd.DataFrame({"age": [10, 20, 30]})

    # Create the DE using a TestModel-backed agent factory
    factory = MockAgentFactory()
    config = ModelConfig(provider="openai", model_name="gpt-4o")
    
    de = DataExplorer(agent_factory=factory, model_config=config)
    
    # We must patch the TestModel's structured output generation inside pydantic_ai 
    # to return a valid PlanningOutput and EvaluationOutput, because otherwise 
    # TestModel might just return empty/default Pydantic models.
    # For integration testing the wire-up, we can just patch `de.model.plan` and `de.model.evaluate`
    # if we want to bypass the actual LLM call, OR rely on TestModel's defaults.
    # Since TestModel returns default values (e.g. empty lists for steps), it might fail validation
    # if we require min_length=1. Let's just mock the `de.model` methods for reliability
    # or patch the TestModel's custom return types.
    
    # Actually, let's just use our FakeDataExplorerModel for the integration logic test
    # to ensure it behaves correctly when called from a Planner-like context.
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
    
    plan_out = PlanningOutput(
        steps=[
            AnalysisStep(
                step_id="step1",
                description="Row count",
                target_columns=["age"],
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
    
    de.model = FakeDataExplorerModel(planning_output=plan_out, evaluation_output=eval_out)

    task_id = uuid4()
    de_input = DEInput(
        task_instruction="Count rows",
        dataset_path="dummy.csv",
        dataset_digest="sha256:dummy",
        data_profile=profile,
        dataframe=df,
    )

    # Execute (Mocking Planner Request)
    output = await de.run(task_id, de_input)

    # Assert
    assert output.task_id == task_id
    assert output.error is None
    assert output.evidence is not None
    assert output.data_profile is None
    assert "step1" in output.evidence.content
