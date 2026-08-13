from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace
from uuid import uuid4

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataExecutionProvenance,
    DataExplorerObservation,
    DataExplorerResult,
)
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.planner_data_work import run_data_work
from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContext,
)
from cognieda.schemas.artifacts import DataProfile, Task
from cognieda.schemas.enums import TaskKind

DATASET_DIGEST = "sha256:" + "a" * 64


class ToolTestDispatcher:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest) -> DataExplorerResult:
        self.requests.append(request)
        return DataExplorerResult(
            source_role="data_explorer",
            task_id=request.input.task.task_id,
            work_id="tool-test:1",
            status=ExecutionStatus.SUCCEEDED,
            capability=Capability.DATA_ANALYSIS,
            observations=[
                DataExplorerObservation(
                    observation_type="row_count",
                    summary="Counted rows.",
                    payload={"row_count": 3},
                )
            ],
            provenance=DataExecutionProvenance(
                dataset_reference="dataset.csv",
                dataset_digest=DATASET_DIGEST,
                data_profile_id=request.context.data_profile_id,
                tool_reference="test:row-count",
                operation=DataAnalysisOperation.ROW_COUNT,
            ),
            analysis_plan=DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
        )


def test_semantic_data_tool_uses_application_supplied_authority_and_hidden_route() -> None:
    dispatcher = ToolTestDispatcher()
    task = Task(
        objective_id=uuid4(),
        kind=TaskKind.DATA,
        instruction="Understand dataset size.",
    )
    profile = DataProfile(row_count=3, column_count=0, columns=())
    deps = PlannerDeps(
        dispatcher=dispatcher,
        active_task=task,
        data_profile=profile,
        execution_context=ExecutorContext(
            dataset_path="dataset.csv",
            data_profile_id=profile.data_profile_id,
        ),
        dataset_digest=DATASET_DIGEST,
    )

    result = asyncio.run(
        run_data_work(
            SimpleNamespace(deps=deps),  # type: ignore[arg-type]
            "Count the rows needed to assess size.",
        )
    )

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.source_role == "data_explorer"
    assert len(dispatcher.requests) == 1
    request = dispatcher.requests[0]
    assert request.capability is Capability.DATA_ANALYSIS
    assert request.input.task == task
    assert request.input.requested_work == "Count the rows needed to assess size."
    assert deps.data_results[0].task_id == task.task_id
    assert tuple(inspect.signature(run_data_work).parameters) == (
        "ctx",
        "requested_work",
    )
