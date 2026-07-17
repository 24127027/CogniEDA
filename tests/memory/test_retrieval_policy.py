from __future__ import annotations

import pytest
from memory.retrieval_policy import exclusion_reason, is_allowed_in_context
from schemas.enums import (
    AssumptionStatus,
    ContextMode,
    DataProfileLifecycleState,
    DiscoveryLifecycleState,
    EvidenceLifecycleState,
    FirstClassObjectType,
    HypothesisStatus,
    TaskLifecycleState,
)


def assert_excluded(
    object_type: FirstClassObjectType | str,
    lifecycle_state: object,
    context_mode: ContextMode,
) -> str:
    reason = exclusion_reason(object_type, lifecycle_state, context_mode)

    assert reason is not None
    assert reason
    assert not is_allowed_in_context(object_type, lifecycle_state, context_mode)
    return reason


@pytest.mark.parametrize(
    ("object_type", "lifecycle_state"),
    [
        (FirstClassObjectType.ASSUMPTION, AssumptionStatus.ACTIVE),
        (FirstClassObjectType.DISCOVERY, DiscoveryLifecycleState.ACTIVE),
        (FirstClassObjectType.HYPOTHESIS, HypothesisStatus.COMPLETED),
        (FirstClassObjectType.TASK, TaskLifecycleState.REJECTED),
        (FirstClassObjectType.DATA_PROFILE, DataProfileLifecycleState.SUPERSEDED),
        (FirstClassObjectType.EVIDENCE, EvidenceLifecycleState.HISTORICALLY_SCOPED),
        (FirstClassObjectType.EVIDENCE, EvidenceLifecycleState.SUPERSEDED),
        (FirstClassObjectType.EVIDENCE, EvidenceLifecycleState.INVALIDATED),
    ],
)
def test_discovery_synthesis_excludes_unsafe_roles_and_states(
    object_type: FirstClassObjectType,
    lifecycle_state: object,
) -> None:
    assert_excluded(object_type, lifecycle_state, ContextMode.DISCOVERY_SYNTHESIS)


@pytest.mark.parametrize(
    ("object_type", "lifecycle_state"),
    [
        (FirstClassObjectType.ASSUMPTION, AssumptionStatus.ACTIVE),
        (FirstClassObjectType.DISCOVERY, DiscoveryLifecycleState.ACTIVE),
    ],
)
def test_conclusion_context_excludes_assumptions_and_existing_discoveries(
    object_type: FirstClassObjectType,
    lifecycle_state: object,
) -> None:
    assert_excluded(object_type, lifecycle_state, ContextMode.CONCLUSION)


def test_planning_context_allows_active_assumption() -> None:
    assert is_allowed_in_context(
        FirstClassObjectType.ASSUMPTION,
        AssumptionStatus.ACTIVE,
        ContextMode.PLANNING,
    )


def test_answer_context_allows_active_discovery() -> None:
    assert is_allowed_in_context(
        FirstClassObjectType.DISCOVERY,
        DiscoveryLifecycleState.ACTIVE,
        ContextMode.ANSWER,
    )


def test_answer_context_excludes_historically_scoped_evidence_by_default() -> None:
    reason = assert_excluded(
        FirstClassObjectType.EVIDENCE,
        EvidenceLifecycleState.HISTORICALLY_SCOPED,
        ContextMode.ANSWER,
    )

    assert "Historically scoped Evidence" in reason


def test_policy_returns_explicit_exclusion_reasons_for_safety_critical_cases() -> None:
    safety_critical_cases = [
        (
            FirstClassObjectType.ASSUMPTION,
            AssumptionStatus.ACTIVE,
            ContextMode.DISCOVERY_SYNTHESIS,
        ),
        (
            FirstClassObjectType.DISCOVERY,
            DiscoveryLifecycleState.ACTIVE,
            ContextMode.CONCLUSION,
        ),
        (
            FirstClassObjectType.EVIDENCE,
            EvidenceLifecycleState.INVALIDATED,
            ContextMode.DISCOVERY_SYNTHESIS,
        ),
        (
            FirstClassObjectType.DATA_PROFILE,
            DataProfileLifecycleState.SUPERSEDED,
            ContextMode.DISCOVERY_SYNTHESIS,
        ),
    ]

    for object_type, lifecycle_state, context_mode in safety_critical_cases:
        assert_excluded(object_type, lifecycle_state, context_mode)
