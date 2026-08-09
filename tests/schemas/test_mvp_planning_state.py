"""M1-A executable planning-state contracts."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from schemas import Assumption, Objective, Task, TaskStatus


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
    task = Task(instruction="Count retained customers", status=status)

    assert isinstance(task.task_id, UUID)
    assert task.instruction == "Count retained customers"
    assert task.status is status
    assert task.model_dump().keys() == {"task_id", "instruction", "status"}


def test_task_defaults_to_pending_and_rejects_empty_instruction() -> None:
    assert Task(instruction="Profile the dataset").status is TaskStatus.PENDING

    with pytest.raises(ValidationError):
        Task(instruction="  ")


def test_task_rejects_legacy_executable_fields() -> None:
    with pytest.raises(ValidationError):
        Task(instruction="Profile data", title="Legacy title")
