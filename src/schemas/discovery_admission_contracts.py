"""Typed contracts for Package 3 Discovery Admission Governance."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from schemas.common import ImmutableCogniEDABaseModel, NonEmptyStr
from schemas.enums import (
    AuthorizationClass,
    DiscoveryEpistemicStatus,
    EvaluationControlState,
    GovernanceDecisionOutcome,
    HypothesisStatus,
    TaskLifecycleState,
)
from schemas.specialist_contracts import DecisionRuleSnapshot, MethodParameterSnapshot


class AuthenticatedPrincipal(ImmutableCogniEDABaseModel):
    """Authenticated identity provided by an authentication subsystem."""

    authentication_context_id: NonEmptyStr
    principal_id: NonEmptyStr
    workspace_id: NonEmptyStr
    session_id: NonEmptyStr
    authenticated_at: datetime


class GovernanceAuthority(ImmutableCogniEDABaseModel):
    """Durable, independently issued actor authority used to record one decision."""

    authority_id: UUID
    actor_identity: NonEmptyStr
    authority_class: AuthorizationClass
    workspace_id: NonEmptyStr
    session_id: str | None = None
    purpose: NonEmptyStr
    operation_type: NonEmptyStr
    issued_by: NonEmptyStr
    issued_at: datetime
    expires_at: datetime | None = None
    authority_fingerprint: NonEmptyStr


class ProposalAuthority(ImmutableCogniEDABaseModel):
    """Immutable identity and provenance binding for a persisted evaluation proposal."""

    evaluation_id: UUID
    evaluation_key: NonEmptyStr
    hypothesis_id: UUID
    source_task_id: UUID
    profile_id: UUID
    proposal_digest: NonEmptyStr
    bundle_digest: NonEmptyStr
    evidence_set_digest: NonEmptyStr
    manifest_digest: NonEmptyStr
    exact_evidence_ids: tuple[UUID, ...]
    exact_analysis_frame_ids: tuple[UUID, ...]
    proposal_contract_version: Literal["1.0"] = "1.0"
    serialized_proposal_identity: NonEmptyStr
    evaluation_attempt_number: int = Field(ge=1)
    evaluation_owner: NonEmptyStr
    evaluation_fencing_epoch: int = Field(ge=1)
    evaluation_created_at: datetime


class GovernanceDecision(ImmutableCogniEDABaseModel):
    """Durable provenance for an authorized governance decision."""

    decision_id: UUID
    authority_id: UUID
    evaluation_id: UUID
    evaluation_key: NonEmptyStr
    hypothesis_id: UUID
    task_id: UUID
    proposal_digest: NonEmptyStr
    bundle_digest: NonEmptyStr
    evidence_set_digest: NonEmptyStr
    decision: GovernanceDecisionOutcome
    actor: NonEmptyStr
    actor_authority_type: AuthorizationClass
    workspace_id: NonEmptyStr
    session_id: str | None = None
    purpose: NonEmptyStr
    operation_type: NonEmptyStr
    decision_timestamp: datetime
    reason: str | None = None
    decision_fingerprint: NonEmptyStr
    consumed: bool = False
    consumed_at: datetime | None = None
    consumed_by: str | None = None


class DiscoveryClaimSnapshot(ImmutableCogniEDABaseModel):
    """Deep-frozen, exact scientific claim copied from the persisted proposal."""

    statement: NonEmptyStr
    scope: NonEmptyStr
    conditions: tuple[NonEmptyStr, ...] = ()
    result: str | None = None


class ValidityBasisSnapshot(ImmutableCogniEDABaseModel):
    """Deep-frozen, exact validity basis copied from the persisted proposal."""

    data_profile_id: UUID
    analysis_frame_refs: tuple[NonEmptyStr, ...]
    hypothesis_id: UUID
    evidence_ids: tuple[UUID, ...]
    method: NonEmptyStr
    parameters: tuple[MethodParameterSnapshot, ...] = ()
    code_reference: str | None = None
    environment_reference: str | None = None
    decision_rule: DecisionRuleSnapshot
    strength: str | None = None
    uncertainty: str | None = None
    assumptions_excluded_from_inference: Literal[True] = True
    invalidators: tuple[NonEmptyStr, ...] = ()


DEFAULT_FUTURE_ATOMIC_WRITE_SET = (
    "discovery_insert",
    "hypothesis_evaluated_transition",
    "terminal_task_completed_transition",
    "evaluation_control_committed_transition",
    "admission_claim_committed_transition",
    "authorization_decision_consumed_transition",
    "conclusion_session_frame_insert",
)


class FutureAtomicWriteSet(ImmutableCogniEDABaseModel):
    """Operations required for the future Package 4 cutover transaction."""

    write_operations: tuple[str, ...] = Field(default=DEFAULT_FUTURE_ATOMIC_WRITE_SET)


class DiscoveryAdmissionPlan(ImmutableCogniEDABaseModel):
    """Detached, deep-frozen plan for future atomic Discovery admission cutover."""

    contract_version: Literal["discovery-admission/v1"] = "discovery-admission/v1"
    authorization_decision_id: UUID
    authorization_fingerprint: NonEmptyStr
    authorization_authority_id: UUID
    authorization_actor: NonEmptyStr
    authorization_class: AuthorizationClass
    authorization_workspace_id: NonEmptyStr
    authorization_session_id: str | None = None
    authorization_purpose: NonEmptyStr
    authorization_operation_type: NonEmptyStr
    evaluation_id: UUID
    evaluation_key: NonEmptyStr
    evaluation_attempt_number: int = Field(ge=1)
    evaluation_owner: NonEmptyStr
    evaluation_fencing_epoch: int = Field(ge=1)
    proposal_digest: NonEmptyStr
    bundle_digest: NonEmptyStr
    evidence_set_digest: NonEmptyStr
    bundle_manifest_digest: NonEmptyStr
    hypothesis_id: UUID
    source_task_id: UUID
    profile_id: UUID
    evidence_ids: tuple[UUID, ...]
    analysis_frame_ids: tuple[UUID, ...]
    proposed_claim: DiscoveryClaimSnapshot
    epistemic_status: DiscoveryEpistemicStatus
    scope: NonEmptyStr
    validity_basis: ValidityBasisSnapshot
    uncertainty: str | None = None
    limitations: tuple[NonEmptyStr, ...] = ()
    proposal_contract_version: Literal["1.0"] = "1.0"
    expected_evaluation_state: Literal[EvaluationControlState.PROPOSAL_READY] = (
        EvaluationControlState.PROPOSAL_READY
    )
    expected_hypothesis_state: Literal[HypothesisStatus.READY_FOR_EVALUATION] = (
        HypothesisStatus.READY_FOR_EVALUATION
    )
    expected_task_state: Literal[TaskLifecycleState.ACTIVE] = TaskLifecycleState.ACTIVE
    expected_discovery_absent: Literal[True] = True
    deterministic_discovery_id: UUID
    admission_fingerprint: NonEmptyStr
    future_atomic_write_set: FutureAtomicWriteSet = Field(default_factory=FutureAtomicWriteSet)
