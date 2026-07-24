"""Durable authorization and read-only planning for future Discovery admission."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4, uuid5

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from application.orchestrator.synthesis_bundle import (
    SynthesisBundleError,
    build_synthesis_bundle,
    compute_evaluation_key,
    compute_evidence_set_digest,
)
from db.models import (
    DiscoveryRecord,
    EvaluationControlRecord,
    GovernanceAuthorityRecord,
    ProposalDecisionRecord,
    utc_now,
)
from repositories.discovery_admission_claim_repository import DiscoveryAdmissionClaimRepository
from repositories.proposal_decision_repository import ProposalDecisionRepository
from schemas.canonical import canonical_sha256
from schemas.discovery_admission_contracts import (
    AuthenticatedPrincipal,
    DiscoveryAdmissionPlan,
    DiscoveryClaimSnapshot,
    GovernanceAuthority,
    ProposalAuthority,
    ValidityBasisSnapshot,
)
from schemas.enums import (
    AuthorizationClass,
    DiscoveryAdmissionReplayDisposition,
    EvaluationControlState,
    GovernanceDecisionOutcome,
)
from schemas.specialist_contracts import (
    BundleProvenanceManifest,
    DecisionRuleSnapshot,
    DiscoveryProposal,
    DiscoverySynthesisBundle,
    MethodParameterSnapshot,
    compute_proposal_digest,
    validate_proposal_against_bundle,
)

DISCOVERY_ADMISSION_NAMESPACE = UUID("2b8f42e2-65a8-4f10-9831-d85c4908079f")
DISCOVERY_ADMISSION_CONTRACT_VERSION = "discovery-admission/v1"

USER_GOVERNED_PURPOSE = "governed_discovery_admission"
USER_GOVERNED_OPERATION_TYPE = "authorize_proposal"
GOVERNANCE_AUTHORITY_ISSUER_ID = "service:governance_authority_issuer"
ALLOWED_TRUSTED_PRODUCERS = frozenset(
    {"system:evaluator", "system:internal_batch", "system:trusted_service"}
)
ALLOWED_TRUSTED_PURPOSES = frozenset({"governed_discovery_admission", "automated_batch_admission"})
ALLOWED_TRUSTED_OPERATION_TYPES = frozenset({"authorize_proposal"})


class ProposalAuthorizationError(ValueError):
    """Raised when proposal authority or authorization verification fails."""


class ProposalDecisionConflictError(ValueError):
    """Raised when conflicting decision submissions or replay conflicts occur."""


class AuthenticatedPrincipalResolver(Protocol):
    """Trusted authentication adapter supplied by the production composition root."""

    def resolve_authenticated_principal(
        self,
        authentication_context_id: str,
    ) -> AuthenticatedPrincipal:
        """Resolve one server-authenticated principal; never accept caller identity fields."""


def generate_deterministic_discovery_id(
    hypothesis_id: UUID,
    proposal_digest: str,
    *,
    contract_version: str = DISCOVERY_ADMISSION_CONTRACT_VERSION,
) -> UUID:
    """Derive a deterministic Discovery ID from authoritative identity."""

    seed = f"{contract_version}:{hypothesis_id}:{proposal_digest}"
    return uuid5(DISCOVERY_ADMISSION_NAMESPACE, seed)


def compute_governance_authority_fingerprint(
    *,
    authority_id: UUID,
    actor_identity: str,
    authority_class: AuthorizationClass,
    workspace_id: str,
    session_id: str | None,
    purpose: str,
    operation_type: str,
    issued_by: str,
    issued_at: datetime,
    expires_at: datetime | None,
) -> str:
    """Fingerprint one independently issued durable actor-authority grant."""

    return canonical_sha256(
        {
            "actor_identity": actor_identity,
            "authority_class": authority_class.value,
            "authority_id": authority_id,
            "expires_at": _canonical_datetime(expires_at),
            "issued_at": _canonical_datetime(issued_at),
            "issued_by": issued_by,
            "operation_type": operation_type,
            "purpose": purpose,
            "session_id": session_id,
            "workspace_id": workspace_id,
        }
    )


def compute_decision_fingerprint(
    *,
    decision_id: UUID,
    authority_id: UUID,
    evaluation_id: UUID,
    evaluation_key: str,
    hypothesis_id: UUID,
    task_id: UUID,
    proposal_digest: str,
    bundle_digest: str,
    evidence_set_digest: str,
    decision: GovernanceDecisionOutcome,
    actor: str,
    actor_authority_type: AuthorizationClass,
    workspace_id: str,
    session_id: str | None,
    purpose: str,
    operation_type: str,
    decision_timestamp: datetime,
    reason: str | None,
) -> str:
    """Fingerprint every immutable field of one durable governance decision."""

    return canonical_sha256(
        {
            "actor": actor,
            "actor_authority_type": actor_authority_type.value,
            "authority_id": authority_id,
            "bundle_digest": bundle_digest,
            "decision": decision.value,
            "decision_id": decision_id,
            "decision_timestamp": _canonical_datetime(decision_timestamp),
            "evaluation_id": evaluation_id,
            "evaluation_key": evaluation_key,
            "evidence_set_digest": evidence_set_digest,
            "hypothesis_id": hypothesis_id,
            "operation_type": operation_type,
            "proposal_digest": proposal_digest,
            "purpose": purpose,
            "reason": reason,
            "session_id": session_id,
            "task_id": task_id,
            "workspace_id": workspace_id,
        }
    )


def compute_admission_fingerprint(plan: DiscoveryAdmissionPlan) -> str:
    """Fingerprint every plan field other than the fingerprint itself."""

    return canonical_sha256(plan.model_dump(mode="python", exclude={"admission_fingerprint"}))


class GovernanceAuthorityIssuer:
    """Production authority issuer boundary for user-governed decision authority."""

    def __init__(
        self,
        session: Session,
        *,
        principal_resolver: AuthenticatedPrincipalResolver,
        workspace_id: str,
        session_id: str | None = None,
    ) -> None:
        if not workspace_id.strip():
            raise ValueError("Governance authority issuer requires a non-empty workspace identity.")
        if session_id is not None and not session_id.strip():
            raise ValueError("Session identity must be non-empty when supplied.")
        self._session = session
        self._principal_resolver = principal_resolver
        self._workspace_id = workspace_id
        self._session_id = session_id

    def issue_user_authority(
        self,
        *,
        authentication_context_id: str,
        expires_at: datetime | None = None,
    ) -> GovernanceAuthorityRecord:
        """Resolve authenticated identity and durably issue one fixed-purpose grant."""

        if self._session.new or self._session.dirty or self._session.deleted:
            raise ProposalAuthorizationError("Authority issuer requires a clean unit of work.")

        if not authentication_context_id.strip():
            raise ProposalAuthorizationError("Authentication context identity cannot be empty.")
        principal = self._principal_resolver.resolve_authenticated_principal(
            authentication_context_id
        )
        if principal.authentication_context_id != authentication_context_id:
            raise ProposalAuthorizationError("Authentication context identity mismatch.")
        if principal.workspace_id != self._workspace_id:
            raise ProposalAuthorizationError("Authenticated principal workspace mismatch.")
        if self._session_id is None or principal.session_id != self._session_id:
            raise ProposalAuthorizationError("Authenticated principal session mismatch.")

        now = utc_now()
        authenticated_at = principal.authenticated_at
        if authenticated_at.tzinfo is None:
            authenticated_at = authenticated_at.replace(tzinfo=UTC)
        if authenticated_at > now:
            raise ProposalAuthorizationError("Authenticated principal timestamp is in the future.")
        if _datetime_is_expired(expires_at, now):
            raise ProposalAuthorizationError("Cannot issue an already-expired authority grant.")

        authority_id = uuid4()
        fingerprint = compute_governance_authority_fingerprint(
            authority_id=authority_id,
            actor_identity=principal.principal_id,
            authority_class=AuthorizationClass.USER_GOVERNED,
            workspace_id=self._workspace_id,
            session_id=self._session_id,
            purpose=USER_GOVERNED_PURPOSE,
            operation_type=USER_GOVERNED_OPERATION_TYPE,
            issued_by=GOVERNANCE_AUTHORITY_ISSUER_ID,
            issued_at=now,
            expires_at=expires_at,
        )

        record = GovernanceAuthorityRecord(
            authority_id=authority_id,
            actor_identity=principal.principal_id,
            authority_class=AuthorizationClass.USER_GOVERNED,
            workspace_id=self._workspace_id,
            session_id=self._session_id,
            purpose=USER_GOVERNED_PURPOSE,
            operation_type=USER_GOVERNED_OPERATION_TYPE,
            issued_by=GOVERNANCE_AUTHORITY_ISSUER_ID,
            issued_at=now,
            expires_at=expires_at,
            active=True,
            authority_fingerprint=fingerprint,
        )

        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record


class DiscoveryAdmissionGovernanceService:
    """Persist decisions and construct detached plans without scientific mutation."""

    def __init__(
        self,
        session: Session,
        *,
        workspace_id: str,
        session_id: str | None = None,
    ) -> None:
        if not workspace_id.strip():
            raise ValueError("Discovery governance requires a non-empty workspace identity.")
        if session_id is not None and not session_id.strip():
            raise ValueError("Session identity must be non-empty when supplied.")
        self._session = session
        self._decision_repo = ProposalDecisionRepository(session)
        self._claim_repo = DiscoveryAdmissionClaimRepository(session)
        self._workspace_id = workspace_id
        self._session_id = session_id

    def extract_proposal_authority(self, evaluation_id: UUID) -> ProposalAuthority:
        """Rebuild canonical durable proposal/bundle authority from repositories."""

        self._require_clean_unit_of_work()
        authority, _, _, _ = self._load_current_proposal(evaluation_id)
        return authority

    def record_governance_decision(
        self,
        *,
        evaluation_id: UUID,
        authority_id: UUID,
        decision: GovernanceDecisionOutcome,
    ) -> ProposalDecisionRecord:
        """Persist a decision using an independently issued durable authority grant."""

        self._require_clean_unit_of_work()
        authority_grant = self._load_governance_authority(authority_id)
        proposal_authority, _, _, _ = self._load_current_proposal(evaluation_id)

        existing = self._decision_repo.get_for_proposal(
            evaluation_id, proposal_authority.proposal_digest
        )
        if existing is not None:
            if self._is_exact_decision_replay(
                existing,
                authority=authority_grant,
                decision=decision,
            ):
                return existing
            raise ProposalDecisionConflictError(
                f"A conflicting decision ({existing.decision}) already exists for this evaluation."
            )

        decision_id = uuid4()
        decision_timestamp = utc_now()
        fingerprint = compute_decision_fingerprint(
            decision_id=decision_id,
            authority_id=authority_grant.authority_id,
            evaluation_id=proposal_authority.evaluation_id,
            evaluation_key=proposal_authority.evaluation_key,
            hypothesis_id=proposal_authority.hypothesis_id,
            task_id=proposal_authority.source_task_id,
            proposal_digest=proposal_authority.proposal_digest,
            bundle_digest=proposal_authority.bundle_digest,
            evidence_set_digest=proposal_authority.evidence_set_digest,
            decision=decision,
            actor=authority_grant.actor_identity,
            actor_authority_type=authority_grant.authority_class,
            workspace_id=authority_grant.workspace_id,
            session_id=authority_grant.session_id,
            purpose=authority_grant.purpose,
            operation_type=authority_grant.operation_type,
            decision_timestamp=decision_timestamp,
            reason=None,
        )
        record = ProposalDecisionRecord(
            decision_id=decision_id,
            authority_id=authority_grant.authority_id,
            evaluation_id=proposal_authority.evaluation_id,
            evaluation_key=proposal_authority.evaluation_key,
            hypothesis_id=proposal_authority.hypothesis_id,
            task_id=proposal_authority.source_task_id,
            proposal_digest=proposal_authority.proposal_digest,
            bundle_digest=proposal_authority.bundle_digest,
            evidence_set_digest=proposal_authority.evidence_set_digest,
            decision=decision,
            actor=authority_grant.actor_identity,
            actor_authority_type=authority_grant.authority_class,
            workspace_id=authority_grant.workspace_id,
            session_id=authority_grant.session_id,
            purpose=authority_grant.purpose,
            operation_type=authority_grant.operation_type,
            decision_timestamp=decision_timestamp,
            reason=None,
            decision_fingerprint=fingerprint,
            consumed=False,
        )
        try:
            return self._decision_repo.create(record)
        except IntegrityError as exc:
            winner = self._decision_repo.get_for_proposal(
                evaluation_id, proposal_authority.proposal_digest
            )
            if winner is not None and self._is_exact_decision_replay(
                winner,
                authority=authority_grant,
                decision=decision,
            ):
                return winner
            raise ProposalDecisionConflictError(
                "Concurrent decision submission produced a conflicting authoritative result."
            ) from exc

    def verify_authorization(
        self,
        evaluation_id: UUID,
        decision_id: UUID,
    ) -> tuple[ProposalAuthority, ProposalDecisionRecord]:
        """Rebuild and verify every durable authorization input before planning."""

        self._require_clean_unit_of_work()
        authority = self.extract_proposal_authority(evaluation_id)
        decision_record = self._decision_repo.get_by_id(decision_id)
        if decision_record is None:
            raise ProposalAuthorizationError(f"Decision record not found: {decision_id}")

        eval_rec = self._session.get(EvaluationControlRecord, evaluation_id)
        authority_grant = self._load_governance_authority(
            decision_record.authority_id,
            require_active=(eval_rec is None or eval_rec.state != EvaluationControlState.COMMITTED),
        )
        expected_bindings = {
            "evaluation_id": (decision_record.evaluation_id, authority.evaluation_id),
            "evaluation_key": (decision_record.evaluation_key, authority.evaluation_key),
            "hypothesis_id": (decision_record.hypothesis_id, authority.hypothesis_id),
            "task_id": (decision_record.task_id, authority.source_task_id),
            "proposal_digest": (decision_record.proposal_digest, authority.proposal_digest),
            "bundle_digest": (decision_record.bundle_digest, authority.bundle_digest),
            "evidence_set_digest": (
                decision_record.evidence_set_digest,
                authority.evidence_set_digest,
            ),
        }
        for label, (actual, expected) in expected_bindings.items():
            if actual != expected:
                raise ProposalAuthorizationError(f"Decision record {label} mismatch.")

        if decision_record.decision != GovernanceDecisionOutcome.APPROVED:
            raise ProposalAuthorizationError(
                f"Decision outcome must be APPROVED, got: {decision_record.decision}"
            )
        if decision_record.consumed:
            eval_rec = self._session.get(EvaluationControlRecord, evaluation_id)
            if eval_rec is None or eval_rec.state != EvaluationControlState.COMMITTED:
                raise ProposalAuthorizationError(
                    f"Decision {decision_id} has already been consumed."
                )
        if (
            decision_record.actor != authority_grant.actor_identity
            or decision_record.actor_authority_type != authority_grant.authority_class
            or decision_record.workspace_id != authority_grant.workspace_id
            or decision_record.session_id != authority_grant.session_id
            or decision_record.purpose != authority_grant.purpose
            or decision_record.operation_type != authority_grant.operation_type
        ):
            raise ProposalAuthorizationError(
                "Decision actor authority does not match its durable authority grant."
            )

        expected_fingerprint = compute_decision_fingerprint(
            decision_id=decision_record.decision_id,
            authority_id=decision_record.authority_id,
            evaluation_id=decision_record.evaluation_id,
            evaluation_key=decision_record.evaluation_key,
            hypothesis_id=decision_record.hypothesis_id,
            task_id=decision_record.task_id,
            proposal_digest=decision_record.proposal_digest,
            bundle_digest=decision_record.bundle_digest,
            evidence_set_digest=decision_record.evidence_set_digest,
            decision=decision_record.decision,
            actor=decision_record.actor,
            actor_authority_type=decision_record.actor_authority_type,
            workspace_id=decision_record.workspace_id,
            session_id=decision_record.session_id,
            purpose=decision_record.purpose,
            operation_type=decision_record.operation_type,
            decision_timestamp=decision_record.decision_timestamp,
            reason=decision_record.reason,
        )
        if decision_record.decision_fingerprint != expected_fingerprint:
            raise ProposalAuthorizationError("Decision fingerprint is invalid.")

        allow_existing = eval_rec is not None and eval_rec.state == EvaluationControlState.COMMITTED
        self._require_no_discovery(authority.hypothesis_id, allow_existing=allow_existing)
        return authority, decision_record

    def check_admission_preconditions(
        self,
        hypothesis_id: UUID,
    ) -> tuple[DiscoveryAdmissionReplayDisposition, DiscoveryRecord | None]:
        """Classify the only Package 3 legal state: no Discovery exists yet."""

        discovery = self._session.exec(
            select(DiscoveryRecord).where(DiscoveryRecord.hypothesis_id == hypothesis_id)
        ).first()
        if discovery is None:
            return DiscoveryAdmissionReplayDisposition.NEW, None
        return DiscoveryAdmissionReplayDisposition.CONFLICT, discovery

    def create_admission_plan(
        self,
        evaluation_id: UUID,
        decision_id: UUID,
    ) -> DiscoveryAdmissionPlan:
        """Construct a detached plan and perform no flush, commit, or lifecycle mutation."""

        self._require_clean_unit_of_work()
        authority, decision_record = self.verify_authorization(evaluation_id, decision_id)
        rebuilt_authority, proposal, bundle, manifest = self._load_current_proposal(evaluation_id)
        if rebuilt_authority != authority:
            raise ProposalAuthorizationError(
                "Proposal authority changed while the admission plan was being constructed."
            )

        authority_grant = self._load_governance_authority(
            decision_record.authority_id,
            require_active=(
                self._session.get(EvaluationControlRecord, evaluation_id).state
                != EvaluationControlState.COMMITTED
            ),
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
            decision_rule=DecisionRuleSnapshot.from_domain(proposal.validity_basis.decision_rule),
            strength=proposal.validity_basis.strength,
            uncertainty=proposal.validity_basis.uncertainty,
            assumptions_excluded_from_inference=True,
            invalidators=tuple(proposal.validity_basis.invalidators),
        )
        unsigned = DiscoveryAdmissionPlan(
            authorization_decision_id=decision_record.decision_id,
            authorization_fingerprint=decision_record.decision_fingerprint,
            authorization_authority_id=authority_grant.authority_id,
            authorization_actor=authority_grant.actor_identity,
            authorization_class=authority_grant.authority_class,
            authorization_workspace_id=authority_grant.workspace_id,
            authorization_session_id=authority_grant.session_id,
            authorization_purpose=authority_grant.purpose,
            authorization_operation_type=authority_grant.operation_type,
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

        final_authority, final_decision = self.verify_authorization(evaluation_id, decision_id)
        if final_authority != authority or final_decision.decision_fingerprint != (
            decision_record.decision_fingerprint
        ):
            raise ProposalAuthorizationError(
                "Durable authority changed before admission-plan construction completed."
            )
        if compute_admission_fingerprint(plan) != plan.admission_fingerprint:
            raise ProposalAuthorizationError("Admission plan fingerprint is not self-consistent.")
        return plan

    def _load_current_proposal(
        self,
        evaluation_id: UUID,
    ) -> tuple[
        ProposalAuthority,
        DiscoveryProposal,
        DiscoverySynthesisBundle,
        BundleProvenanceManifest,
    ]:
        self._session.expire_all()
        record = self._session.get(EvaluationControlRecord, evaluation_id)
        if record is None:
            raise ProposalAuthorizationError(
                f"Evaluation control record not found: {evaluation_id}"
            )
        if record.state not in (
            EvaluationControlState.PROPOSAL_READY,
            EvaluationControlState.COMMITTED,
        ):
            raise ProposalAuthorizationError(
                "Evaluation control record state must be PROPOSAL_READY or COMMITTED, "
                f"got: {record.state}"
            )
        if (
            not record.proposal_digest
            or not record.serialized_proposal
            or not record.owner
            or record.fencing_epoch < 1
        ):
            raise ProposalAuthorizationError(
                "Evaluation control record has incomplete proposal or fencing provenance."
            )

        try:
            proposal = DiscoveryProposal.model_validate(record.serialized_proposal)
        except ValueError as exc:
            raise ProposalAuthorizationError("Persisted proposal is invalid.") from exc
        if proposal.model_dump(mode="json") != record.serialized_proposal:
            raise ProposalAuthorizationError(
                "Persisted proposal is not the exact canonical serialized proposal."
            )

        try:
            bundle, manifest = build_synthesis_bundle(
                self._session,
                record.hypothesis_id,
                contract_version=record.contract_version,
                allow_evaluated=True,
            )
            validate_proposal_against_bundle(proposal, bundle)
        except (SynthesisBundleError, ValueError) as exc:
            raise ProposalAuthorizationError(
                f"Current durable proposal authority is stale or invalid: {exc}"
            ) from exc

        evidence_ids = [str(item.evidence_id) for item in bundle.admitted_evidence]
        if (
            record.evidence_ids != evidence_ids
            or record.evidence_set_digest != compute_evidence_set_digest(bundle)
            or record.bundle_digest != bundle.input_digest
            or record.evaluation_key != compute_evaluation_key(bundle)
            or record.serialized_manifest != manifest.model_dump(mode="json")
        ):
            raise ProposalAuthorizationError(
                "Evaluation record no longer matches the current canonical protected bundle."
            )
        proposal_digest = compute_proposal_digest(proposal, bundle.input_digest)
        if proposal_digest != record.proposal_digest:
            raise ProposalAuthorizationError(
                "Persisted proposal digest does not match the exact proposal and current bundle."
            )

        from db.models import HypothesisRecord

        hypothesis = self._session.get(HypothesisRecord, record.hypothesis_id)
        if hypothesis is None:
            raise ProposalAuthorizationError("Durable Hypothesis disappeared during verification.")
        authority = ProposalAuthority(
            evaluation_id=record.evaluation_id,
            evaluation_key=record.evaluation_key,
            hypothesis_id=record.hypothesis_id,
            source_task_id=hypothesis.task_id,
            profile_id=bundle.data_profile.data_profile_id,
            proposal_digest=record.proposal_digest,
            bundle_digest=record.bundle_digest,
            evidence_set_digest=record.evidence_set_digest,
            manifest_digest=canonical_sha256(manifest),
            exact_evidence_ids=tuple(item.evidence_id for item in bundle.admitted_evidence),
            exact_analysis_frame_ids=tuple(
                item.analysis_frame_id for item in bundle.analysis_frames
            ),
            proposal_contract_version=proposal.proposal_schema_version,
            serialized_proposal_identity=canonical_sha256(record.serialized_proposal),
            evaluation_attempt_number=record.attempt_number,
            evaluation_owner=record.owner,
            evaluation_fencing_epoch=record.fencing_epoch,
            evaluation_created_at=record.created_at,
        )
        return authority, proposal, bundle, manifest

    def _load_governance_authority(
        self,
        authority_id: UUID,
        *,
        require_active: bool = True,
    ) -> GovernanceAuthority:
        self._session.expire_all()
        record = self._decision_repo.get_authority(authority_id)
        if record is None:
            raise ProposalAuthorizationError(
                f"Governance authority record not found: {authority_id}"
            )
        now = utc_now()
        if require_active and (not record.active or _datetime_is_expired(record.expires_at, now)):
            raise ProposalAuthorizationError("Governance authority is inactive or expired.")
        if record.workspace_id != self._workspace_id:
            raise ProposalAuthorizationError("Governance authority workspace mismatch.")
        if record.authority_class == AuthorizationClass.USER_GOVERNED:
            if (
                record.session_id is None
                or self._session_id is None
                or record.session_id != self._session_id
                or record.purpose != USER_GOVERNED_PURPOSE
                or record.operation_type != USER_GOVERNED_OPERATION_TYPE
            ):
                raise ProposalAuthorizationError(
                    "User-governed authority is not bound to this session and operation."
                )
        elif record.authority_class == AuthorizationClass.TRUSTED_INTERNAL:
            if (
                self._session_id is not None
                or record.actor_identity not in ALLOWED_TRUSTED_PRODUCERS
                or record.purpose not in ALLOWED_TRUSTED_PURPOSES
                or record.operation_type not in ALLOWED_TRUSTED_OPERATION_TYPES
            ):
                raise ProposalAuthorizationError(
                    "Trusted-internal authority is not durably allow-listed for this operation."
                )
        else:
            raise ProposalAuthorizationError("Governance authority class is unauthorized.")

        expected = compute_governance_authority_fingerprint(
            authority_id=record.authority_id,
            actor_identity=record.actor_identity,
            authority_class=record.authority_class,
            workspace_id=record.workspace_id,
            session_id=record.session_id,
            purpose=record.purpose,
            operation_type=record.operation_type,
            issued_by=record.issued_by,
            issued_at=record.issued_at,
            expires_at=record.expires_at,
        )
        if record.authority_fingerprint != expected:
            raise ProposalAuthorizationError("Governance authority fingerprint is invalid.")
        return GovernanceAuthority(
            authority_id=record.authority_id,
            actor_identity=record.actor_identity,
            authority_class=record.authority_class,
            workspace_id=record.workspace_id,
            session_id=record.session_id,
            purpose=record.purpose,
            operation_type=record.operation_type,
            issued_by=record.issued_by,
            issued_at=record.issued_at,
            expires_at=record.expires_at,
            authority_fingerprint=record.authority_fingerprint,
        )

    def _is_exact_decision_replay(
        self,
        record: ProposalDecisionRecord,
        *,
        authority: GovernanceAuthority,
        decision: GovernanceDecisionOutcome,
    ) -> bool:
        return (
            record.authority_id == authority.authority_id
            and record.decision == decision
            and record.actor == authority.actor_identity
            and record.actor_authority_type == authority.authority_class
            and record.workspace_id == authority.workspace_id
            and record.session_id == authority.session_id
            and record.purpose == authority.purpose
            and record.operation_type == authority.operation_type
            and record.reason is None
        )

    def _require_no_discovery(self, hypothesis_id: UUID, *, allow_existing: bool = False) -> None:
        disposition, _ = self.check_admission_preconditions(hypothesis_id)
        if disposition != DiscoveryAdmissionReplayDisposition.NEW and not allow_existing:
            raise ProposalAuthorizationError(
                f"Discovery already exists for Hypothesis {hypothesis_id}."
            )

    def _require_clean_unit_of_work(self) -> None:
        if self._session.new or self._session.dirty or self._session.deleted:
            raise ProposalAuthorizationError(
                "Discovery governance requires a clean session and will not flush caller changes."
            )


def _canonical_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _datetime_is_expired(expiry: datetime | None, now: datetime) -> bool:
    if expiry is None:
        return False
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return expiry <= now
