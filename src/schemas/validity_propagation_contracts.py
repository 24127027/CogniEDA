"""Typed, authority-inert contracts for atomic validity propagation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from schemas.canonical import canonical_sha256
from schemas.enums import AuthorizationClass, ValidityEventType, ValiditySourceType

ValidityTargetType = Literal[
    "source",
    "evidence",
    "evaluation",
    "admission_claim",
    "discovery",
    "hypothesis",
    "task",
    "session_frame",
]


class ValidityPropagationCommand(BaseModel):
    """Request data whose authority and source guards must be verified from storage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_type: ValiditySourceType
    source_id: UUID
    event_type: ValidityEventType
    reason: str
    authority_id: UUID
    workspace_id: str
    session_id: str | None = None
    expected_source_state: str
    expected_source_fingerprint: str
    idempotency_key: str
    replacement_id: UUID | None = None
    expected_replacement_fingerprint: str | None = None

    @field_validator(
        "reason",
        "workspace_id",
        "expected_source_state",
        "expected_source_fingerprint",
        "idempotency_key",
    )
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace.")
        return cleaned

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("session_id cannot be empty or whitespace.")
        return cleaned

    @model_validator(mode="after")
    def _validate_replacement_guard(self) -> ValidityPropagationCommand:
        is_supersession = self.event_type in {
            ValidityEventType.EVIDENCE_SUPERSESSION,
            ValidityEventType.DATA_PROFILE_SUPERSESSION,
        }
        if is_supersession:
            if self.replacement_id is None or self.expected_replacement_fingerprint is None:
                raise ValueError(
                    "Supersession requires a persisted replacement ID and expected fingerprint."
                )
            if self.replacement_id == self.source_id:
                raise ValueError("A validity source cannot supersede itself.")
        elif self.replacement_id is not None or self.expected_replacement_fingerprint is not None:
            raise ValueError("Replacement identity is allowed only for supersession events.")
        return self

    def derive_request_fingerprint(
        self,
        *,
        authority_identity: str,
        authority_class: AuthorizationClass,
        authority_purpose: str,
        authority_operation: str,
    ) -> str:
        """Bind the request to independently persisted authority and source guards."""

        return canonical_sha256(
            {
                "source_type": self.source_type.value,
                "source_id": self.source_id,
                "event_type": self.event_type.value,
                "reason": self.reason,
                "authority_id": self.authority_id,
                "authority_identity": authority_identity,
                "authority_class": authority_class.value,
                "authority_purpose": authority_purpose,
                "authority_operation": authority_operation,
                "workspace_id": self.workspace_id,
                "session_id": self.session_id,
                "expected_source_state": self.expected_source_state,
                "expected_source_fingerprint": self.expected_source_fingerprint,
                "idempotency_key": self.idempotency_key,
                "replacement_id": self.replacement_id,
                "expected_replacement_fingerprint": self.expected_replacement_fingerprint,
            }
        )


class ValidityTargetTransition(BaseModel):
    """One closed, deterministic write in a validity propagation plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_type: ValidityTargetType
    target_id: UUID
    expected_state: str
    target_state: str
    expected_fingerprint: str


class ValidityPropagationPlan(BaseModel):
    """Frozen detached description of the complete applicable write set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    idempotency_key: str
    request_fingerprint: str
    source_type: ValiditySourceType
    source_id: UUID
    source_fingerprint: str
    expected_source_state: str
    source_post_state: str
    event_type: ValidityEventType
    reason: str
    authority_id: UUID
    authority_identity: str
    authority_class: AuthorizationClass
    authority_purpose: str
    authority_operation: str
    workspace_id: str
    session_id: str | None = None
    replacement_id: UUID | None = None
    replacement_fingerprint: str | None = None
    transitions: tuple[ValidityTargetTransition, ...] = ()
    plan_fingerprint: str = ""

    def derive_fingerprint(self) -> str:
        """Hash every plan field except the fingerprint itself."""

        payload: dict[str, Any] = self.model_dump(
            mode="python",
            exclude={"plan_fingerprint"},
        )
        return canonical_sha256(payload)


class ValidityPropagationResult(BaseModel):
    """Committed or exactly replayed validity propagation result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    idempotency_key: str
    plan_fingerprint: str
    replayed: bool
    affected_evidence_count: int
    affected_evaluation_count: int
    affected_admission_claim_count: int
    affected_discovery_count: int
    affected_hypothesis_count: int
    affected_task_count: int
    affected_session_frame_count: int
    committed_at: datetime
