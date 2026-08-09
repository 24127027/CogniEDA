"""M1-A typed DataProfile contracts."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from cognieda.schemas import (
    ColumnProfile,
    ContinuousColumnSummary,
    DataProfile,
    DiscreteColumnSummary,
    DiscreteValueCount,
    VariableType,
)


def _continuous_column() -> ColumnProfile:
    return ColumnProfile(
        name="amount",
        dtype="float64",
        variable_type=VariableType.CONTINUOUS,
        distinct_count=3,
        missing_count=1,
        summary=ContinuousColumnSummary(
            min=1.0,
            max=3.0,
            mean=2.0,
            median=2.0,
            std=0.8,
            p25=1.5,
            p75=2.5,
        ),
    )


def _discrete_column() -> ColumnProfile:
    return ColumnProfile(
        name="segment",
        dtype="object",
        variable_type=VariableType.DISCRETE,
        distinct_count=2,
        missing_count=0,
        summary=DiscreteColumnSummary(
            value_counts=(
                DiscreteValueCount(value="premium", count=2),
                DiscreteValueCount(value="standard", count=1),
            )
        ),
    )


def test_data_profile_has_stable_identity_ordered_columns_and_json_serialization() -> None:
    columns = (_discrete_column(), _continuous_column())
    profile = DataProfile(row_count=4, column_count=2, columns=columns)

    assert isinstance(profile.data_profile_id, UUID)
    assert [column.name for column in profile.columns] == ["segment", "amount"]
    assert profile.model_dump(mode="json")["columns"][0]["summary"]["value_counts"] == [
        {"value": "premium", "count": 2},
        {"value": "standard", "count": 1},
    ]


def test_data_profile_and_nested_columns_are_immutable() -> None:
    profile = DataProfile(row_count=4, column_count=1, columns=(_continuous_column(),))

    with pytest.raises(ValidationError):
        profile.row_count = 5
    with pytest.raises(ValidationError):
        profile.columns[0].name = "changed"


def test_data_profile_rejects_column_count_mismatch() -> None:
    with pytest.raises(ValidationError, match="column_count"):
        DataProfile(row_count=1, column_count=0, columns=(_continuous_column(),))


def test_column_profile_rejects_summary_for_wrong_variable_type() -> None:
    with pytest.raises(ValidationError, match="CONTINUOUS"):
        ColumnProfile(
            name="amount",
            dtype="float64",
            variable_type=VariableType.CONTINUOUS,
            distinct_count=2,
            missing_count=0,
            summary=DiscreteColumnSummary(value_counts=()),
        )


def test_discrete_summary_requires_one_bounded_representation() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        DiscreteColumnSummary()
    with pytest.raises(ValidationError, match="exactly one"):
        DiscreteColumnSummary(value_counts=(), top_values=(DiscreteValueCount(value="a", count=1),))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["min", "max", "mean", "median", "std", "p25", "p75"])
def test_continuous_summary_rejects_non_finite_statistics(
    field: str,
    value: float,
) -> None:
    with pytest.raises(ValidationError, match="must be finite"):
        ContinuousColumnSummary(**{field: value})
