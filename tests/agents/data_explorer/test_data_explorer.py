from __future__ import annotations

import asyncio

import pandas as pd

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataExplorer,
    DataExplorerInput,
    DataExplorerResult,
)
from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContext,
    ExecutorDispatcher,
    ExecutorInput,
    ExecutorRegistry,
)
from cognieda.schemas.artifacts import DataProfile, Task


class FakeAnalysisPlanner:
    def __init__(self, plan: DataAnalysisPlan) -> None:
        self.plan = plan

    async def propose(self, _request):
        return self.plan


def _task(instruction: str) -> Task:
    return Task(instruction=instruction)


def _request(
    capability: Capability,
    task: Task,
    dataset_path: str | None = None,
    *,
    data_profile_id=None,
    data_profile: DataProfile | None = None,
):
    return ExecutionRequest(
        capability=capability,
        input=(
            DataExplorerInput(task=task, data_profile=data_profile)
            if data_profile is not None
            else ExecutorInput(task=task)
        ),
        context=ExecutorContext(
            dataset_path=dataset_path,
            data_profile_id=data_profile_id,
        ),
    )


def test_data_explorer_analysis_returns_role_native_observation(tmp_path) -> None:
    dataframe = pd.DataFrame({"value": [1, 2, 3], "group": ["a", "b", "a"]})
    dataset_path = tmp_path / "analysis.csv"
    dataframe.to_csv(dataset_path, index=False)
    profile = DataExplorer().profile_candidate(str(dataset_path)).profile

    result = asyncio.run(
        DataExplorer(
            analysis_planner=FakeAnalysisPlanner(
                DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT)
            )
        ).run(
            _request(
                Capability.DATA_ANALYSIS,
                _task("Report the row count and column names for this dataset."),
                str(dataset_path),
                data_profile_id=profile.data_profile_id,
                data_profile=profile,
            )
        )
    )

    assert isinstance(result, DataExplorerResult)
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.capability == Capability.DATA_ANALYSIS
    assert result.observations
    assert result.observations[0].payload == {"row_count": 3}
    assert result.provenance is not None
    assert result.provenance.dataset_reference == str(dataset_path.resolve())
    assert result.produced_data_profile is None


def test_data_explorer_profiling_returns_successor_candidate_profile(tmp_path) -> None:
    dataframe = pd.DataFrame({"value": [1, 1, None], "group": ["a", "a", "b"]})
    dataset_path = tmp_path / "profiling.csv"
    dataframe.to_csv(dataset_path, index=False)

    result = asyncio.run(
        DataExplorer().run(
            _request(
                Capability.DATA_PROFILING,
                _task("Profile the dataset."),
                str(dataset_path),
            )
        )
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.capability == Capability.DATA_PROFILING
    assert result.produced_data_profile is not None
    assert result.observations == []


def test_data_transformation_fails_closed_without_successor_semantics() -> None:
    result = asyncio.run(
        DataExplorer().run(
            _request(
                Capability.DATA_TRANSFORMATION,
                _task("Transform the dataset."),
            )
        )
    )

    assert result.status == ExecutionStatus.BLOCKED
    assert result.failure is not None
    assert result.failure.code == "successor_data_profile_not_implemented"
    assert result.produced_data_profile is None


def test_data_explorer_provider_maps_all_data_capabilities_to_one_instance() -> None:
    registry = ExecutorRegistry()
    registry.register_provider(
        DataExplorer,
        capabilities=(
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
            Capability.DATA_TRANSFORMATION,
        ),
    )
    dispatcher = ExecutorDispatcher(registry)

    providers = {registry.resolve(capability) for capability in registry.list_capabilities()}
    assert len(providers) == 1
    assert dispatcher is not None
