from __future__ import annotations

from uuid import uuid4

from db.models import DataProfileRecord, DiscoveryRecord, HypothesisRecord, TaskRecord
from memory.retrieval_engine import DiscoveryRetrievalEngine
from memory.semantic_scorer import LexicalScorer
from schemas.artifacts import SessionFrame
from schemas.enums import DataProfileMethod, DiscoveryEpistemicStatus, DiscoveryLifecycleState
from schemas.retrieval import RetrievalRequest


def _add_discovery(
    db_session,
    *,
    statement: str,
    lifecycle_state: DiscoveryLifecycleState = DiscoveryLifecycleState.ACTIVE,
    review_reasons: list[str] | None = None,
) -> DiscoveryRecord:
    profile = DataProfileRecord(
        dataset_path=f"data/{uuid4()}.csv",
        method=DataProfileMethod.BASELINE_SUMMARY,
        row_count=1,
        column_count=1,
    )
    db_session.add(profile)
    db_session.flush()
    task = TaskRecord(
        title="Discovery source",
        description="Source task for bounded retrieval tests.",
        profile_id=profile.profile_id,
    )
    db_session.add(task)
    db_session.flush()
    hypothesis_id = uuid4()
    evidence_id = uuid4()
    db_session.add(
        HypothesisRecord(
            hypothesis_id=hypothesis_id,
            task_id=task.task_id,
            profile_id=profile.profile_id,
            statement="Test statement",
            scope="current dataset",
            validation_method="deterministic test",
            evidence_expectation="A bounded result.",
        )
    )
    db_session.flush()
    discovery = DiscoveryRecord(
        hypothesis_id=hypothesis_id,
        evidence_ids=[str(evidence_id)],
        claim={"statement": statement, "scope": "current dataset"},
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="current dataset",
        validity_basis={
            "data_profile_id": str(profile.profile_id),
            "analysis_frame_refs": ["frame:bounded"],
            "hypothesis_id": str(hypothesis_id),
            "evidence_ids": [str(evidence_id)],
            "method": "deterministic test",
            "decision_rule": "p < 0.05",
            "assumptions_excluded_from_inference": True,
        },
        lifecycle_state=lifecycle_state,
        review_reasons=review_reasons or [],
    )
    db_session.add(discovery)
    return discovery


def test_retrieval_is_bounded_lifecycle_aware_and_frame_ranked(db_session) -> None:
    framed = _add_discovery(db_session, statement="A prior quality finding")
    lexical = _add_discovery(db_session, statement="Revenue is associated with churn")
    invalid = _add_discovery(
        db_session,
        statement="Revenue finding that must not be reused",
        lifecycle_state=DiscoveryLifecycleState.INVALIDATED,
    )
    db_session.commit()

    result = DiscoveryRetrievalEngine(db_session).retrieve(
        RetrievalRequest(query_text="revenue", max_results=2, candidate_pool_limit=3),
        SessionFrame(
            frame_topic="retrieval",
            objective_snapshot="Plan a bounded follow-up.",
            relevant_discovery_refs=[framed.discovery_id],
        ),
    )

    assert [item.discovery_id for item in result.candidates] == [
        framed.discovery_id,
        lexical.discovery_id,
    ]
    assert result.candidates[0].inclusion_reasons == ["Included by the active SessionFrame."]
    assert all(item.discovery_id != invalid.discovery_id for item in result.candidates)
    assert result.exclusion_notes == [
        "A Discovery candidate is excluded: invalidated Discovery is not allowed "
        "in Planning Context."
    ]


def test_retrieval_keeps_flagged_discoveries_visible_with_review_warning(db_session) -> None:
    flagged = _add_discovery(
        db_session,
        statement="Revenue data needs follow-up review",
        lifecycle_state=DiscoveryLifecycleState.FLAGGED,
        review_reasons=["Evidence was superseded."],
    )
    db_session.commit()

    result = DiscoveryRetrievalEngine(db_session).retrieve(
        RetrievalRequest(query_text="revenue", max_results=1),
    )

    assert [item.discovery_id for item in result.candidates] == [flagged.discovery_id]
    assert result.candidates[0].flags == ["Flagged for review: Evidence was superseded."]


def test_lexical_scorer_is_local_and_deterministic() -> None:
    scorer = LexicalScorer()

    assert scorer.score("Revenue churn", "Revenue and churn") == 2 / 3
    assert scorer.score("Revenue", "quality") == 0.0
