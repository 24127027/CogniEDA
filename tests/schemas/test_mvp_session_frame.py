"""SessionFrame reference-manifest identity and ordering invariants."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from cognieda.schemas.artifacts import SessionFrame


def test_session_frame_contains_only_typed_fco_references() -> None:
    objective_id = uuid4()
    assumption_ids = (uuid4(), uuid4())
    task_ids = (uuid4(), uuid4())
    evidence_ids = (uuid4(), uuid4())
    data_profile_id = uuid4()

    frame = SessionFrame(
        objective_id=objective_id,
        assumption_ids=assumption_ids,
        task_ids=task_ids,
        evidence_ids=evidence_ids,
        data_profile_id=data_profile_id,
    )

    assert frame.objective_id == objective_id
    assert frame.assumption_ids == assumption_ids
    assert frame.task_ids == task_ids
    assert frame.evidence_ids == evidence_ids
    assert frame.data_profile_id == data_profile_id
    assert all(isinstance(item, UUID) for item in frame.task_ids)
    assert set(SessionFrame.model_fields) == {
        "objective_id",
        "assumption_ids",
        "task_ids",
        "evidence_ids",
        "data_profile_id",
    }


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("assumption_ids", "Assumption"),
        ("task_ids", "Task"),
        ("evidence_ids", "Evidence"),
    ],
)
def test_session_frame_rejects_duplicate_reference_ids(field: str, message: str) -> None:
    object_id = uuid4()

    with pytest.raises(ValidationError, match=message):
        SessionFrame(**{field: (object_id, object_id)})


def test_reference_successors_preserve_order_and_do_not_materialize_authority() -> None:
    objective_id = uuid4()
    assumption_id = uuid4()
    first_task_id = uuid4()
    second_task_id = uuid4()
    evidence_id = uuid4()
    profile_id = uuid4()

    initial = SessionFrame()
    frame = initial.set_objective_id(objective_id)
    frame = frame.add_assumption_id(assumption_id)
    frame = frame.add_task_id(first_task_id)
    frame = frame.add_task_id(second_task_id)
    frame = frame.set_data_profile_id(profile_id)
    frame = frame.add_evidence_id(evidence_id)

    assert initial == SessionFrame()
    assert frame.task_ids == (first_task_id, second_task_id)
    assert frame.evidence_ids == (evidence_id,)
    assert not hasattr(frame, "tasks")
    assert not hasattr(frame, "evidences")


@pytest.mark.parametrize(
    ("method_name", "object_id", "message"),
    [
        ("add_assumption_id", uuid4(), "Assumption"),
        ("add_task_id", uuid4(), "Task"),
        ("add_evidence_id", uuid4(), "Evidence"),
    ],
)
def test_reference_successors_reject_duplicates(
    method_name: str, object_id: UUID, message: str
) -> None:
    frame = SessionFrame()
    method = getattr(frame, method_name)
    frame = method(object_id)

    with pytest.raises(ValueError, match=message):
        getattr(frame, method_name)(object_id)


def test_session_frame_membership_does_not_manufacture_validity() -> None:
    frame = SessionFrame(evidence_ids=(uuid4(),))

    assert len(frame.evidence_ids) == 1
    assert "valid" not in SessionFrame.model_fields
    assert "eligible" not in SessionFrame.model_fields


def test_session_frame_is_immutable_and_has_no_conversation_or_pydanticai_dependency() -> None:
    import cognieda.schemas.artifacts as artifacts_module

    frame = SessionFrame(task_ids=(uuid4(),))

    with pytest.raises(ValidationError, match="frozen"):
        frame.task_ids = ()
    source = inspect.getsource(artifacts_module)
    assert "conversation_history" not in SessionFrame.model_fields
    assert "ModelMessage" not in source
    assert "pydantic_ai" not in source
