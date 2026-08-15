from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from pydantic import ValidationError

from cognieda.agents.data_explorer import (
    CorrelationMethod,
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataExplorer,
    DataExplorerInput,
)
from cognieda.agents.data_explorer.planning import UnsupportedAnalysisRequest
from cognieda.delegation import (
    Capability,
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContext,
    ExecutorDispatcher,
    ExecutorInput,
    ExecutorRegistry,
)
from cognieda.schemas import DataProfile, Task, TaskKind


class InstructionPlanFake:
    async def propose(self, request):
        try:
            return DataAnalysisPlan.model_validate_json(request.task_instruction)
        except ValueError as exc:
            raise UnsupportedAnalysisRequest("Task is outside the finite operation set.") from exc


class RecordingPlanner:
    def __init__(self, plan: DataAnalysisPlan) -> None:
        self.plan = plan
        self.requests = []

    async def propose(self, request):
        self.requests.append(request)
        return self.plan


class FailingPlanner:
    async def propose(self, _request):
        raise RuntimeError("model unavailable")


def _task(instruction: str) -> Task:
    return Task(objective_id=uuid4(), kind=TaskKind.DATA, instruction=instruction)


def _request(
    dataset_path: Path | None,
    plan: DataAnalysisPlan | None,
    *,
    capability: Capability = Capability.DATA_ANALYSIS,
    data_profile_id=None,
) -> ExecutionRequest:
    profile_projection = _profile_projection(dataset_path, data_profile_id)
    return ExecutionRequest(
        capability=capability,
        input=(
            DataExplorerInput(
                task=_task(
                    plan.model_dump_json()
                    if plan is not None
                    else "Unsupported direct analysis request"
                ),
                data_profile=profile_projection,
            )
            if profile_projection is not None
            else ExecutorInput(
                task=_task(
                    plan.model_dump_json()
                    if plan is not None
                    else "Unsupported direct analysis request"
                )
            )
        ),
        context=ExecutorContext(
            dataset_path=str(dataset_path) if dataset_path is not None else None,
            data_profile_id=data_profile_id,
        ),
    )


def _run(request: ExecutionRequest):
    return asyncio.run(DataExplorer(analysis_planner=InstructionPlanFake()).run(request))


def _profile_projection(dataset_path: Path | None, data_profile_id) -> DataProfile | None:
    if data_profile_id is None:
        return None
    if dataset_path is not None and dataset_path.exists():
        profile = DataExplorer().profile_candidate(str(dataset_path.resolve())).profile
        return profile.model_copy(update={"data_profile_id": data_profile_id})
    return DataProfile(
        data_profile_id=data_profile_id,
        row_count=0,
        column_count=0,
        columns=(),
    )


def _write_dataset(path: Path) -> pd.DataFrame:
    dataframe = pd.DataFrame(
        {
            "amount": [1.0, 2.0, None, 4.0],
            "other": [2.0, 4.0, 6.0, 8.0],
            "group": ["a", "a", "b", "b"],
            "nullable": ["x", None, None, "x"],
        }
    )
    if path.suffix == ".csv":
        dataframe.to_csv(path, index=False)
    else:
        dataframe.to_parquet(path, index=False)
    return dataframe


@pytest.mark.parametrize("suffix", [".csv", ".parquet"])
def test_real_explicit_dataset_executes_exact_row_count(tmp_path, suffix) -> None:
    dataset_path = tmp_path / f"dataset{suffix}"
    _write_dataset(dataset_path)
    profile_id = uuid4()
    result = _run(
        _request(
            dataset_path,
            DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
            data_profile_id=profile_id,
        )
    )

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.observations[0].payload == {"row_count": 4}
    assert result.provenance is not None
    assert result.provenance.data_profile_id == profile_id
    assert result.provenance.tool_reference == "cognieda.data_explorer.row_count:v1"
    assert result.work_id.startswith("de:")


