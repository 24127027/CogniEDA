from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from sqlmodel import Session

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataExplorer,
    DataExplorerInput,
)
from cognieda.application.services import (
    DataAdmissionError,
    DataAdmissionErrorCode,
    MvpDataProfileAdmissionService,
    MvpEvidenceAdmissionService,
)
from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutorContext,
    ExecutorInput,
)
from cognieda.infrastructure.persistence.repositories import (
    AssumptionRepository,
    DataProfileDatasetBindingRepository,
    DataProfileRepository,
    EvidenceRepository,
    ObjectiveRepository,
    TaskRepository,
)
from cognieda.schemas import Assumption, DataProfile, Objective, Task, TaskKind, TaskStatus


class FixedPlanner:
    def __init__(self, plan: DataAnalysisPlan | None = None) -> None:
        self.plan = plan or DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT)

    async def propose(self, _request):
        return self.plan


def _raw_profile(db_session, row_count: int = 3) -> DataProfile:
    return DataProfileRepository(db_session).create(
        DataProfile(row_count=row_count, column_count=0, columns=())
    )


def _admitted_profile(db_session, dataset_path) -> DataProfile:
    candidate = DataExplorer().profile_candidate(str(dataset_path))
    return MvpDataProfileAdmissionService(db_session).admit_candidate(candidate).data_profile


def _persisted_task(
    db_session,
    instruction: str = "Count rows",
    status: TaskStatus = TaskStatus.COMPLETED,
    kind: TaskKind = TaskKind.DATA,
) -> Task:
    objective = ObjectiveRepository(db_session).create(Objective(text="Understand dataset size"))
    return TaskRepository(db_session).create(
        Task(
            objective_id=objective.objective_id,
            kind=kind,
            instruction=instruction,
            status=status,
        )
    )


def _execute(dataset_path, task: Task, profile: DataProfile):
    request = ExecutionRequest(
        capability=Capability.DATA_ANALYSIS,
        input=DataExplorerInput(task=task, data_profile=profile),
        context=ExecutorContext(
            dataset_path=str(dataset_path),
            data_profile_id=profile.data_profile_id,
        ),
    )
    result = asyncio.run(DataExplorer(analysis_planner=FixedPlanner()).run(request))
    return request, result


