"""Durable proposal governance decision recording and admission-plan construction."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from application.evaluation.bundle_builder import (
    SynthesisBundleError,
    build_synthesis_bundle,
    compute_evaluation_key,
    compute_evidence_set_digest,
)
from application.governance.authority import (
    USER_GOVERNED_OPERATION_TYPE,
    USER_GOVERNED_PURPOSE,
    ProposalAuthorizationError,
)
from application.governance.fingerprints import (
    _datetime_is_expired,
    compute_admission_fingerprint,
    compute_decision_fingerprint,
    compute_governance_authority_fingerprint,
    generate_deterministic_discovery_id,
)
from db.models import (
    DiscoveryRecord,
    EvaluationControlRecord,
    ProposalDecisionRecord,
    utc_now,
)
from repositories.governance import ProposalDecisionRepository
from schemas.canonical import canonical_sha256
from schemas.discovery_admission_contracts import (
    DiscoveryAdmissionPlan,
    DiscoveryClaimSnapshot,
    ValidityBasisSnapshot,
)
from schemas.enums import (
    AuthorizationClass,
    DiscoveryAdmissionReplayDisposition,
    EvaluationControlState,
    GovernanceDecisionOutcome,
)
from schemas.evaluation import (
    BundleProvenanceManifest,
    DecisionRuleSnapshot,
    DiscoveryProposal,
    DiscoverySynthesisBundle,
    MethodParameterSnapshot,
    compute_proposal_digest,
    validate_proposal_against_bundle,
)
from schemas.governance import GovernanceAuthority, ProposalAuthority

ALLOWED_TRUSTED_PRODUCERS = frozenset(
    {"system:evaluator", "system:internal_batch", "system:trusted_service"}
)
ALLOWED_TRUSTED_PURPOSES = frozenset({"governed_discovery_admission", "automated_batch_admission"})
ALLOWED_TRUSTED_OPERATION_TYPES = frozenset({"authorize_proposal"})


class ProposalDecisionConflictError(ValueError):
    """Raised when conflicting decision submissions or replay conflicts occur."""


class DiscoveryAdmissionGovernanceService:
    """Persist decisions and construct detached plans without scientific mutation."""

    def __init__(
        self,
        session: Session,
        *,
        workspace_id: str,
        session_id: str | None = None,
        principal_id: str | None = None,
    ) -> None:
        if not workspace_id.strip():
            raise ValueError("Discovery governance requires a non-empty workspace identity.")
        if session_id is not None and not session_id.strip():
            raise ValueError("Session identity must be non-empty when supplied.")
        if principal_id is not None and not principal_id.strip():
            raise ValueError("Principal identity must be non-empty when supplied.")
        self._session = session
        self._decision_repo = ProposalDecisionRepository(session)
        self._workspace_id = workspace_id
        self._session_id = session_id
        self._principal_id = principal_id

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
        self._verify_recording_principal(authority_grant)
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
            return self._decision_repo._create_from_governance(record)
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
        if record.expires_at is None:
            raise ProposalAuthorizationError("Governance authority has no expiry.")
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

    def _verify_recording_principal(self, authority: GovernanceAuthority) -> None:
        if authority.authority_class != AuthorizationClass.USER_GOVERNED:
            return
        if self._principal_id is None:
            raise ProposalAuthorizationError(
                "User-governed decisions require an authenticated principal identity."
            )
        if authority.actor_identity != self._principal_id:
            raise ProposalAuthorizationError(
                "Authenticated principal does not own this governance authority."
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
