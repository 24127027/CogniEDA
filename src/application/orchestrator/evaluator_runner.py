"""Claim, invoke, validate, and durably publish one protected evaluation attempt."""

from __future__ import annotations

from uuid import UUID

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from sqlmodel import Session, select

from agents.executor.hypothesis_analyst.nodes import (
    HypothesisAnalystConfigurationError,
    HypothesisAnalystDependencies,
    evaluate_synthesis_bundle,
)
from application.orchestrator.evaluation_transition_service import EvaluationTransitionService
from db.models import EvaluationControlRecord, HypothesisRecord
from schemas.enums import HypothesisStatus
from schemas.specialist_contracts import (
    DiscoveryProposal,
    EvaluationFailure,
    EvaluationFailureReason,
    HypothesisAnalystResult,
)


def enqueue_ready_evaluations(
    session: Session,
    *,
    limit: int = 100,
) -> list[EvaluationControlRecord]:
    """Discover READY_FOR_EVALUATION hypotheses and durably enqueue canonical bundles."""

    hypothesis_ids = session.exec(
        select(HypothesisRecord.hypothesis_id)
        .where(HypothesisRecord.status == HypothesisStatus.READY_FOR_EVALUATION)
        .order_by(HypothesisRecord.updated_at, HypothesisRecord.hypothesis_id)
        .limit(limit)
    ).all()
    service = EvaluationTransitionService(session)
    records: list[EvaluationControlRecord] = []
    for hypothesis_id in hypothesis_ids:
        record, _ = service.enqueue_evaluation(hypothesis_id=hypothesis_id)
        records.append(record)
    return records


def run_evaluation_attempt(
    session: Session,
    *,
    evaluation_id: UUID,
    owner: str = "hypothesis_analyst_worker",
    claim_duration_seconds: int = 300,
    agent: Agent[HypothesisAnalystDependencies, HypothesisAnalystResult],
) -> EvaluationControlRecord:
    """Run the Analyst outside Evidence admission and publish through a fresh fence."""

    service = EvaluationTransitionService(session)
    claimed = service.claim_evaluation(
        evaluation_id=evaluation_id,
        owner=owner,
        claim_duration_seconds=claim_duration_seconds,
    )
    bundle = service.load_claimed_bundle(
        evaluation_id=evaluation_id,
        owner=owner,
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=claimed.bundle_digest,
    )

    try:
        result = evaluate_synthesis_bundle(bundle, agent=agent)
    except UnexpectedModelBehavior as exc:
        failure = EvaluationFailure(
            failure_reason=EvaluationFailureReason.MALFORMED_STRUCTURED_OUTPUT,
            message="Hypothesis Analyst exhausted bounded structured-output retries.",
            details=(type(exc).__name__, str(exc)),
        )
        return service.record_failure(
            evaluation_id=evaluation_id,
            owner=owner,
            fencing_epoch=claimed.fencing_epoch,
            source_bundle_digest=bundle.input_digest,
            failure=failure,
            retryable=True,
        )
    except (
        HypothesisAnalystConfigurationError,
        ModelAPIError,
        TimeoutError,
        ConnectionError,
    ) as exc:
        failure = EvaluationFailure(
            failure_reason=EvaluationFailureReason.TRANSIENT_PROVIDER_FAILURE,
            message="Hypothesis Analyst provider invocation failed transiently.",
            details=(type(exc).__name__, str(exc)),
        )
        return service.record_failure(
            evaluation_id=evaluation_id,
            owner=owner,
            fencing_epoch=claimed.fencing_epoch,
            source_bundle_digest=bundle.input_digest,
            failure=failure,
            retryable=True,
        )
    if isinstance(result, EvaluationFailure):
        return service.record_failure(
            evaluation_id=evaluation_id,
            owner=owner,
            fencing_epoch=claimed.fencing_epoch,
            source_bundle_digest=bundle.input_digest,
            failure=result,
            retryable=False,
        )
    if isinstance(result, DiscoveryProposal):
        return service.publish_proposal(
            evaluation_id=evaluation_id,
            owner=owner,
            fencing_epoch=claimed.fencing_epoch,
            source_bundle_digest=bundle.input_digest,
            proposal=result,
        )
    raise TypeError("PydanticAI returned an impossible untyped Hypothesis Analyst result.")
