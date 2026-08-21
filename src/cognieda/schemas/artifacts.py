"""Core research-state models for CogniEDA."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping
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
    TaskKind,
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


class Objective(ImmutableCogniEDABaseModel):
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

    def with_column_descriptions(
        self,
        descriptions: Mapping[str, str],
    ) -> DataProfile:
        column_names = {column.name for column in self.columns}
        unknown = descriptions.keys() - column_names

        if unknown:
            raise ValueError(f"Unknown columns: {sorted(unknown)}")

        columns = tuple(
            column.model_copy(
                update={"semantic_description": descriptions[column.name]}
            )
            if column.name in descriptions
            else column
            for column in self.columns
        )

        return self.model_copy(update={"columns": columns})


class Assumption(ImmutableCogniEDABaseModel):
    """Planning-only statement; an Assumption is never empirical Evidence."""

    assumption_id: UUID = Field(default_factory=uuid4)
    text: NonEmptyStr


class Task(ImmutableCogniEDABaseModel):
    """Objective-scoped semantic work identity; a Task is not scientific knowledge."""

    task_id: UUID = Field(default_factory=uuid4)
    objective_id: UUID
    kind: TaskKind
    description: NonEmptyStr
    status: TaskStatus = TaskStatus.PENDING

    def semantic_payload(self) -> dict[str, Any]:
        """Return immutable Task definition fields, excluding execution status."""

        return {
            "task_id": str(self.task_id),
            "objective_id": str(self.objective_id),
            "kind": self.kind.value,
            "description": self.description,
        }


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
    # task_id: UUID
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
    """Authoritative typed research state for the single active MVP session."""

    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    discoveries: tuple[Discovery, ...] = ()
    data_profile: DataProfile | None = None

    @model_validator(mode="after")
    def _validate_research_state(self) -> SessionFrame:
        self._check_research_state()
        return self

    def _check_research_state(self) -> None:
        self._reject_duplicate_ids(
            [assumption.assumption_id for assumption in self.assumptions],
            object_name="Assumption",
        )
        self._reject_duplicate_ids(
            [hypothesis.hypothesis_id for hypothesis in self.hypotheses],
            object_name="Hypothesis",
        )
        self._reject_duplicate_ids(
            [evidence.evidence_id for evidence in self.evidences],
            object_name="Evidence",
        )
        self._reject_duplicate_ids(
            [discovery.discovery_id for discovery in self.discoveries],
            object_name="Discovery",
        )

        for evidence in self.evidences:
            if self.data_profile is None:
                raise ValueError("SessionFrame cannot retain Evidence without a DataProfile.")
            if evidence.data_profile_id != self.data_profile.data_profile_id:
                raise ValueError("Evidence must reference the active SessionFrame DataProfile.")

    @staticmethod
    def _reject_duplicate_ids(ids: list[UUID], *, object_name: str) -> None:
        if len(ids) != len(set(ids)):
            raise ValueError(f"SessionFrame rejects duplicate {object_name} IDs.")

    def _validated_copy(self, **updates: object) -> SessionFrame:
        values: dict[str, object] = {
            "objective": self.objective,
            "assumptions": self.assumptions,
            "hypotheses": self.hypotheses,
            "evidences": self.evidences,
            "discoveries": self.discoveries,
            "data_profile": self.data_profile,
        }
        values.update(updates)
        return SessionFrame.model_validate(values)

    def set_objective(self, objective: Objective | None) -> SessionFrame:
        return self._validated_copy(objective=objective)

    def add_assumption(self, assumption: Assumption) -> SessionFrame:
        if any(item.assumption_id == assumption.assumption_id for item in self.assumptions):
            raise ValueError("SessionFrame rejects duplicate Assumption IDs.")
        return self._validated_copy(assumptions=(*self.assumptions, assumption))

    def add_hypothesis(self, hypothesis: Hypothesis) -> SessionFrame:
        if any(item.hypothesis_id == hypothesis.hypothesis_id for item in self.hypotheses):
            raise ValueError("SessionFrame rejects duplicate Hypothesis IDs.")
        return self._validated_copy(hypotheses=(*self.hypotheses, hypothesis))

    def add_evidence(self, evidence: Evidence) -> SessionFrame:
        return self._validated_copy(evidences=(*self.evidences, evidence))

    def add_discovery(self, discovery: Discovery) -> SessionFrame:
        return self._validated_copy(discoveries=(*self.discoveries, discovery))

    def set_data_profile(self, data_profile: DataProfile | None) -> SessionFrame:
        return self._validated_copy(data_profile=data_profile)
