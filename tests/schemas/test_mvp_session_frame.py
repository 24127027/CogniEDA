"""SessionFrame cumulative-reference identity and active-selector invariants."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from cognieda.schemas.artifacts import SessionFrame


def test_session_frame_contains_only_typed_fco_references_and_active_selectors() -> None:
    objective_ids = (uuid4(), uuid4())
    assumption_ids = (uuid4(), uuid4())
    task_ids = (uuid4(), uuid4())
    data_profile_ids = (uuid4(), uuid4())
    evidence_ids = (uuid4(), uuid4())

    frame = SessionFrame(
        objective_ids=objective_ids,
        active_objective_id=objective_ids[-1],
        assumption_ids=assumption_ids,
        task_ids=task_ids,
        data_profile_ids=data_profile_ids,
        active_data_profile_id=data_profile_ids[-1],
        evidence_ids=evidence_ids,
    )

    assert frame.objective_ids == objective_ids
    assert frame.active_objective_id == objective_ids[-1]
    assert frame.data_profile_ids == data_profile_ids
    assert frame.active_data_profile_id == data_profile_ids[-1]
    assert all(isinstance(item, UUID) for item in frame.task_ids)
    assert set(SessionFrame.model_fields) == {
        "objective_ids",
        "active_objective_id",
        "assumption_ids",
        "task_ids",
        "data_profile_ids",
        "active_data_profile_id",
        "evidence_ids",
    }


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("objective_ids", "Objective"),
        ("assumption_ids", "Assumption"),
        ("task_ids", "Task"),
        ("data_profile_ids", "DataProfile"),
        ("evidence_ids", "Evidence"),
    ],
)
def test_session_frame_rejects_duplicate_historical_reference_ids(
    field: str, message: str
) -> None:
    object_id = uuid4()

    with pytest.raises(ValidationError, match=message):
        SessionFrame(**{field: (object_id, object_id)})


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("active_objective_id", "Objective history member"),
        ("active_data_profile_id", "DataProfile history member"),
    ],
)
def test_active_selector_must_reference_historical_membership(
    field: str, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        SessionFrame(**{field: uuid4()})


def test_reference_successors_preserve_cumulative_history_and_active_selection() -> None:
    objective_ids = (uuid4(), uuid4())
    profile_ids = (uuid4(), uuid4())
    assumption_id = uuid4()
    task_id = uuid4()
    evidence_id = uuid4()

    initial = SessionFrame()
    frame = initial.add_objective_id(objective_ids[0])
    frame = frame.add_objective_id(objective_ids[1])
    frame = frame.add_assumption_id(assumption_id)
    frame = frame.add_task_id(task_id)
    frame = frame.add_data_profile_id(profile_ids[0])
    frame = frame.add_data_profile_id(profile_ids[1])
    frame = frame.add_evidence_id(evidence_id)
    switched = frame.set_active_objective_id(objective_ids[0]).set_active_data_profile_id(
        profile_ids[0]
    )

    assert initial == SessionFrame()
    assert frame.objective_ids == objective_ids
    assert frame.active_objective_id == objective_ids[1]
    assert frame.data_profile_ids == profile_ids
    assert frame.active_data_profile_id == profile_ids[1]
    assert switched.objective_ids == objective_ids
    assert switched.data_profile_ids == profile_ids
    assert switched.assumption_ids == (assumption_id,)
    assert switched.task_ids == (task_id,)
    assert switched.evidence_ids == (evidence_id,)
    assert not hasattr(switched, "objectives")
    assert not hasattr(switched, "data_profiles")


@pytest.mark.parametrize(
    ("method_name", "object_id", "message"),
    [
        ("add_objective_id", uuid4(), "Objective"),
        ("add_assumption_id", uuid4(), "Assumption"),
        ("add_task_id", uuid4(), "Task"),
        ("add_data_profile_id", uuid4(), "DataProfile"),
        ("add_evidence_id", uuid4(), "Evidence"),
    ],
)
def test_reference_successors_reject_duplicates(
    method_name: str, object_id: UUID, message: str
) -> None:
    method = getattr(SessionFrame(), method_name)
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
