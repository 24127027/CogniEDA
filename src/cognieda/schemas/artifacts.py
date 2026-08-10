"""Core research-state models for CogniEDA."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, JsonValue, NonNegativeInt, field_validator, model_validator

from cognieda.schemas.common import (
    CogniEDABaseModel,
    ColumnProfile,
    DiscoveryClaim,
    EvidenceProvenance,
    ImmutableCogniEDABaseModel,
    NonEmptyStr,
    ValidityBasis,
    utc_now,
)
from cognieda.schemas.enums import (
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    HypothesisStatus,
    TaskStatus,
    UserDecisionStatus,
    UserDecisionType,
)


class _FrozenJsonDict(dict[str, Any]):
    """Internal mapping that preserves JSON shape while rejecting mutation."""

    @staticmethod
    def _immutable(*_: Any, **__: Any) -> None:
        raise TypeError("Evidence content is immutable.")

    __delitem__ = _immutable
    __ior__ = _immutable  # type: ignore[assignment]
    __setitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable  # type: ignore[assignment]
    setdefault = _immutable
    update = _immutable


class _FrozenJsonList(list[Any]):
    """Internal list that preserves JSON shape while rejecting mutation."""

    @staticmethod
    def _immutable(*_: Any, **__: Any) -> None:
        raise TypeError("Evidence content is immutable.")

    __delitem__ = _immutable
    __iadd__ = _immutable  # type: ignore[assignment]
    __imul__ = _immutable  # type: ignore[assignment]
    __setitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable


class Objective(CogniEDABaseModel):
    """Minimum executable research intent for the active MVP session."""

    objective_id: UUID = Field(default_factory=uuid4)
    text: NonEmptyStr


class DataProfile(ImmutableCogniEDABaseModel):
    """Immutable typed description of the single active MVP dataset."""

    data_profile_id: UUID = Field(default_factory=uuid4)
    row_count: NonNegativeInt
    column_count: NonNegativeInt
    columns: tuple[ColumnProfile, ...]

    @model_validator(mode="after")
    def _column_count_matches_columns(self) -> DataProfile:
        if self.column_count != len(self.columns):
            raise ValueError("column_count must equal the number of ColumnProfile entries.")
        return self


class Assumption(CogniEDABaseModel):
    """Planning-only statement; an Assumption is never empirical Evidence."""

    assumption_id: UUID = Field(default_factory=uuid4)
    text: NonEmptyStr


class Task(ImmutableCogniEDABaseModel):
    """Bounded executable MVP work identity; a Task is not scientific knowledge."""

    task_id: UUID = Field(default_factory=uuid4)
    instruction: NonEmptyStr
    status: TaskStatus = TaskStatus.PENDING


class Hypothesis(CogniEDABaseModel):
    """Atomic test contract created from one terminal analytical Task."""

    hypothesis_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    profile_id: UUID
    statement: NonEmptyStr
    variables: list[NonEmptyStr] = Field(default_factory=list)
    scope: NonEmptyStr
    validation_method: NonEmptyStr
    evidence_expectation: NonEmptyStr
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Evidence(ImmutableCogniEDABaseModel):
    """Immutable structured result linked directly to real MVP work and data state."""

    evidence_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    data_profile_id: UUID
    content: dict[str, JsonValue] = Field(min_length=1)
    provenance: EvidenceProvenance
    artifact_refs: tuple[NonEmptyStr, ...] = ()

    def model_post_init(self, __context: Any) -> None:
        del __context
        object.__setattr__(self, "content", self._freeze_json(self.content))

    @classmethod
    def _freeze_json(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return _FrozenJsonDict({key: cls._freeze_json(item) for key, item in value.items()})
        if isinstance(value, list):
            return _FrozenJsonList(cls._freeze_json(item) for item in value)
        return value

    @field_validator("content", mode="before")
    @classmethod
    def _content_is_native_json(cls, value: Any) -> Any:
        cls._validate_json_value(value, path="content")
        return value

    @classmethod
    def _validate_json_value(cls, value: Any, *, path: str) -> None:
        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float):
            try:
                json.dumps(value, allow_nan=False)
            except ValueError as exc:
                raise ValueError(f"{path} contains a non-finite float.") from exc
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                cls._validate_json_value(item, path=f"{path}[{index}]")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"{path} requires string object keys.")
                cls._validate_json_value(item, path=f"{path}.{key}")
            return
        raise ValueError(f"{path} contains unsupported value type {type(value).__name__}.")

    @model_validator(mode="after")
    def _provenance_matches_data_profile(self) -> Evidence:
        if self.provenance.data_profile_id != self.data_profile_id:
            raise ValueError("Evidence provenance must reference the same DataProfile.")
        return self


class Discovery(ImmutableCogniEDABaseModel):
    """Evidence-bound claim produced from exactly one Hypothesis."""

    discovery_id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    evidence_ids: list[UUID]
    claim: DiscoveryClaim
    epistemic_status: DiscoveryEpistemicStatus
    scope: NonEmptyStr
    validity_basis: ValidityBasis
    lifecycle_state: DiscoveryLifecycleState = DiscoveryLifecycleState.ACTIVE
    review_reasons: list[NonEmptyStr] = Field(default_factory=list)
    flagged_by_evidence_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate_evidence_bound_claim(self) -> Discovery:
        if not self.evidence_ids:
            raise ValueError("Discovery requires at least one Evidence reference.")
        if self.validity_basis.hypothesis_id != self.hypothesis_id:
            raise ValueError("Discovery validity_basis must reference the same Hypothesis.")
        if set(self.validity_basis.evidence_ids) != set(self.evidence_ids):
            raise ValueError("Discovery validity_basis must cover all supporting Evidence.")
        if self.validity_basis.assumptions_excluded_from_inference is not True:
            raise ValueError("Discovery inference must exclude Assumptions.")
        return self


class UserDecision(CogniEDABaseModel):
    """Typed provenance record for a user decision."""

    decision_id: UUID = Field(default_factory=uuid4)
    decision_type: UserDecisionType
    decision: NonEmptyStr
    rationale: NonEmptyStr
    status: UserDecisionStatus = UserDecisionStatus.ACTIVE
    alternatives_considered: list[NonEmptyStr] = Field(default_factory=list)
    related_task_ids: list[UUID] = Field(default_factory=list)
    related_hypothesis_ids: list[UUID] = Field(default_factory=list)
    superseded_by_decision_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SessionFrame(ImmutableCogniEDABaseModel):
    """Cumulative typed FCO-reference history plus explicit active selectors."""

    objective_ids: tuple[UUID, ...] = ()
    active_objective_id: UUID | None = None
    assumption_ids: tuple[UUID, ...] = ()
    task_ids: tuple[UUID, ...] = ()
    data_profile_ids: tuple[UUID, ...] = ()
    active_data_profile_id: UUID | None = None
    evidence_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def _validate_research_state(self) -> SessionFrame:
        for ids, object_name in (
            (self.objective_ids, "Objective"),
            (self.assumption_ids, "Assumption"),
            (self.task_ids, "Task"),
            (self.data_profile_ids, "DataProfile"),
            (self.evidence_ids, "Evidence"),
        ):
            self._reject_duplicate_ids(ids, object_name=object_name)
        if (
            self.active_objective_id is not None
            and self.active_objective_id not in self.objective_ids
        ):
            raise ValueError("active_objective_id must reference an Objective history member.")
        if (
            self.active_data_profile_id is not None
            and self.active_data_profile_id not in self.data_profile_ids
        ):
            raise ValueError(
                "active_data_profile_id must reference a DataProfile history member."
            )
        return self

    @staticmethod
    def _reject_duplicate_ids(ids: tuple[UUID, ...], *, object_name: str) -> None:
        if len(ids) != len(set(ids)):
            raise ValueError(f"SessionFrame rejects duplicate {object_name} IDs.")

    def _validated_copy(self, **updates: object) -> SessionFrame:
        values: dict[str, object] = {
            "objective_ids": self.objective_ids,
            "active_objective_id": self.active_objective_id,
            "assumption_ids": self.assumption_ids,
            "task_ids": self.task_ids,
            "data_profile_ids": self.data_profile_ids,
            "active_data_profile_id": self.active_data_profile_id,
            "evidence_ids": self.evidence_ids,
        }
        values.update(updates)
        return SessionFrame.model_validate(values)

    def add_objective_id(self, objective_id: UUID, *, make_active: bool = True) -> SessionFrame:
        if objective_id in self.objective_ids:
            raise ValueError("SessionFrame rejects duplicate Objective IDs.")
        return self._validated_copy(
            objective_ids=(*self.objective_ids, objective_id),
            active_objective_id=(objective_id if make_active else self.active_objective_id),
        )

    def set_active_objective_id(self, objective_id: UUID | None) -> SessionFrame:
        return self._validated_copy(active_objective_id=objective_id)

    def add_assumption_id(self, assumption_id: UUID) -> SessionFrame:
        if assumption_id in self.assumption_ids:
            raise ValueError("SessionFrame rejects duplicate Assumption IDs.")
        return self._validated_copy(assumption_ids=(*self.assumption_ids, assumption_id))

    def add_task_id(self, task_id: UUID) -> SessionFrame:
        if task_id in self.task_ids:
            raise ValueError("SessionFrame rejects duplicate Task IDs.")
        return self._validated_copy(task_ids=(*self.task_ids, task_id))

    def add_data_profile_id(
        self, data_profile_id: UUID, *, make_active: bool = True
    ) -> SessionFrame:
        if data_profile_id in self.data_profile_ids:
            raise ValueError("SessionFrame rejects duplicate DataProfile IDs.")
        return self._validated_copy(
            data_profile_ids=(*self.data_profile_ids, data_profile_id),
            active_data_profile_id=(
                data_profile_id if make_active else self.active_data_profile_id
            ),
        )

    def set_active_data_profile_id(self, data_profile_id: UUID | None) -> SessionFrame:
        return self._validated_copy(active_data_profile_id=data_profile_id)

    def add_evidence_id(self, evidence_id: UUID) -> SessionFrame:
        if evidence_id in self.evidence_ids:
            raise ValueError("SessionFrame rejects duplicate Evidence IDs.")
        return self._validated_copy(evidence_ids=(*self.evidence_ids, evidence_id))
