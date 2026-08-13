from __future__ import annotations

import asyncio
from uuid import uuid4

from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataExecutionProvenance,
    DataExplorerObservation,
    DataExplorerResult,
)
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.ports import ModelConfig
from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContext,
)
from cognieda.schemas.artifacts import DataProfile, Task
from cognieda.schemas.enums import TaskKind

DATASET_DIGEST = "sha256:" + "b" * 64


class RecordingDispatcher:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest) -> DataExplorerResult:
        self.requests.append(request)
        interaction = len(self.requests)
        return DataExplorerResult(
            source_role="data_explorer",
            task_id=request.input.task.task_id,
            work_id=f"data-work:{interaction}",
            status=ExecutionStatus.SUCCEEDED,
            capability=Capability.DATA_ANALYSIS,
            observations=[
                DataExplorerObservation(
                    observation_type="row_count",
                    summary=f"Completed interaction {interaction}.",
                    payload={"row_count": 4},
                )
            ],
            provenance=DataExecutionProvenance(
                dataset_reference="customers.csv",
                dataset_digest=DATASET_DIGEST,
                data_profile_id=request.context.data_profile_id,
                tool_reference="test:row-count",
                operation=DataAnalysisOperation.ROW_COUNT,
            ),
            analysis_plan=DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
        )


def _model_function(
    messages: list[ModelRequest | ModelResponse],
    info: AgentInfo,
) -> ModelResponse:
    returns = [
        part
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.tool_name == "run_data_work"
    ]
    if len(returns) < 2:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "run_data_work",
                    {
                        "requested_work": (
                            "Count rows for the approved goal."
                            if not returns
                            else "Repeat the row count to check consistency."
                        )
                    },
                    tool_call_id=f"data-call-{len(returns) + 1}",
                )
            ]
        )
    output_tool = info.output_tools[0]
    return ModelResponse(
        parts=[
            ToolCallPart(
                output_tool.name,
                {
                    "response": (
                        "Two governed Data Explorer interactions completed; these outputs "
                        "are not admitted Evidence."
                    ),
                    "blocker": None,
                },
                tool_call_id="final-response",
            )
        ]
    )


class LocalAgentFactory:
    def create_agent(self, *, deps_type, builtin_tools, **kwargs):
        del kwargs
        return Agent(
            FunctionModel(_model_function),
            deps_type=deps_type,
            tools=builtin_tools,
        )


def test_one_approved_task_can_drive_multiple_native_data_tool_interactions() -> None:
    dispatcher = RecordingDispatcher()
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        agent_factory=LocalAgentFactory(),  # type: ignore[arg-type]
        model_config=ModelConfig(
            provider="openai",
            model_name="local-function-model",
            api_key="not-used",
        ),
    )
    task = Task(
        objective_id=uuid4(),
        kind=TaskKind.DATA,
        instruction="Establish and verify the active dataset row count.",
    )
    profile = DataProfile(row_count=4, column_count=0, columns=())

    output = asyncio.run(
        planner.execute_task(
            task=task,
            data_profile=profile,
            execution_context=ExecutorContext(
                dataset_path="customers.csv",
                data_profile_id=profile.data_profile_id,
            ),
            dataset_digest=DATASET_DIGEST,
        )
    )

    assert output.blocker is None
    assert len(output.data_results) == 2
    assert [result.task_id for result in output.data_results] == [
        task.task_id,
        task.task_id,
    ]
    assert [request.input.requested_work for request in dispatcher.requests] == [
        "Count rows for the approved goal.",
        "Repeat the row count to check consistency.",
    ]
    assert "not admitted Evidence" in output.response