def test_real_request_dispatches_through_registered_data_explorer(tmp_path) -> None:
    dataset_path = tmp_path / "dispatched.csv"
    _write_dataset(dataset_path)
    request = _request(
        dataset_path,
        DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
        data_profile_id=uuid4(),
    )
    registry = ExecutorRegistry()
    registry.register(lambda: DataExplorer(analysis_planner=InstructionPlanFake()))

    result = asyncio.run(ExecutorDispatcher(registry).dispatch(request))

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.observations[0].payload == {"row_count": 4}


def test_all_allowlisted_operations_return_exact_bounded_results(tmp_path) -> None:
    dataset_path = tmp_path / "operations.csv"
    _write_dataset(dataset_path)
    profile_id = uuid4()
    plans = (
        DataAnalysisPlan(
            operation=DataAnalysisOperation.COLUMN_SUMMARY,
            columns=("nullable",),
        ),
        DataAnalysisPlan(
            operation=DataAnalysisOperation.MISSINGNESS,
            columns=("amount", "nullable"),
        ),
        DataAnalysisPlan(
            operation=DataAnalysisOperation.VALUE_COUNTS,
            columns=("group",),
            top_k=2,
        ),
        DataAnalysisPlan(
            operation=DataAnalysisOperation.DESCRIPTIVE_STATISTICS,
            columns=("amount",),
        ),
        DataAnalysisPlan(
            operation=DataAnalysisOperation.GROUP_SUMMARY,
            columns=("group", "amount"),
            max_groups=5,
        ),
        DataAnalysisPlan(
            operation=DataAnalysisOperation.CORRELATION,
            columns=("amount", "other"),
            correlation_method=CorrelationMethod.PEARSON,
        ),
    )
    payloads = [
        _run(_request(dataset_path, plan, data_profile_id=profile_id)).observations[0].payload
        for plan in plans
    ]

    assert payloads[0] == {
        "column": "nullable",
        "dtype": "object",
        "row_count": 4,
        "non_missing_count": 2,
        "missing_count": 2,
        "distinct_count": 1,
    }
    assert payloads[1] == {
        "row_count": 4,
        "columns": [
            {"column": "amount", "missing_count": 1, "missing_rate": 0.25},
            {"column": "nullable", "missing_count": 2, "missing_rate": 0.5},
        ],
    }
    assert payloads[2] == {
        "column": "group",
        "top_k": 2,
        "values": [{"value": "a", "count": 2}, {"value": "b", "count": 2}],
    }
    assert payloads[3]["statistics"] == pytest.approx(
        {
            "min": 1.0,
            "max": 4.0,
            "mean": 7 / 3,
            "median": 2.0,
            "standard_deviation": 1.5275252316519465,
            "p25": 1.5,
            "p75": 3.0,
        }
    )
    assert payloads[4] == {
        "group_column": "group",
        "value_column": "amount",
        "groups": [
            {"group": "a", "row_count": 2, "finite_count": 2, "mean": 1.5, "sum": 3.0},
            {"group": "b", "row_count": 2, "finite_count": 1, "mean": 4.0, "sum": 4.0},
        ],
    }
    assert payloads[5] == {
        "columns": ["amount", "other"],
        "method": "pearson",
        "matrix": [
            {"column": "amount", "values": [1.0, 1.0]},
            {"column": "other", "values": [1.0, 1.0]},
        ],
    }


def test_exact_column_validation_fails_closed(tmp_path) -> None:
    dataset_path = tmp_path / "columns.csv"
    _write_dataset(dataset_path)
    result = _run(
        _request(
            dataset_path,
            DataAnalysisPlan(
                operation=DataAnalysisOperation.COLUMN_SUMMARY,
                columns=("Amount",),
            ),
            data_profile_id=uuid4(),
        )
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "column_not_found"
    assert result.observations == []


def test_invalid_parameters_and_unsupported_operation_are_rejected() -> None:
    with pytest.raises(ValidationError, match="top_k"):
        DataAnalysisPlan(
            operation=DataAnalysisOperation.VALUE_COUNTS,
            columns=("group",),
            top_k=51,
        )
    with pytest.raises(ValidationError, match="operation"):
        DataAnalysisPlan.model_validate({"operation": "arbitrary_python", "columns": []})


def test_missing_plan_profile_binding_and_dataset_fail_closed(tmp_path) -> None:
    dataset_path = tmp_path / "bound.csv"
    _write_dataset(dataset_path)
    missing_plan = _run(_request(dataset_path, None, data_profile_id=uuid4()))
    missing_profile = _run(
        _request(dataset_path, DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT))
    )
    missing_dataset = _run(
        _request(
            tmp_path / "does-not-exist.csv",
            DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
            data_profile_id=uuid4(),
        )
    )

    assert missing_plan.failure is not None
    assert missing_plan.failure.code == "unsupported_analysis_request"
    assert missing_profile.failure is not None
    assert missing_profile.failure.code == "missing_data_profile_binding"
    assert missing_dataset.failure is not None
    assert missing_dataset.failure.code == "dataset_not_found"