def test_successful_real_work_admits_exactly_one_immutable_evidence(db_session, tmp_path) -> None:
    dataset_path = tmp_path / "admission.csv"
    pd.DataFrame({"value": [1, 2, 3]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session)
    profile = _admitted_profile(db_session, dataset_path)
    request, result = _execute(dataset_path, task, profile)
    service = MvpEvidenceAdmissionService(db_session)

    admission = service.admit(request, result)
    replay = service.admit(request, result)

    assert admission.created is True
    assert replay.created is False
    assert replay.evidence == admission.evidence
    assert len(EvidenceRepository(db_session).list()) == 1
    assert admission.evidence.task_id == task.task_id
    assert admission.evidence.data_profile_id == profile.data_profile_id
    assert admission.evidence.content == {
        "operation": "row_count",
        "parameters": {"columns": []},
        "result": {"row_count": 3},
    }
    assert admission.evidence.provenance.producer_role == "data_explorer"
    assert admission.evidence.provenance.work_reference == result.work_id
    assert admission.evidence.provenance.dataset_reference == str(dataset_path.resolve())
    assert admission.evidence.provenance.data_profile_id == profile.data_profile_id
    assert admission.evidence.provenance.tool_reference == (
        "cognieda.data_explorer.row_count:v1"
    )
    assert admission.evidence.provenance.code_reference is None
    assert admission.planner_outcome.authoritative_refs == [
        f"evidence:{admission.evidence.evidence_id}"
    ]


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("wrong_task", DataAdmissionErrorCode.TASK_MISMATCH),
        ("wrong_profile", DataAdmissionErrorCode.DATA_PROFILE_MISMATCH),
        ("wrong_dataset", DataAdmissionErrorCode.DATASET_MISMATCH),
        ("wrong_source", DataAdmissionErrorCode.INVALID_RESULT),
        ("invalid_payload", DataAdmissionErrorCode.INVALID_RESULT),
    ],
)
def test_lineage_or_payload_mismatch_creates_zero_evidence(
    db_session,
    tmp_path,
    mutation,
    expected_code,
) -> None:
    dataset_path = tmp_path / "mismatch.csv"
    pd.DataFrame({"value": [1, 2, 3]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session)
    profile = _admitted_profile(db_session, dataset_path)
    request, result = _execute(dataset_path, task, profile)

    if mutation == "wrong_task":
        other_task = _persisted_task(db_session, "Different work")
        request = request.model_copy(update={"input": ExecutorInput(task=other_task)})
    elif mutation == "wrong_profile":
        other_profile = _raw_profile(db_session)
        request = request.model_copy(
            update={
                "context": request.context.model_copy(
                    update={"data_profile_id": other_profile.data_profile_id}
                )
            }
        )
    elif mutation == "wrong_dataset":
        other_dataset = tmp_path / "other.csv"
        pd.DataFrame({"value": [1, 2, 3]}).to_csv(other_dataset, index=False)
        request = request.model_copy(
            update={
                "context": request.context.model_copy(
                    update={"dataset_path": str(other_dataset)}
                )
            }
        )
    elif mutation == "wrong_source":
        result = result.model_copy(update={"source_role": "planner"})
    else:
        observation = result.observations[0].model_copy(
            update={"payload": {"bad": object()}}
        )
        result = result.model_copy(update={"observations": [observation]})

    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert exc_info.value.code is expected_code
    assert EvidenceRepository(db_session).list() == []


@pytest.mark.parametrize(
    ("semantic_field", "expected_code"),
    [
        ("objective_id", DataAdmissionErrorCode.TASK_MISMATCH),
        ("kind", DataAdmissionErrorCode.INVALID_RESULT),
        ("instruction", DataAdmissionErrorCode.TASK_MISMATCH),
    ],
)
def test_forged_task_semantics_create_zero_evidence(
    db_session: Session,
    tmp_path: Path,
    semantic_field: str,
    expected_code: DataAdmissionErrorCode,
) -> None:
    dataset_path = tmp_path / f"forged-{semantic_field}.csv"
    pd.DataFrame({"value": [1, 2, 3]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session)
    profile = _admitted_profile(db_session, dataset_path)
    request, result = _execute(dataset_path, task, profile)
    semantic_values = {
        "objective_id": task.objective_id,
        "kind": task.kind,
        "instruction": task.instruction,
    }
    semantic_values[semantic_field] = {
        "objective_id": uuid4(),
        "kind": TaskKind.SCIENTIFIC,
        "instruction": "Different semantic work",
    }[semantic_field]
    forged_task = Task.model_validate(
        {"task_id": task.task_id, "status": task.status, **semantic_values}
    )
    forged_input = request.input.model_copy(update={"task": forged_task})
    forged_request = request.model_copy(update={"input": forged_input})

    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(forged_request, result)

    assert exc_info.value.code is expected_code
    assert EvidenceRepository(db_session).list() == []


def test_scientific_task_cannot_enter_direct_data_evidence_admission(
    db_session: Session,
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "scientific-direct.csv"
    pd.DataFrame({"value": [1, 2, 3]}).to_csv(dataset_path, index=False)
    data_task = _persisted_task(db_session)
    scientific_task = _persisted_task(
        db_session,
        instruction="Test a scientific relationship",
        kind=TaskKind.SCIENTIFIC,
    )
    profile = _admitted_profile(db_session, dataset_path)
    request, result = _execute(dataset_path, data_task, profile)
    scientific_input = request.input.model_copy(update={"task": scientific_task})
    scientific_request = request.model_copy(update={"input": scientific_input})
    scientific_result = result.model_copy(update={"task_id": scientific_task.task_id})

    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(scientific_request, scientific_result)

    assert exc_info.value.code is DataAdmissionErrorCode.INVALID_RESULT
    assert EvidenceRepository(db_session).list() == []


@pytest.mark.parametrize("task_status", [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.FAILED])
def test_non_completed_authoritative_task_creates_zero_evidence(
    db_session, tmp_path, task_status
) -> None:
    dataset_path = tmp_path / "task-status.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session, status=task_status)
    profile = _admitted_profile(db_session, dataset_path)
    request, result = _execute(dataset_path, task, profile)

    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert exc_info.value.code is DataAdmissionErrorCode.TASK_NOT_COMPLETED
    assert EvidenceRepository(db_session).list() == []


def test_failed_and_blocked_work_create_zero_evidence(db_session, tmp_path) -> None:
    dataset_path = tmp_path / "fail-closed.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session)
    profile = _admitted_profile(db_session, dataset_path)
    missing_request, failed_result = _execute(tmp_path / "missing.csv", task, profile)
    blocked_request = ExecutionRequest(
        capability=Capability.DATA_TRANSFORMATION,
        input=ExecutorInput(task=task),
        context=ExecutorContext(
            dataset_path=str(dataset_path), data_profile_id=profile.data_profile_id
        ),
    )
    blocked_result = asyncio.run(DataExplorer().run(blocked_request))
    service = MvpEvidenceAdmissionService(db_session)

    for request, result in (
        (missing_request, failed_result),
        (blocked_request, blocked_result),
    ):
        with pytest.raises(DataAdmissionError) as exc_info:
            service.admit(request, result)
        assert exc_info.value.code is DataAdmissionErrorCode.INVALID_RESULT

    assert EvidenceRepository(db_session).list() == []


def test_existing_profile_reprofiling_can_be_admitted_only_when_metrics_match(
    db_session, tmp_path
) -> None:
    dataset_path = tmp_path / "reprofile.csv"
    pd.DataFrame({"value": [1, 2, None]}).to_csv(dataset_path, index=False)
    candidate = DataExplorer().profile_candidate(str(dataset_path))
    profile = MvpDataProfileAdmissionService(db_session).admit_candidate(
        candidate
    ).data_profile
    task = _persisted_task(db_session, "Reprofile the active dataset")
    request = ExecutionRequest(
        capability=Capability.DATA_PROFILING,
        input=ExecutorInput(task=task),
        context=ExecutorContext(
            dataset_path=str(dataset_path), data_profile_id=profile.data_profile_id
        ),
    )
    result = asyncio.run(DataExplorer().run(request))

    admission = MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert admission.evidence.content["operation"] == "dataset_profile"
    assert admission.evidence.content["result"] == profile.model_dump(
        mode="json", exclude={"data_profile_id"}
    )


def test_changed_dataset_reprofiling_does_not_match_authoritative_profile(
    db_session, tmp_path
) -> None:
    dataset_path = tmp_path / "changed-reprofile.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(dataset_path, index=False)
    candidate = DataExplorer().profile_candidate(str(dataset_path))
    profile = MvpDataProfileAdmissionService(db_session).admit_candidate(
        candidate
    ).data_profile
    pd.DataFrame({"value": [1, 2, 3]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session, "Reprofile changed data")
    request = ExecutionRequest(
        capability=Capability.DATA_PROFILING,
        input=ExecutorInput(task=task),
        context=ExecutorContext(
            dataset_path=str(dataset_path), data_profile_id=profile.data_profile_id
        ),
    )
    result = asyncio.run(DataExplorer().run(request))

    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert exc_info.value.code is DataAdmissionErrorCode.DATASET_MISMATCH
    assert EvidenceRepository(db_session).list() == []


def test_duplicate_work_reference_with_changed_result_fails_closed(db_session, tmp_path) -> None:
    dataset_path = tmp_path / "duplicate.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session)
    profile = _admitted_profile(db_session, dataset_path)
    request, result = _execute(dataset_path, task, profile)
    service = MvpEvidenceAdmissionService(db_session)
    service.admit(request, result)
    observation = result.observations[0].model_copy(update={"payload": {"row_count": 99}})
    conflicting = result.model_copy(update={"observations": [observation]})

    with pytest.raises(DataAdmissionError) as exc_info:
        service.admit(request, conflicting)

    assert exc_info.value.code is DataAdmissionErrorCode.DUPLICATE_WORK_CONFLICT
    assert len(EvidenceRepository(db_session).list()) == 1


def test_initial_profile_admission_is_application_owned_and_does_not_activate(
    db_session, tmp_path
) -> None:
    active_profile = _raw_profile(db_session, row_count=1)
    dataset_path = tmp_path / "initial-profile.csv"
    pd.DataFrame({"value": [1, 2, 3]}).to_csv(dataset_path, index=False)
    candidate = DataExplorer().profile_candidate(str(dataset_path))
    service = MvpDataProfileAdmissionService(db_session)

    admission = service.admit_candidate(candidate)
    replay = service.admit_candidate(candidate)

    assert admission.created is True
    assert replay.created is False
    assert admission.data_profile == candidate.profile
    assert DataProfileRepository(db_session).get_by_id(active_profile.data_profile_id) == (
        active_profile
    )
    assert len(DataProfileRepository(db_session).list()) == 2
    assert "SessionFrame" not in inspect.getsource(MvpDataProfileAdmissionService)


def test_evidence_admission_has_no_assumption_input_or_lookup(db_session, tmp_path) -> None:
    AssumptionRepository(db_session).create(Assumption(text="Planning-only context"))
    dataset_path = tmp_path / "assumption-isolation.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session)
    profile = _admitted_profile(db_session, dataset_path)
    request, result = _execute(dataset_path, task, profile)

    admission = MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert admission.evidence.content["result"] == {"row_count": 1}
    assert "assumption" not in inspect.signature(
        MvpEvidenceAdmissionService.admit
    ).parameters


def test_raw_profile_without_dataset_binding_is_not_evidence_eligible(
    db_session, tmp_path
) -> None:
    dataset_path = tmp_path / "unbound.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(dataset_path, index=False)
    profile = _raw_profile(db_session, row_count=2)
    task = _persisted_task(db_session)
    request, result = _execute(dataset_path, task, profile)

    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert exc_info.value.code is DataAdmissionErrorCode.DATA_PROFILE_MISMATCH
    assert EvidenceRepository(db_session).list() == []


def test_bound_profile_cannot_be_used_for_another_dataset_path(
    db_session, tmp_path
) -> None:
    dataset_a = tmp_path / "dataset-a.csv"
    dataset_b = tmp_path / "dataset-b.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(dataset_a, index=False)
    pd.DataFrame({"value": [8, 9]}).to_csv(dataset_b, index=False)
    profile = _admitted_profile(db_session, dataset_a)
    task = _persisted_task(db_session)
    request, result = _execute(dataset_b, task, profile)

    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert exc_info.value.code is DataAdmissionErrorCode.DATASET_MISMATCH
    assert EvidenceRepository(db_session).list() == []


def test_profile_binding_exact_replay_is_idempotent(db_session, tmp_path) -> None:
    dataset_path = tmp_path / "binding-replay.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset_path, index=False)
    candidate = DataExplorer().profile_candidate(str(dataset_path))
    service = MvpDataProfileAdmissionService(db_session)

    first = service.admit_candidate(candidate)
    replay = service.admit_candidate(candidate)

    assert first.created is True
    assert replay.created is False
    assert replay.data_profile == first.data_profile
    assert replay.dataset_binding == first.dataset_binding
    assert replay.dataset_binding.dataset_digest == candidate.provenance.dataset_digest


def test_profile_identity_with_conflicting_dataset_binding_fails_closed(
    db_session, tmp_path
) -> None:
    dataset_a = tmp_path / "binding-a.csv"
    dataset_b = tmp_path / "binding-b.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(dataset_a, index=False)
    pd.DataFrame({"value": [8, 9]}).to_csv(dataset_b, index=False)
    candidate_a = DataExplorer().profile_candidate(str(dataset_a))
    candidate_b = DataExplorer().profile_candidate(str(dataset_b))
    service = MvpDataProfileAdmissionService(db_session)
    service.admit_candidate(candidate_a)
    conflicting = candidate_b.model_copy(
        update={
            "profile": candidate_b.profile.model_copy(
                update={"data_profile_id": candidate_a.profile.data_profile_id}
            )
        }
    )

    with pytest.raises(DataAdmissionError) as exc_info:
        service.admit_candidate(conflicting)

    assert exc_info.value.code is DataAdmissionErrorCode.DUPLICATE_WORK_CONFLICT
    binding = DataProfileDatasetBindingRepository(db_session).get_by_profile_id(
        candidate_a.profile.data_profile_id
    )
    assert binding is not None
    assert binding.dataset_reference == str(dataset_a.resolve())


def test_same_content_at_different_path_requires_new_profile_admission(
    db_session, tmp_path
) -> None:
    dataset_a = tmp_path / "original.csv"
    dataset_b = tmp_path / "copy.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(dataset_a, index=False)
    dataset_b.write_bytes(dataset_a.read_bytes())
    profile = _admitted_profile(db_session, dataset_a)
    task = _persisted_task(db_session)
    request, result = _execute(dataset_b, task, profile)

    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert exc_info.value.code is DataAdmissionErrorCode.DATASET_MISMATCH
    assert result.provenance is not None
    binding = DataProfileDatasetBindingRepository(db_session).get_by_profile_id(
        profile.data_profile_id
    )
    assert binding is not None
    assert result.provenance.dataset_digest == binding.dataset_digest
    assert EvidenceRepository(db_session).list() == []


def test_same_path_mutation_blocks_analysis_evidence(db_session, tmp_path) -> None:
    dataset_path = tmp_path / "mutated-analysis.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(dataset_path, index=False)
    profile = _admitted_profile(db_session, dataset_path)
    binding = DataProfileDatasetBindingRepository(db_session).get_by_profile_id(
        profile.data_profile_id
    )
    assert binding is not None
    pd.DataFrame({"value": [3, 4]}).to_csv(dataset_path, index=False)
    task = _persisted_task(db_session)
    request, result = _execute(dataset_path, task, profile)

    assert result.provenance is not None
    assert result.provenance.dataset_reference == binding.dataset_reference
    assert result.provenance.dataset_digest != binding.dataset_digest
    with pytest.raises(DataAdmissionError) as exc_info:
        MvpEvidenceAdmissionService(db_session).admit(request, result)

    assert exc_info.value.code is DataAdmissionErrorCode.DATASET_MISMATCH
    assert EvidenceRepository(db_session).list() == []


def test_profile_and_binding_admission_rolls_back_as_one_transaction(
    db_session, tmp_path, monkeypatch
) -> None:
    dataset_path = tmp_path / "atomic-profile.csv"
    pd.DataFrame({"value": [1]}).to_csv(dataset_path, index=False)
    candidate = DataExplorer().profile_candidate(str(dataset_path))

    def reject_binding(_repository, _binding):
        raise RuntimeError("binding storage failed")

    monkeypatch.setattr(DataProfileDatasetBindingRepository, "add", reject_binding)
    with pytest.raises(RuntimeError, match="binding storage failed"):
        MvpDataProfileAdmissionService(db_session).admit_candidate(candidate)

    assert DataProfileRepository(db_session).get_by_id(candidate.profile.data_profile_id) is None
