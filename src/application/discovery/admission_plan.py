"""Deterministic, side-effect-free Discovery admission plan construction."""

from __future__ import annotations

from uuid import UUID, uuid5

from sqlmodel import Session

from application.governance import (
    DiscoveryAdmissionGovernanceService,
    ProposalAuthorizationError,
)
from db.models import EvaluationControlRecord
from schemas.canonical import canonical_sha256
from schemas.discovery import (
    DiscoveryAdmissionPlan,
    DiscoveryClaimSnapshot,
    ValidityBasisSnapshot,
)
from schemas.evaluation import (
    DecisionRuleSnapshot,
    DiscoveryProposal,
    MethodParameterSnapshot,
)

DISCOVERY_ADMISSION_NAMESPACE = UUID("2b8f42e2-65a8-4f10-9831-d85c4908079f")
DISCOVERY_ADMISSION_CONTRACT_VERSION = "discovery-admission/v1"

__all__ = [
    "DISCOVERY_ADMISSION_CONTRACT_VERSION",
    "DISCOVERY_ADMISSION_NAMESPACE",
    "build_discovery_admission_plan",
    "compute_admission_fingerprint",
    "generate_deterministic_discovery_id",
]


def generate_deterministic_discovery_id(
    hypothesis_id: UUID,
    proposal_digest: str,
    *,
    contract_version: str = DISCOVERY_ADMISSION_CONTRACT_VERSION,
) -> UUID:
    """Derive the durable Discovery ID from exact proposal authority."""

    seed = f"{contract_version}:{hypothesis_id}:{proposal_digest}"
    return uuid5(DISCOVERY_ADMISSION_NAMESPACE, seed)


def compute_admission_fingerprint(plan: DiscoveryAdmissionPlan) -> str:
    """Fingerprint every admission-plan field except the fingerprint itself."""

    return canonical_sha256(plan.model_dump(mode="python", exclude={"admission_fingerprint"}))


def build_discovery_admission_plan(
    session: Session,
    evaluation_id: UUID,
    decision_id: UUID,
    *,
    workspace_id: str,
    session_id: str | None = None,
) -> DiscoveryAdmissionPlan:
    """Build a deterministic, detached Discovery admission plan without mutating state."""

    governance_service = DiscoveryAdmissionGovernanceService(
        session,
        workspace_id=workspace_id,
        session_id=session_id,
    )
    authority, decision_record = governance_service.verify_authorization(
        evaluation_id,
        decision_id,
    )
    evaluation_record = session.get(EvaluationControlRecord, evaluation_id)
    if evaluation_record is None or not evaluation_record.serialized_proposal:
        raise ProposalAuthorizationError("Evaluation control has no persisted proposal.")
    try:
        proposal = DiscoveryProposal.model_validate(evaluation_record.serialized_proposal)
    except ValueError as exc:
        raise ProposalAuthorizationError("Persisted proposal is invalid.") from exc
    if proposal.model_dump(mode="json") != evaluation_record.serialized_proposal:
        raise ProposalAuthorizationError(
            "Persisted proposal is not the exact canonical serialized proposal."
        )

    deterministic_discovery_id = generate_deterministic_discovery_id(
        hypothesis_id=authority.hypothesis_id,
        proposal_digest=authority.proposal_digest,
    )
    claim = DiscoveryClaimSnapshot(
        statement=proposal.claim.statement,
        scope=proposal.claim.scope,
        conditions=tuple(proposal.claim.conditions),
        result=proposal.claim.result,
    )
    basis = ValidityBasisSnapshot(
        data_profile_id=proposal.validity_basis.data_profile_id,
        analysis_frame_refs=tuple(proposal.validity_basis.analysis_frame_refs),
        hypothesis_id=proposal.validity_basis.hypothesis_id,
        evidence_ids=tuple(proposal.validity_basis.evidence_ids),
        method=proposal.validity_basis.method,
        parameters=tuple(
            MethodParameterSnapshot(name=parameter.name, value=parameter.value)
            for parameter in proposal.validity_basis.parameters
        ),
        code_reference=proposal.validity_basis.code_reference,
        environment_reference=proposal.validity_basis.environment_reference,
        decision_rule=DecisionRuleSnapshot.from_domain(
            proposal.validity_basis.decision_rule
        ),
        strength=proposal.validity_basis.strength,
        uncertainty=proposal.validity_basis.uncertainty,
        assumptions_excluded_from_inference=True,
        invalidators=tuple(proposal.validity_basis.invalidators),
    )
    unsigned = DiscoveryAdmissionPlan(
        authorization_decision_id=decision_record.decision_id,
        authorization_fingerprint=decision_record.decision_fingerprint,
        authorization_authority_id=decision_record.authority_id,
        authorization_actor=decision_record.actor,
        authorization_class=decision_record.actor_authority_type,
        authorization_workspace_id=decision_record.workspace_id,
        authorization_session_id=decision_record.session_id,
        authorization_purpose=decision_record.purpose,
        authorization_operation_type=decision_record.operation_type,
        evaluation_id=authority.evaluation_id,
        evaluation_key=authority.evaluation_key,
        evaluation_attempt_number=authority.evaluation_attempt_number,
        evaluation_owner=authority.evaluation_owner,
        evaluation_fencing_epoch=authority.evaluation_fencing_epoch,
        proposal_digest=authority.proposal_digest,
        bundle_digest=authority.bundle_digest,
        evidence_set_digest=authority.evidence_set_digest,
        bundle_manifest_digest=authority.manifest_digest,
        hypothesis_id=authority.hypothesis_id,
        source_task_id=authority.source_task_id,
        profile_id=authority.profile_id,
        evidence_ids=authority.exact_evidence_ids,
        analysis_frame_ids=authority.exact_analysis_frame_ids,
        proposed_claim=claim,
        epistemic_status=proposal.epistemic_status,
        scope=proposal.scope,
        validity_basis=basis,
        uncertainty=proposal.validity_basis.uncertainty,
        limitations=tuple(proposal.limitations),
        deterministic_discovery_id=deterministic_discovery_id,
        admission_fingerprint="0" * 64,
    )
    plan = unsigned.model_copy(
        update={"admission_fingerprint": compute_admission_fingerprint(unsigned)}
    )

    final_authority, final_decision = governance_service.verify_authorization(
        evaluation_id,
        decision_id,
    )
    if (
        final_authority != authority
        or final_decision.decision_fingerprint != decision_record.decision_fingerprint
    ):
        raise ProposalAuthorizationError(
            "Durable authority changed before admission-plan construction completed."
        )
    if compute_admission_fingerprint(plan) != plan.admission_fingerprint:
        raise ProposalAuthorizationError("Admission plan fingerprint is not self-consistent.")
    return plan