def test_no_environment_or_process_cwd_dataset_authority(tmp_path, monkeypatch) -> None:
    ambient = tmp_path / "ambient.csv"
    _write_dataset(ambient)
    process_cwd = tmp_path / "cwd"
    process_cwd.mkdir()
    monkeypatch.setenv("COGNIEDA_DE_DATASET_PATH", str(ambient))
    monkeypatch.chdir(process_cwd)

    result = _run(
        _request(
            None,
            DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
            data_profile_id=uuid4(),
        )
    )
    relative_result = _run(
        _request(
            Path("ambient.csv"),
            DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
            data_profile_id=uuid4(),
        )
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "invalid_dataset_binding"
    assert relative_result.failure is not None
    assert relative_result.failure.code == "invalid_dataset_binding"


def test_workspace_and_external_absolute_paths_survive_arbitrary_cwd(tmp_path, monkeypatch) -> None:
    workspace_dataset = tmp_path / "workspace" / "data" / "workspace.csv"
    workspace_dataset.parent.mkdir(parents=True)
    external_dataset = tmp_path / "external" / "external.csv"
    external_dataset.parent.mkdir()
    _write_dataset(workspace_dataset)
    _write_dataset(external_dataset)
    unrelated_cwd = tmp_path / "unrelated"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)
    plan = DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT)

    results = [
        _run(_request(path, plan, data_profile_id=uuid4()))
        for path in (workspace_dataset, external_dataset)
    ]

    assert [result.observations[0].payload for result in results] == [
        {"row_count": 4},
        {"row_count": 4},
    ]
    assert [result.provenance.dataset_reference for result in results if result.provenance] == [
        str(workspace_dataset.resolve()),
        str(external_dataset.resolve()),
    ]


def test_analysis_and_profiling_do_not_mutate_source_dataset(tmp_path) -> None:
    dataset_path = tmp_path / "immutable.csv"
    original = pd.DataFrame(
        {
            "value": [1.0, 1.0, None, None],
            "duplicate": ["same", "same", None, None],
            "all_null": [None, None, None, None],
        }
    )
    original.to_csv(dataset_path, index=False)
    before_dataframe = pd.read_csv(dataset_path)
    before_bytes = dataset_path.read_bytes()
    before_digest = hashlib.sha256(before_bytes).hexdigest()

    analysis = _run(
        _request(
            dataset_path,
            DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
            data_profile_id=uuid4(),
        )
    )
    profiling = _run(_request(dataset_path, None, capability=Capability.DATA_PROFILING))

    assert analysis.status is ExecutionStatus.SUCCEEDED
    assert profiling.status is ExecutionStatus.SUCCEEDED
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == before_digest
    assert dataset_path.read_bytes() == before_bytes
    assert_frame_equal(pd.read_csv(dataset_path), before_dataframe)
    assert len(pd.read_csv(dataset_path)) == len(original)


def test_initial_profile_candidate_has_no_fabricated_task_lineage(tmp_path) -> None:
    dataset_path = tmp_path / "initial.csv"
    _write_dataset(dataset_path)

    candidate = DataExplorer().profile_candidate(str(dataset_path))

    assert candidate.profile.row_count == 4
    assert candidate.provenance.data_profile_id is None
    assert candidate.provenance.dataset_digest == (
        f"sha256:{hashlib.sha256(dataset_path.read_bytes()).hexdigest()}"
    )
    assert candidate.provenance.parameters == {"mode": "candidate"}
    assert "task_id" not in type(candidate).model_fields


