"""Durable evaluation-control transitions with database CAS and stale-bundle fencing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from application.evaluation.bundle_builder import (
    SynthesisBundleError,
    build_synthesis_bundle,
    compute_evaluation_key,
    compute_evidence_set_digest,
)
from db.models import EvaluationControlRecord, utc_now
from repositories.evaluation import (
    ACTIVE_EVALUATION_STATES,
    EvaluationControlRepository,
)
from schemas.enums import EvaluationControlState
from schemas.evaluation import (
    BundleProvenanceManifest,
    DiscoveryProposal,
    DiscoverySynthesisBundle,
    EvaluationFailure,
    compute_proposal_digest,
    validate_proposal_against_bundle,
)


class EvaluationTransitionError(Exception):
    """Base exception for illegal or fenced evaluation-control transitions."""


class StaleEvaluationOwnerError(EvaluationTransitionError):
    """Raised when a stale evaluator attempts a fenced mutation."""


class StaleEvaluationBundleError(EvaluationTransitionError):
    """Raised after current durable state invalidates a claimed bundle."""


class EvaluationConflictError(EvaluationTransitionError):
    """Raised when identity-bound records or proposal digests conflict."""


def _is_expired(expiry: datetime | None, now: datetime) -> bool:
    if expiry is None:
        return False
    if expiry.tzinfo is None and now.tzinfo is not None:
        expiry = expiry.replace(tzinfo=UTC)
    elif expiry.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return expiry <= now


class EvaluationTransitionService:
    """Own every writer for the Package 2 evaluation lifecycle."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = EvaluationControlRepository(session)

    def enqueue_evaluation(
        self,
        *,
        hypothesis_id: UUID,
    ) -> tuple[EvaluationControlRecord, bool]:
        """Build from repositories and enqueue one exact protected evaluation identity."""

        bundle, manifest = build_synthesis_bundle(self._session, hypothesis_id)
        evaluation_key = compute_evaluation_key(bundle)
        evidence_set_digest = compute_evidence_set_digest(bundle)
        evidence_ids = [str(evidence.evidence_id) for evidence in bundle.admitted_evidence]

        exact = self._repo.get_by_evaluation_key(evaluation_key)
        if exact is not None:
            if not _record_matches_bundle(
                exact,
                bundle=bundle,
                manifest=manifest,
                evidence_ids=evidence_ids,
                evidence_set_digest=evidence_set_digest,
            ):
                self._quarantine_partial_identity(exact.evaluation_id)
                raise EvaluationConflictError(
                    "Existing evaluation identity contains partial or conflicting provenance."
                )
            return exact, False

        active = self._repo.get_active_evaluation(hypothesis_id)
        if active is not None:
            invalidated = self._session.execute(
                update(EvaluationControlRecord)
                .where(EvaluationControlRecord.evaluation_id == active.evaluation_id)
                .where(EvaluationControlRecord.state.in_(tuple(ACTIVE_EVALUATION_STATES)))
                .values(
                    state=EvaluationControlState.INVALIDATED,
                    invalidation_reason=f"Superseded by bundle {bundle.input_digest}.",
                    updated_at=utc_now(),
                )
                .execution_options(synchronize_session=False)
            )
            if invalidated.rowcount != 1:
                self._session.rollback()
                raise EvaluationConflictError(
                    "Active evaluation changed while replacement was being enqueued."
                )

        record = EvaluationControlRecord(
            hypothesis_id=hypothesis_id,
            evidence_ids=evidence_ids,
            evidence_set_digest=evidence_set_digest,
            bundle_digest=bundle.input_digest,
            contract_version=bundle.contract_version,
            evaluation_key=evaluation_key,
            serialized_manifest=manifest.model_dump(mode="json"),
            state=EvaluationControlState.PENDING,
            fencing_epoch=0,
            attempt_number=1,
        )
        self._repo._stage_create_from_transition(record)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            winner = self._repo.get_by_evaluation_key(evaluation_key)
            if winner is not None and _record_matches_bundle(
                winner,
                bundle=bundle,
                manifest=manifest,
                evidence_ids=evidence_ids,
                evidence_set_digest=evidence_set_digest,
            ):
                return winner, False
            raise EvaluationConflictError(
                "Concurrent enqueue produced a conflicting evaluation identity."
            ) from exc
        self._session.refresh(record)
        return record, True

    def claim_evaluation(
        self,
        *,
        evaluation_id: UUID,
        owner: str,
        claim_duration_seconds: int = 300,
    ) -> EvaluationControlRecord:
        """CAS-claim PENDING or reclaim an expired CLAIMED record."""

        if not owner.strip() or claim_duration_seconds <= 0:
            raise ValueError("Evaluation claim requires an owner and positive duration.")
        now = utc_now()
        claimed = self._session.execute(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == evaluation_id)
            .where(
                or_(
                    EvaluationControlRecord.state == EvaluationControlState.PENDING,
                    (
                        (EvaluationControlRecord.state == EvaluationControlState.CLAIMED)
                        & (EvaluationControlRecord.claim_expiry <= now)
                    ),
                )
            )
            .values(
                state=EvaluationControlState.CLAIMED,
                owner=owner,
                claim_time=now,
                claim_expiry=now + timedelta(seconds=claim_duration_seconds),
                fencing_epoch=EvaluationControlRecord.fencing_epoch + 1,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            self._session.rollback()
            raise EvaluationTransitionError(
                f"Evaluation {evaluation_id} is absent or not claimable."
            )
        self._session.commit()
        return self._require_record(evaluation_id)

    def publish_proposal(
        self,
        *,
        evaluation_id: UUID,
        owner: str,
        fencing_epoch: int,
        source_bundle_digest: str,
        proposal: DiscoveryProposal,
    ) -> EvaluationControlRecord:
        """Recheck current durable inputs and CAS-publish one validated proposal."""

        existing = self._require_record(evaluation_id)
        if (
            existing.state == EvaluationControlState.PROPOSAL_READY
            and existing.owner == owner
            and existing.fencing_epoch == fencing_epoch
        ):
            return self._resolve_published_proposal(
                existing=existing,
                source_bundle_digest=source_bundle_digest,
                proposal=proposal,
            )

        try:
            _, current_bundle = self._current_claim_bundle(
                evaluation_id=evaluation_id,
                owner=owner,
                fencing_epoch=fencing_epoch,
                source_bundle_digest=source_bundle_digest,
            )
        except StaleEvaluationOwnerError:
            self._session.rollback()
            existing = self._require_record(evaluation_id)
            if (
                existing.state == EvaluationControlState.PROPOSAL_READY
                and existing.owner == owner
                and existing.fencing_epoch == fencing_epoch
            ):
                return self._resolve_published_proposal(
                    existing=existing,
                    source_bundle_digest=source_bundle_digest,
                    proposal=proposal,
                )
            raise
        validate_proposal_against_bundle(proposal, current_bundle)
        proposal_digest = compute_proposal_digest(proposal, current_bundle.input_digest)
        serialized = proposal.model_dump(mode="json")
        now = utc_now()
        published = self._session.execute(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == evaluation_id)
            .where(EvaluationControlRecord.state == EvaluationControlState.CLAIMED)
            .where(EvaluationControlRecord.owner == owner)
            .where(EvaluationControlRecord.fencing_epoch == fencing_epoch)
            .where(EvaluationControlRecord.claim_expiry > now)
            .where(EvaluationControlRecord.bundle_digest == source_bundle_digest)
            .values(
                state=EvaluationControlState.PROPOSAL_READY,
                proposal_digest=proposal_digest,
                serialized_proposal=serialized,
                failure_reason=None,
                serialized_failure=None,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if published.rowcount == 1:
            self._session.commit()
            return self._require_record(evaluation_id)

        self._session.rollback()
        existing = self._require_record(evaluation_id)
        if (
            existing.state == EvaluationControlState.PROPOSAL_READY
            and existing.owner == owner
            and existing.fencing_epoch == fencing_epoch
            and existing.proposal_digest == proposal_digest
            and existing.serialized_proposal == serialized
        ):
            return existing
        if (
            existing.state == EvaluationControlState.PROPOSAL_READY
            and existing.owner == owner
            and existing.fencing_epoch == fencing_epoch
        ):
            self._mark_conflict(
                evaluation_id,
                reason="changed_proposal_under_same_evaluation_claim",
            )
            raise EvaluationConflictError(
                "A changed proposal contended under the same evaluation claim."
            )
        raise StaleEvaluationOwnerError("Proposal publication lost its evaluation fence.")

    def _resolve_published_proposal(
        self,
        *,
        existing: EvaluationControlRecord,
        source_bundle_digest: str,
        proposal: DiscoveryProposal,
    ) -> EvaluationControlRecord:
        current_bundle, _ = build_synthesis_bundle(self._session, existing.hypothesis_id)
        validate_proposal_against_bundle(proposal, current_bundle)
        replay_digest = compute_proposal_digest(proposal, current_bundle.input_digest)
        if (
            existing.bundle_digest == source_bundle_digest
            and existing.bundle_digest == current_bundle.input_digest
            and existing.proposal_digest == replay_digest
            and existing.serialized_proposal == proposal.model_dump(mode="json")
        ):
            self._session.rollback()
            return existing
        self._session.rollback()
        self._mark_conflict(
            existing.evaluation_id,
            reason="changed_proposal_under_same_evaluation_claim",
        )
        raise EvaluationConflictError(
            "A changed proposal contended under the same evaluation claim."
        )

    def load_claimed_bundle(
        self,
        *,
        evaluation_id: UUID,
        owner: str,
        fencing_epoch: int,
        source_bundle_digest: str,
    ) -> DiscoverySynthesisBundle:
        """Rebuild and fence the canonical bundle before model invocation."""

        _, bundle = self._current_claim_bundle(
            evaluation_id=evaluation_id,
            owner=owner,
            fencing_epoch=fencing_epoch,
            source_bundle_digest=source_bundle_digest,
        )
        self._session.rollback()
        return bundle

    def record_failure(
        self,
        *,
        evaluation_id: UUID,
        owner: str,
        fencing_epoch: int,
        source_bundle_digest: str,
        failure: EvaluationFailure,
        retryable: bool,
    ) -> EvaluationControlRecord:
        """CAS-record one typed technical or contract failure for the same bundle."""

        self._current_claim_bundle(
            evaluation_id=evaluation_id,
            owner=owner,
            fencing_epoch=fencing_epoch,
            source_bundle_digest=source_bundle_digest,
        )
        now = utc_now()
        target_state = (
            EvaluationControlState.RETRYABLE_FAILED
            if retryable
            else EvaluationControlState.NON_RETRYABLE_FAILED
        )
        updated = self._session.execute(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == evaluation_id)
            .where(EvaluationControlRecord.state == EvaluationControlState.CLAIMED)
            .where(EvaluationControlRecord.owner == owner)
            .where(EvaluationControlRecord.fencing_epoch == fencing_epoch)
            .where(EvaluationControlRecord.claim_expiry > now)
            .where(EvaluationControlRecord.bundle_digest == source_bundle_digest)
            .values(
                state=target_state,
                failure_reason=failure.failure_reason.value,
                serialized_failure=failure.model_dump(mode="json"),
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if updated.rowcount != 1:
            self._session.rollback()
            raise StaleEvaluationOwnerError("Failure publication lost its evaluation fence.")
        self._session.commit()
        return self._require_record(evaluation_id)

    def retry_evaluation(self, *, evaluation_id: UUID) -> EvaluationControlRecord:
        """Retry the same current bundle without dispatching a Data Explorer attempt."""

        record = self._require_record(evaluation_id)
        if record.state != EvaluationControlState.RETRYABLE_FAILED:
            raise EvaluationTransitionError("Only retryable_failed evaluations may be retried.")
        try:
            current_bundle, _ = build_synthesis_bundle(self._session, record.hypothesis_id)
        except SynthesisBundleError as exc:
            self.invalidate_evaluation(
                evaluation_id=evaluation_id,
                reason=f"Bundle no longer admissible before retry: {exc}",
            )
            raise StaleEvaluationBundleError(str(exc)) from exc
        if current_bundle.input_digest != record.bundle_digest:
            self.invalidate_evaluation(
                evaluation_id=evaluation_id,
                reason="Bundle digest changed before retry.",
            )
            raise StaleEvaluationBundleError("Bundle digest changed before retry.")

        now = utc_now()
        retried = self._session.execute(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == evaluation_id)
            .where(EvaluationControlRecord.state == EvaluationControlState.RETRYABLE_FAILED)
            .where(EvaluationControlRecord.bundle_digest == current_bundle.input_digest)
            .values(
                state=EvaluationControlState.PENDING,
                attempt_number=EvaluationControlRecord.attempt_number + 1,
                owner=None,
                claim_time=None,
                claim_expiry=None,
                failure_reason=None,
                serialized_failure=None,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if retried.rowcount != 1:
            self._session.rollback()
            raise EvaluationTransitionError("Evaluation retry lost its state transition.")
        self._session.commit()
        return self._require_record(evaluation_id)

    def invalidate_evaluation(self, *, evaluation_id: UUID, reason: str) -> EvaluationControlRecord:
        return self._terminal_transition(
            evaluation_id=evaluation_id,
            target=EvaluationControlState.INVALIDATED,
            reason=reason,
        )

    def cancel_evaluation(self, *, evaluation_id: UUID, reason: str) -> EvaluationControlRecord:
        return self._terminal_transition(
            evaluation_id=evaluation_id,
            target=EvaluationControlState.CANCELLED,
            reason=reason,
        )

    def quarantine_conflict(self, *, evaluation_id: UUID, reason: str) -> EvaluationControlRecord:
        return self._terminal_transition(
            evaluation_id=evaluation_id,
            target=EvaluationControlState.CONFLICT,
            reason=reason,
        )

    def _current_claim_bundle(
        self,
        *,
        evaluation_id: UUID,
        owner: str,
        fencing_epoch: int,
        source_bundle_digest: str,
    ) -> tuple[EvaluationControlRecord, DiscoverySynthesisBundle]:
        self._session.expire_all()
        record = self._require_record(evaluation_id)
        now = utc_now()
        if (
            record.state != EvaluationControlState.CLAIMED
            or record.owner != owner
            or record.fencing_epoch != fencing_epoch
            or _is_expired(record.claim_expiry, now)
            or record.bundle_digest != source_bundle_digest
        ):
            raise StaleEvaluationOwnerError("Evaluation claim authority is stale or mismatched.")
        try:
            bundle, _ = build_synthesis_bundle(self._session, record.hypothesis_id)
        except SynthesisBundleError as exc:
            self._invalidate_claim(
                record,
                reason=f"Protected bundle no longer admissible: {exc}",
            )
            raise StaleEvaluationBundleError(str(exc)) from exc
        if bundle.input_digest != record.bundle_digest:
            self._invalidate_claim(record, reason="Protected bundle digest changed.")
            raise StaleEvaluationBundleError("Protected bundle digest changed.")
        return record, bundle

    def _invalidate_claim(self, record: EvaluationControlRecord, *, reason: str) -> None:
        updated = self._session.execute(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == record.evaluation_id)
            .where(EvaluationControlRecord.state == EvaluationControlState.CLAIMED)
            .where(EvaluationControlRecord.owner == record.owner)
            .where(EvaluationControlRecord.fencing_epoch == record.fencing_epoch)
            .values(
                state=EvaluationControlState.INVALIDATED,
                invalidation_reason=reason,
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        if updated.rowcount != 1:
            self._session.rollback()
            raise StaleEvaluationOwnerError("Stale-bundle invalidation lost its fence.")
        self._session.commit()

    def _terminal_transition(
        self,
        *,
        evaluation_id: UUID,
        target: EvaluationControlState,
        reason: str,
    ) -> EvaluationControlRecord:
        if target not in {
            EvaluationControlState.INVALIDATED,
            EvaluationControlState.CANCELLED,
            EvaluationControlState.CONFLICT,
        }:
            raise ValueError("Package 2 cannot write this terminal evaluation state.")
        transitioned = self._session.execute(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == evaluation_id)
            .where(EvaluationControlRecord.state.in_(tuple(ACTIVE_EVALUATION_STATES)))
            .values(
                state=target,
                invalidation_reason=reason,
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        if transitioned.rowcount != 1:
            self._session.rollback()
            raise EvaluationTransitionError("Evaluation is absent or already terminal.")
        self._session.commit()
        return self._require_record(evaluation_id)

    def _quarantine_partial_identity(self, evaluation_id: UUID) -> None:
        changed = self._session.execute(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == evaluation_id)
            .where(EvaluationControlRecord.state != EvaluationControlState.COMMITTED)
            .values(
                state=EvaluationControlState.CONFLICT,
                invalidation_reason="partial_or_conflicting_evaluation_identity",
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        if changed.rowcount != 1:
            self._session.rollback()
            raise EvaluationConflictError(
                "Committed or absent evaluation identity cannot be quarantined by Package 2."
            )
        self._session.commit()

    def _mark_conflict(self, evaluation_id: UUID, *, reason: str) -> None:
        changed = self._session.execute(
            update(EvaluationControlRecord)
            .where(EvaluationControlRecord.evaluation_id == evaluation_id)
            .where(EvaluationControlRecord.state.in_(tuple(ACTIVE_EVALUATION_STATES)))
            .values(
                state=EvaluationControlState.CONFLICT,
                invalidation_reason=reason,
                updated_at=utc_now(),
            )
            .execution_options(synchronize_session=False)
        )
        if changed.rowcount != 1:
            self._session.rollback()
            raise EvaluationConflictError("Conflicting evaluation could not be quarantined.")
        self._session.commit()

    def _require_record(self, evaluation_id: UUID) -> EvaluationControlRecord:
        self._session.expire_all()
        record = self._repo.get_by_id(evaluation_id)
        if record is None:
            raise EvaluationTransitionError(f"EvaluationControlRecord {evaluation_id} not found.")
        return record


def _record_matches_bundle(
    record: EvaluationControlRecord,
    *,
    bundle: DiscoverySynthesisBundle,
    manifest: BundleProvenanceManifest,
    evidence_ids: list[str],
    evidence_set_digest: str,
) -> bool:
    return (
        record.hypothesis_id == bundle.hypothesis.hypothesis_id
        and record.evidence_ids == evidence_ids
        and record.evidence_set_digest == evidence_set_digest
        and record.bundle_digest == bundle.input_digest
        and record.contract_version == bundle.contract_version
        and record.evaluation_key == compute_evaluation_key(bundle)
        and record.serialized_manifest == manifest.model_dump(mode="json")
    )
