"""M1-A executable planning-state contracts."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

import cognieda.schemas as schemas
from cognieda.schemas import Assumption, Objective, Task, TaskKind, TaskStatus


def _task(**overrides: object) -> Task:
    values: dict[str, object] = {
        "objective_id": uuid4(),
        "kind": TaskKind.DATA,
        "instruction": "Count retained customers",
    }
    values.update(overrides)
    return Task.model_validate(values)


def test_objective_has_stable_identity_and_only_requires_text() -> None:
    objective = Objective(text="Understand customer retention")

    assert isinstance(objective.objective_id, UUID)
    assert objective.text == "Understand customer retention"
    assert objective.model_dump().keys() == {"objective_id", "text"}


def test_objective_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        Objective(text="   ")


def test_assumption_is_planning_only_text_with_stable_identity() -> None:
    assumption = Assumption(text="Premium members may retain longer")

    assert isinstance(assumption.assumption_id, UUID)
    assert assumption.text == "Premium members may retain longer"
    assert assumption.model_dump().keys() == {"assumption_id", "text"}


def test_assumption_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        Assumption(text="")


@pytest.mark.parametrize("status", list(TaskStatus))
def test_task_supports_exact_mvp_statuses(status: TaskStatus) -> None:
    task = _task(status=status)

    assert isinstance(task.task_id, UUID)
    assert isinstance(task.objective_id, UUID)
    assert task.kind is TaskKind.DATA
    assert task.instruction == "Count retained customers"
    assert task.status is status
    assert task.model_dump().keys() == {
        "task_id",
        "objective_id",
        "kind",
        "instruction",
        "status",
    }


def test_task_kind_is_exactly_the_canonical_four_kind_taxonomy() -> None:
    assert {kind.name for kind in TaskKind} == {"DATA", "SCIENTIFIC", "GRAPH", "SYNTHESIS"}
    assert {kind.value for kind in TaskKind} == {"data", "scientific", "graph", "synthesis"}
    for legacy_name in ("ANALYTICAL", "ORGANIZING", "REVIEW"):
        assert not hasattr(TaskKind, legacy_name)


@pytest.mark.parametrize("kind", list(TaskKind))
def test_each_canonical_task_kind_is_representable(kind: TaskKind) -> None:
    assert _task(kind=kind).kind is kind


def test_schema_package_exports_one_active_task_fco() -> None:
    assert [name for name in schemas.__all__ if name == "Task"] == ["Task"]
    assert schemas.Task is Task


def test_task_requires_exact_objective_identity_and_canonical_kind() -> None:
    with pytest.raises(ValidationError):
        Task.model_validate({"kind": "data", "instruction": "Profile the dataset"})
    with pytest.raises(ValidationError):
        Task.model_validate(
            {"objective_id": None, "kind": "data", "instruction": "Profile the dataset"}
        )
    with pytest.raises(ValidationError):
        Task.model_validate(
            {"objective_id": uuid4(), "instruction": "Profile the dataset"}
        )
    with pytest.raises(ValidationError):
        Task.model_validate(
            {
                "objective_id": uuid4(),
                "kind": "analytical",
                "instruction": "Profile the dataset",
            }
        )


def test_task_defaults_to_pending_and_rejects_empty_instruction() -> None:
    assert _task(instruction="Profile the dataset").status is TaskStatus.PENDING

    with pytest.raises(ValidationError):
        _task(instruction="  ")


def test_task_rejects_legacy_executable_fields() -> None:
    with pytest.raises(ValidationError):
        _task(instruction="Profile data", title="Legacy title")


@pytest.mark.parametrize(
    "field",
    ["task_id", "objective_id", "kind", "instruction", "status"],
)
def test_task_is_immutable(field: str) -> None:
    task = _task(instruction="Profile data")

    with pytest.raises(ValidationError, match="frozen"):
        setattr(task, field, TaskStatus.RUNNING if field == "status" else "changed")


def test_task_exposes_no_scientific_operationalization_or_dataset_locator_fields() -> None:
    prohibited_fields = {
        "hypothesis",
        "hypothesis_statement",
        "method",
        "validation_method",
        "statistical_test",
        "parameters",
        "decision_rule",
        "random_seed",
        "protocol",
        "protocol_revision",
        "evidence_obligation",
        "evidence_expectation",
        "variables",
        "dataset_path",
        "database_connection",
        "uri",
        "table_location",
    }

    assert prohibited_fields.isdisjoint(Task.model_fields)