def test_existing_profile_profiling_returns_observation_not_second_candidate(tmp_path) -> None:
    dataset_path = tmp_path / "profile-observation.csv"
    _write_dataset(dataset_path)
    profile_id = uuid4()
    result = _run(
        _request(
            dataset_path,
            None,
            capability=Capability.DATA_PROFILING,
            data_profile_id=profile_id,
        )
    )

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.produced_data_profile is None
    assert result.observations[0].payload["row_count"] == 4
    assert result.provenance is not None
    assert result.provenance.data_profile_id == profile_id


def test_tool_exception_and_non_json_result_are_typed_failures(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "failures.csv"
    _write_dataset(dataset_path)
    request = _request(
        dataset_path,
        DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
        data_profile_id=uuid4(),
    )

    def raise_tool_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("cognieda.agents.data_explorer.agent.execute_analysis", raise_tool_error)
    tool_failure = _run(request)
    monkeypatch.setattr(
        "cognieda.agents.data_explorer.agent.execute_analysis",
        lambda *_args, **_kwargs: {"bad": object()},
    )
    invalid_result = _run(request)

    assert tool_failure.failure is not None
    assert tool_failure.failure.code == "tool_execution_error"
    assert invalid_result.failure is not None
    assert invalid_result.failure.code == "invalid_result"


def test_task_instruction_is_operationalized_inside_data_explorer(tmp_path) -> None:
    dataset_path = tmp_path / "planning.csv"
    _write_dataset(dataset_path)
    profile = DataExplorer().profile_candidate(str(dataset_path)).profile
    planner = RecordingPlanner(DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT))
    request = ExecutionRequest(
        capability=Capability.DATA_ANALYSIS,
        input=DataExplorerInput(
            task=_task("Count the rows in the active dataset"),
            data_profile=profile,
        ),
        context=ExecutorContext(
            dataset_path=str(dataset_path),
            data_profile_id=profile.data_profile_id,
        ),
    )

    result = asyncio.run(DataExplorer(analysis_planner=planner).run(request))

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.observations[0].payload == {"row_count": 4}
    assert planner.requests[0].task_instruction == request.input.task.instruction
    assert planner.requests[0].data_profile == profile
    assert result.analysis_plan == planner.plan


def test_descriptive_task_uses_planner_proposal_and_deterministic_tool(tmp_path) -> None:
    dataset_path = tmp_path / "descriptive-planning.csv"
    pd.DataFrame({"age": [21, 34, 55]}).to_csv(dataset_path, index=False)
    profile = DataExplorer().profile_candidate(str(dataset_path)).profile
    planner = RecordingPlanner(
        DataAnalysisPlan(
            operation=DataAnalysisOperation.DESCRIPTIVE_STATISTICS,
            columns=("age",),
        )
    )
    request = ExecutionRequest(
        capability=Capability.DATA_ANALYSIS,
        input=DataExplorerInput(
            task=_task("Summarize age"),
            data_profile=profile,
        ),
        context=ExecutorContext(
            dataset_path=str(dataset_path),
            data_profile_id=profile.data_profile_id,
        ),
    )

    result = asyncio.run(DataExplorer(analysis_planner=planner).run(request))

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.observations[0].payload["column"] == "age"
    assert result.analysis_plan == planner.plan


def test_model_planner_failure_creates_typed_zero_observation_failure(tmp_path) -> None:
    dataset_path = tmp_path / "planner-failure.csv"
    _write_dataset(dataset_path)
    profile = DataExplorer().profile_candidate(str(dataset_path)).profile
    request = ExecutionRequest(
        capability=Capability.DATA_ANALYSIS,
        input=DataExplorerInput(
            task=_task("Count rows"),
            data_profile=profile,
        ),
        context=ExecutorContext(
            dataset_path=str(dataset_path),
            data_profile_id=profile.data_profile_id,
        ),
    )

    result = asyncio.run(DataExplorer(analysis_planner=FailingPlanner()).run(request))

    assert result.status is ExecutionStatus.FAILED
    assert result.failure is not None
    assert result.failure.code == "analysis_planning_failed"
    assert result.observations == []
