from __future__ import annotations

import asyncio
from uuid import UUID

import pandas as pd

from agents.executor import (
    Capability,
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContext,
    ExecutorDispatcher,
    ExecutorInput,
    ExecutorRegistry,
)
from agents.executor.data_explorer import DataExplorer, DataExplorerResult
from schemas.artifacts import Task
from schemas.enums import TaskKind


def _task(*, description: str, evidence_expectation: str) -> Task:
    return Task(
        title="Inspect dataset",
        description=description,
        task_kind=TaskKind.ANALYTICAL,
        profile_id=UUID("11111111-1111-1111-1111-111111111111"),
        variables=["value"],
        evidence_expectation=evidence_expectation,
    )


def _request(capability: Capability, task: Task, dataset_path: str | None = None):
    return ExecutionRequest(
        capability=capability,
        input=ExecutorInput(task=task),
        context=ExecutorContext(dataset_path=dataset_path),
    )


def test_data_explorer_analysis_returns_role_native_observation(tmp_path) -> None:
    dataframe = pd.DataFrame({"value": [1, 2, 3], "group": ["a", "b", "a"]})
    dataset_path = tmp_path / "analysis.csv"
    dataframe.to_csv(dataset_path, index=False)

    result = asyncio.run(
        DataExplorer().run(
            _request(
                Capability.DATA_ANALYSIS,
                _task(
                    description="Report the row count and column names for this dataset.",
                    evidence_expectation="row_count",
                ),
                str(dataset_path),
            )
        )
    )

    assert isinstance(result, DataExplorerResult)
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.capability == Capability.DATA_ANALYSIS
    assert result.observations
    assert result.produced_data_profile is None


def test_data_explorer_profiling_returns_successor_candidate_profile(tmp_path) -> None:
    dataframe = pd.DataFrame({"value": [1, 1, None], "group": ["a", "a", "b"]})
    dataset_path = tmp_path / "profiling.csv"
    dataframe.to_csv(dataset_path, index=False)

    result = asyncio.run(
        DataExplorer().run(
            _request(
                Capability.DATA_PROFILING,
                _task(description="Profile the dataset.", evidence_expectation="profile"),
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
                _task(description="Transform the dataset.", evidence_expectation="new state"),
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
