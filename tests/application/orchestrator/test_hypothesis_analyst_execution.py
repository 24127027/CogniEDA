"""Real PydanticAI, validation, publication, and stale-bundle evaluation tests."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError
from pydantic_ai.models.test import TestModel
from sqlmodel import select

from agents.executor.hypothesis_analyst.nodes import build_hypothesis_analyst_agent
from application.orchestrator.evaluation_transition_service import (
    EvaluationConflictError,
    EvaluationTransitionService,
    StaleEvaluationOwnerError,
)
from application.orchestrator.evaluator_runner import run_evaluation_attempt
from application.orchestrator.synthesis_bundle import build_synthesis_bundle
from db.models import DiscoveryRecord, HypothesisRecord, TaskRecord
from db.session import get_session
from package2_helpers import (
    persist_package2_lineage,
    propagate_validity_for_test,
    proposal_for_bundle,
)
from schemas.common import DiscoveryClaim, EvaluationThresholds, MethodParameter
from schemas.enums import (
    DiscoveryEpistemicStatus,
    EvaluationControlState,
    HypothesisStatus,
    TaskLifecycleState,
    ValidityEventType,
    ValiditySourceType,
)
from schemas.specialist_contracts import (
    DiscoveryProposal,
    EvaluationFailure,
    EvaluationFailureReason,
    HypothesisAnalystResult,
    compute_proposal_digest,
    validate_proposal_against_bundle,
)


def _agent_for(result: DiscoveryProposal | EvaluationFailure):
    return build_hypothesis_analyst_agent(
        model=TestModel(
            custom_output_args=result.model_dump(mode="json"),
            seed=1 if isinstance(result, EvaluationFailure) else 0,
        )
    )


def test_successful_typed_agent_run_publishes_proposal_only(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle)
    control, _ = EvaluationTransitionService(db_session).enqueue_evaluation(
        hypothesis_id=lineage.hypothesis_id
    )

    published = run_evaluation_attempt(
        db_session,
        evaluation_id=control.evaluation_id,
        owner="analyst-worker",
        agent=_agent_for(proposal),
    )

    assert published.state == EvaluationControlState.PROPOSAL_READY
    assert published.serialized_proposal == proposal.model_dump(mode="json")
    assert published.proposal_digest == compute_proposal_digest(proposal, bundle.input_digest)
    assert db_session.exec(select(DiscoveryRecord)).all() == []
    hypothesis = db_session.get(HypothesisRecord, lineage.hypothesis_id)
    task = db_session.get(TaskRecord, lineage.task_id)
    assert hypothesis is not None and hypothesis.status == HypothesisStatus.READY_FOR_EVALUATION
    assert task is not None and task.lifecycle_state == TaskLifecycleState.ACTIVE


def test_typed_evaluation_failure_is_durable_and_not_a_scientific_outcome(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    failure = EvaluationFailure(
        failure_reason=EvaluationFailureReason.INVALID_LINEAGE,
        message="The protected lineage is not identifiable.",
    )
    control, _ = EvaluationTransitionService(db_session).enqueue_evaluation(
        hypothesis_id=lineage.hypothesis_id
    )

    failed = run_evaluation_attempt(
        db_session,
        evaluation_id=control.evaluation_id,
        agent=_agent_for(failure),
    )

    assert failed.state == EvaluationControlState.NON_RETRYABLE_FAILED
    assert failed.serialized_failure == failure.model_dump(mode="json")
    assert failed.serialized_proposal is None


def test_invalid_structured_proposal_exhausts_bounded_retries_as_typed_failure(
    db_session,
) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle)
    foreign_id = uuid4()
    invalid = proposal.model_copy(
        update={
            "evidence_ids": [foreign_id],
            "validity_basis": proposal.validity_basis.model_copy(
                update={"evidence_ids": [foreign_id]}
            ),
        }
    )
    control, _ = EvaluationTransitionService(db_session).enqueue_evaluation(
        hypothesis_id=lineage.hypothesis_id
    )

    failed = run_evaluation_attempt(
        db_session,
        evaluation_id=control.evaluation_id,
        agent=_agent_for(invalid),
    )

    assert failed.state == EvaluationControlState.RETRYABLE_FAILED
    assert failed.failure_reason == EvaluationFailureReason.MALFORMED_STRUCTURED_OUTPUT.value
    assert failed.serialized_proposal is None


@pytest.mark.parametrize(
    "mutation",
    [
        "hypothesis",
        "evidence",
        "scope",
        "profile",
        "frames",
        "method",
        "parameters",
        "decision_rule",
        "invalidators",
        "limitations",
    ],
)
def test_application_validation_independently_rejects_contract_drift(
    db_session, mutation: str
) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle)
    basis = proposal.validity_basis
    updates: dict[str, Any] = {}
    proposal_updates: dict[str, Any] = {}
    if mutation == "hypothesis":
        updates["hypothesis_id"] = uuid4()
    elif mutation == "evidence":
        foreign = uuid4()
        proposal_updates["evidence_ids"] = [foreign]
        updates["evidence_ids"] = [foreign]
    elif mutation == "scope":
        proposal_updates["scope"] = "expanded scope"
        proposal_updates["claim"] = proposal.claim.model_copy(update={"scope": "expanded scope"})
    elif mutation == "profile":
        updates["data_profile_id"] = uuid4()
    elif mutation == "frames":
        updates["analysis_frame_refs"] = ["foreign-frame"]
    elif mutation == "method":
        updates["method"] = "invented_method"
    elif mutation == "parameters":
        updates["parameters"] = [MethodParameter(name="alpha", value=0.01)]
    elif mutation == "decision_rule":
        updates["decision_rule"] = EvaluationThresholds(p_value=0.01)
    elif mutation == "invalidators":
        updates["invalidators"] = ["invented invalidator"]
    else:
        proposal_updates["limitations"] = ()
    if updates:
        proposal_updates["validity_basis"] = basis.model_copy(update=updates)
    candidate = proposal.model_copy(update=proposal_updates)

    with pytest.raises(ValueError):
        validate_proposal_against_bundle(candidate, bundle)


def test_fail_to_reject_requires_structured_inconclusive_or_insufficient_status(
    db_session,
) -> None:
    lineage = persist_package2_lineage(db_session, p_value=0.4)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)

    with pytest.raises(ValueError, match="Fail-to-reject"):
        validate_proposal_against_bundle(proposal_for_bundle(bundle), bundle)
    validate_proposal_against_bundle(
        proposal_for_bundle(
            bundle,
            epistemic_status=DiscoveryEpistemicStatus.INCONCLUSIVE,
        ),
        bundle,
    )
    with pytest.raises(ValidationError):
        DiscoveryClaim(
            statement="There is no relationship.",
            scope=bundle.hypothesis.scope,
            result="p-value exceeded the threshold.",
        )


def test_proposal_digest_covers_all_scientific_content_but_no_model_metadata(
    db_session,
) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle)
    baseline = compute_proposal_digest(proposal, bundle.input_digest)
    variants = (
        proposal.model_copy(
            update={
                "claim": proposal.claim.model_copy(update={"result": "Changed interpretation."})
            }
        ),
        proposal.model_copy(update={"limitations": ("Changed limitation.",)}),
        proposal.model_copy(
            update={
                "validity_basis": proposal.validity_basis.model_copy(
                    update={"uncertainty": "Changed uncertainty."}
                )
            }
        ),
        proposal.model_copy(update={"epistemic_status": DiscoveryEpistemicStatus.CONTRADICTED}),
    )
    assert all(
        compute_proposal_digest(variant, bundle.input_digest) != baseline for variant in variants
    )
    assert compute_proposal_digest(proposal, bundle.input_digest) == baseline


def test_exact_proposal_replay_is_idempotent_changed_replay_is_conflict(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle)
    service = EvaluationTransitionService(db_session)
    control, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claim = service.claim_evaluation(evaluation_id=control.evaluation_id, owner="worker")
    first = service.publish_proposal(
        evaluation_id=control.evaluation_id,
        owner="worker",
        fencing_epoch=claim.fencing_epoch,
        source_bundle_digest=bundle.input_digest,
        proposal=proposal,
    )
    replay = service.publish_proposal(
        evaluation_id=control.evaluation_id,
        owner="worker",
        fencing_epoch=claim.fencing_epoch,
        source_bundle_digest=bundle.input_digest,
        proposal=proposal,
    )
    assert replay.evaluation_id == first.evaluation_id

    changed = proposal.model_copy(
        update={"claim": proposal.claim.model_copy(update={"result": "Changed result."})}
    )
    with pytest.raises(EvaluationConflictError):
        service.publish_proposal(
            evaluation_id=control.evaluation_id,
            owner="worker",
            fencing_epoch=claim.fencing_epoch,
            source_bundle_digest=bundle.input_digest,
            proposal=changed,
        )


def test_evidence_invalidation_during_model_call_fences_publication(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle)
    database_url = str(db_session.get_bind().url)

    class InvalidatingModel(TestModel):
        async def request(self, messages, model_settings, model_request_parameters):
            mutation_session = get_session(database_url)
            try:
                propagate_validity_for_test(
                    mutation_session,
                    source_type=ValiditySourceType.EVIDENCE,
                    source_id=lineage.evidence_id,
                    event_type=ValidityEventType.EVIDENCE_INVALIDATION,
                    reason="Concurrent invalidation during Analyst execution.",
                    idempotency_key="analyst-model-call-invalidation",
                )
            finally:
                mutation_session.close()
            return await super().request(messages, model_settings, model_request_parameters)

    agent = build_hypothesis_analyst_agent(
        model=InvalidatingModel(custom_output_args=proposal.model_dump(mode="json"))
    )
    control, _ = EvaluationTransitionService(db_session).enqueue_evaluation(
        hypothesis_id=lineage.hypothesis_id
    )

    with pytest.raises(StaleEvaluationOwnerError):
        run_evaluation_attempt(
            db_session,
            evaluation_id=control.evaluation_id,
            agent=agent,
        )
    db_session.refresh(control)
    assert control.state == EvaluationControlState.INVALIDATED
    assert control.serialized_proposal is None


def test_result_union_rejects_durable_or_lifecycle_authority_fields() -> None:
    payload = {
        "status": "proposed",
        "claim": {"statement": "Scoped claim.", "scope": "scope", "result": "result"},
        "epistemic_status": "supported",
        "scope": "scope",
        "evidence_ids": [str(uuid4())],
        "validity_basis": {
            "data_profile_id": str(uuid4()),
            "analysis_frame_refs": ["frame"],
            "hypothesis_id": str(uuid4()),
            "evidence_ids": [str(uuid4())],
            "method": "method",
            "decision_rule": {},
            "strength": "moderate",
            "uncertainty": "uncertain",
        },
        "discovery_id": str(uuid4()),
        "task_status": "completed",
    }
    with pytest.raises(ValidationError):
        TypeAdapter(HypothesisAnalystResult).validate_python(payload)
