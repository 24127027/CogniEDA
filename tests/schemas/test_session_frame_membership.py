"""Typed-reference SessionFrame membership contract tests."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from cognieda.schemas import SessionFrameMembership


def test_empty_membership_is_valid_and_deterministic() -> None:
    first = SessionFrameMembership()
    second = SessionFrameMembership()

    assert first == second
    assert first.model_dump() == second.model_dump()
    assert all(value in ((), None) for value in first.model_dump().values())


def test_objective_membership_may_select_one_active_reference() -> None:
    objective_id = uuid4()

    membership = SessionFrameMembership(
        objective_ids=(objective_id,),
        active_objective_id=objective_id,
    )

    assert membership.objective_ids == (objective_id,)
    assert membership.active_objective_id == objective_id


def test_multiple_objective_references_are_structurally_allowed() -> None:
    objective_ids = (uuid4(), uuid4())

    membership = SessionFrameMembership(objective_ids=objective_ids)

    assert membership.objective_ids == objective_ids
    assert membership.active_objective_id is None


def test_active_objective_must_be_a_member() -> None:
    with pytest.raises(ValidationError, match="active_objective_id must occur"):
        SessionFrameMembership(
            objective_ids=(uuid4(),),
            active_objective_id=uuid4(),
        )


def test_data_profile_membership_may_select_one_active_reference() -> None:
    data_profile_id = uuid4()

    membership = SessionFrameMembership(
        data_profile_ids=(data_profile_id,),
        active_data_profile_id=data_profile_id,
    )

    assert membership.data_profile_ids == (data_profile_id,)
    assert membership.active_data_profile_id == data_profile_id


def test_multiple_data_profile_references_are_structurally_allowed() -> None:
    data_profile_ids = (uuid4(), uuid4())

    membership = SessionFrameMembership(data_profile_ids=data_profile_ids)

    assert membership.data_profile_ids == data_profile_ids
    assert membership.active_data_profile_id is None


def test_active_data_profile_must_be_a_member() -> None:
    with pytest.raises(ValidationError, match="active_data_profile_id must occur"):
        SessionFrameMembership(
            data_profile_ids=(uuid4(),),
            active_data_profile_id=uuid4(),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "objective_ids",
        "assumption_ids",
        "task_ids",
        "data_profile_ids",
        "hypothesis_ids",
        "evidence_ids",
        "discovery_ids",
    ],
)
def test_each_membership_collection_rejects_duplicate_uuids(field_name: str) -> None:
    identifier = uuid4()

    with pytest.raises(ValidationError, match=rf"{field_name} rejects duplicate UUIDs"):
        SessionFrameMembership(**{field_name: (identifier, identifier)})


def test_membership_is_immutable() -> None:
    membership = SessionFrameMembership()

    with pytest.raises(ValidationError, match="frozen"):
        membership.task_ids = (uuid4(),)


def test_caller_ordering_is_preserved_for_every_membership_collection() -> None:
    identifiers = {
        field_name: (uuid4(), uuid4())
        for field_name in (
            "objective_ids",
            "assumption_ids",
            "task_ids",
            "data_profile_ids",
            "hypothesis_ids",
            "evidence_ids",
            "discovery_ids",
        )
    }

    membership = SessionFrameMembership(**identifiers)

    for field_name, expected in identifiers.items():
        assert getattr(membership, field_name) == expected


def test_membership_contract_contains_only_typed_uuid_references_and_selectors() -> None:
    expected_annotations = {
        "objective_ids": tuple[UUID, ...],
        "active_objective_id": UUID | None,
        "assumption_ids": tuple[UUID, ...],
        "task_ids": tuple[UUID, ...],
        "data_profile_ids": tuple[UUID, ...],
        "active_data_profile_id": UUID | None,
        "hypothesis_ids": tuple[UUID, ...],
        "evidence_ids": tuple[UUID, ...],
        "discovery_ids": tuple[UUID, ...],
    }

    assert {
        field_name: field.annotation
        for field_name, field in SessionFrameMembership.model_fields.items()
    } == expected_annotations
