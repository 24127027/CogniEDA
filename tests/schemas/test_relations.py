"""Unit tests for Objective-Hypothesis semantic graph relation contracts."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

import cognieda.schemas as schemas
from cognieda.schemas import (
    Discovery,
    Evidence,
    FirstClassObjectType,
    Hypothesis,
    ObjectiveHypothesisRelation,
    ObjectiveHypothesisRelationType,
)


def test_relation_type_is_closed_canonical_vocabulary() -> None:
    """ObjectiveHypothesisRelationType is a closed vocabulary with exact semantics."""
    expected_members = {"FORMULATED_FOR", "BEARS_ON"}
    assert set(ObjectiveHypothesisRelationType.__members__.keys()) == expected_members
    assert len(ObjectiveHypothesisRelationType) == 2
    assert ObjectiveHypothesisRelationType.FORMULATED_FOR.value == "formulated_for"
    assert ObjectiveHypothesisRelationType.BEARS_ON.value == "bears_on"


def test_relation_is_immutable_and_structurally_typed() -> None:
    """ObjectiveHypothesisRelation is immutable and enforces strict structural typing."""
    objective_id = uuid4()
    hypothesis_id = uuid4()

    relation = ObjectiveHypothesisRelation(
        objective_id=objective_id,
        hypothesis_id=hypothesis_id,
        relation_type=ObjectiveHypothesisRelationType.FORMULATED_FOR,
    )

    assert relation.objective_id == objective_id
    assert relation.hypothesis_id == hypothesis_id
    assert relation.relation_type is ObjectiveHypothesisRelationType.FORMULATED_FOR

    with pytest.raises(ValidationError, match="frozen"):
        setattr(relation, "relation_type", ObjectiveHypothesisRelationType.BEARS_ON)

    with pytest.raises(ValidationError, match="frozen"):
        setattr(relation, "objective_id", uuid4())


def test_relation_rejects_extra_fields_and_unsupported_properties() -> None:
    """Relation contract strictly forbids scores, embeddings, prose, metadata, etc."""
    objective_id = uuid4()
    hypothesis_id = uuid4()

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ObjectiveHypothesisRelation.model_validate(
            {
                "objective_id": str(objective_id),
                "hypothesis_id": str(hypothesis_id),
                "relation_type": "formulated_for",
                "confidence": 0.95,
            }
        )

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ObjectiveHypothesisRelation.model_validate(
            {
                "objective_id": str(objective_id),
                "hypothesis_id": str(hypothesis_id),
                "relation_type": "bears_on",
                "rationale": "Relevant to churn",
            }
        )


def test_relation_stores_identities_without_embedded_fco_objects() -> None:
    """Relation stores only Objective and Hypothesis UUID identities, not full embedded FCOs."""
    assert set(ObjectiveHypothesisRelation.model_fields.keys()) == {
        "objective_id",
        "hypothesis_id",
        "relation_type",
    }
    assert ObjectiveHypothesisRelation.model_fields["objective_id"].annotation is UUID
    assert ObjectiveHypothesisRelation.model_fields["hypothesis_id"].annotation is UUID
    assert (
        ObjectiveHypothesisRelation.model_fields["relation_type"].annotation
        is ObjectiveHypothesisRelationType
    )


def test_hypothesis_has_no_objective_ownership_or_membership_fields() -> None:
    """Hypothesis scientific identity remains independent of Objective ownership."""
    prohibited_fields = {
        "objective",
        "objectives",
        "objective_id",
        "objective_ids",
        "primary_objective_id",
        "related_objective_ids",
    }
    assert prohibited_fields.isdisjoint(Hypothesis.model_fields)


def test_evidence_and_discovery_have_no_objective_membership_fields() -> None:
    """Evidence and Discovery scientific validity remains grounded in lineage."""
    prohibited_fields = {
        "objective",
        "objectives",
        "objective_id",
        "objective_ids",
        "primary_objective_id",
        "related_objective_ids",
    }
    assert prohibited_fields.isdisjoint(Evidence.model_fields)
    assert prohibited_fields.isdisjoint(Discovery.model_fields)


def test_relation_contract_exported_on_schema_surface() -> None:
    """ObjectiveHypothesisRelation and its enum type are exported in cognieda.schemas."""
    assert "ObjectiveHypothesisRelation" in schemas.__all__
    assert "ObjectiveHypothesisRelationType" in schemas.__all__
    assert schemas.ObjectiveHypothesisRelation is ObjectiveHypothesisRelation
    assert schemas.ObjectiveHypothesisRelationType is ObjectiveHypothesisRelationType


def test_first_class_object_set_remains_exactly_eight() -> None:
    """FirstClassObjectType contains exactly the eight canonical FCOs."""
    assert len(FirstClassObjectType) == 8
    assert {fco.value for fco in FirstClassObjectType} == {
        "objective",
        "data_profile",
        "assumption",
        "task",
        "hypothesis",
        "evidence",
        "discovery",
        "session_frame",
    }


def test_relation_is_explicitly_not_an_fco_or_kg_node() -> None:
    """ObjectiveHypothesisRelation is a typed edge contract, not a ninth FCO or a fifth KG node."""
    assert "OBJECTIVE_HYPOTHESIS_RELATION" not in FirstClassObjectType.__members__
    assert "RELATION" not in FirstClassObjectType.__members__
    assert "EDGE" not in FirstClassObjectType.__members__

    # Knowledge Graph node types are exactly Objective, Hypothesis, Evidence, Discovery
    kg_nodes = {
        FirstClassObjectType.OBJECTIVE,
        FirstClassObjectType.HYPOTHESIS,
        FirstClassObjectType.EVIDENCE,
        FirstClassObjectType.DISCOVERY,
    }
    assert len(kg_nodes) == 4


def test_relation_string_coercion_and_serialization() -> None:
    """Relation accepts valid UUID and enum strings and roundtrips to dict / JSON."""
    objective_id = uuid4()
    hypothesis_id = uuid4()

    relation = ObjectiveHypothesisRelation.model_validate(
        {
            "objective_id": str(objective_id),
            "hypothesis_id": str(hypothesis_id),
            "relation_type": "bears_on",
        }
    )
    assert relation.objective_id == objective_id
    assert relation.hypothesis_id == hypothesis_id
    assert relation.relation_type is ObjectiveHypothesisRelationType.BEARS_ON

    dumped = relation.model_dump()
    assert dumped == {
        "objective_id": objective_id,
        "hypothesis_id": hypothesis_id,
        "relation_type": ObjectiveHypothesisRelationType.BEARS_ON,
    }
