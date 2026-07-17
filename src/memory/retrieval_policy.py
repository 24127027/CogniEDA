"""Pure retrieval type-safety policy for context assembly.

This module is a policy boundary only. It does not retrieve objects, query the
database, build prompts, or refresh SessionFrames.
"""

from __future__ import annotations

from enum import StrEnum

from schemas.enums import (
    AssumptionStatus,
    ContextMode,
    DataProfileLifecycleState,
    DiscoveryLifecycleState,
    EvidenceLifecycleState,
    FirstClassObjectType,
    HypothesisStatus,
    MemoryStatus,
    ObjectiveStatus,
    SessionFrameStatus,
    TaskLifecycleState,
)

type RetrievalObjectType = FirstClassObjectType | str
type ContextModeInput = ContextMode | str
type LifecycleState = (
    ObjectiveStatus
    | DataProfileLifecycleState
    | AssumptionStatus
    | TaskLifecycleState
    | HypothesisStatus
    | EvidenceLifecycleState
    | DiscoveryLifecycleState
    | SessionFrameStatus
    | MemoryStatus
    | str
    | None
)

_CACHE_OBJECT_TYPES = {
    "cache",
    "tool_result_cache",
    "tool_result_cache_summary",
    "evidence_cache",
    "evidence_cache_entry",
}
_GENERATED_VIEW_OBJECT_TYPES = {"generated_view", "generated_summary"}
_STALE_CONTEXT_OBJECT_TYPES = {"stale_context", "stale_context_marker"}
_PROVENANCE_REFERENCE_TYPES = {
    "analysis_frame",
    "analysis_frame_ref",
    "execution_run",
    "execution_run_ref",
}
_KNOWN_NON_FCO_OBJECT_TYPES = (
    _CACHE_OBJECT_TYPES
    | _GENERATED_VIEW_OBJECT_TYPES
    | _STALE_CONTEXT_OBJECT_TYPES
    | _PROVENANCE_REFERENCE_TYPES
)
_KNOWN_CONTEXT_MODES = {mode.value for mode in ContextMode}
_KNOWN_FCO_TYPES = {object_type.value for object_type in FirstClassObjectType}

_ACTIVE_MEMORY_STATES = {
    MemoryStatus.ACTIVE.value,
    MemoryStatus.PINNED.value,
    MemoryStatus.VALIDATED.value,
}
_ACTIVE_OR_REVIEW_MEMORY_STATES = _ACTIVE_MEMORY_STATES | {
    MemoryStatus.NEEDS_REVIEW.value,
}

_CONTEXT_LABELS = {
    ContextMode.PLANNING.value: "Planning Context",
    ContextMode.ANSWER.value: "Answer Context",
    ContextMode.CONCLUSION.value: "Conclusion Context",
    ContextMode.DISCOVERY_SYNTHESIS.value: "Discovery Synthesis Context",
}


def is_allowed_in_context(
    object_type: RetrievalObjectType,
    lifecycle_state: LifecycleState,
    context_mode: ContextModeInput,
) -> bool:
    """Return whether a retrieval candidate may enter the requested context."""

    return exclusion_reason(object_type, lifecycle_state, context_mode) is None


def exclusion_reason(
    object_type: RetrievalObjectType,
    lifecycle_state: LifecycleState,
    context_mode: ContextModeInput,
) -> str | None:
    """Return a concise reason when a candidate is excluded from a context."""

    object_key = _normalize_token(object_type)
    state_key = _normalize_state(lifecycle_state)
    mode_key = _normalize_token(context_mode)
    context_label = _CONTEXT_LABELS.get(mode_key, f"{mode_key} context")

    if mode_key not in _KNOWN_CONTEXT_MODES:
        return f"Unknown context mode '{mode_key}' is not allowed."

    if object_key in _CACHE_OBJECT_TYPES:
        return f"Cache records are not allowed in {context_label}."
    if object_key in _GENERATED_VIEW_OBJECT_TYPES:
        return f"Generated views are runtime outputs and are not allowed in {context_label}."
    if object_key in _STALE_CONTEXT_OBJECT_TYPES:
        if mode_key == ContextMode.PLANNING.value:
            return None
        return f"Stale context markers are not allowed in {context_label}."
    if object_key in _PROVENANCE_REFERENCE_TYPES:
        return _provenance_reference_exclusion_reason(state_key, mode_key, context_label)

    if object_key not in _KNOWN_FCO_TYPES:
        return f"Unknown object type '{object_key}' is not allowed in {context_label}."

    if object_key == FirstClassObjectType.OBJECTIVE.value:
        return _objective_exclusion_reason(state_key, mode_key, context_label)
    if object_key == FirstClassObjectType.DATA_PROFILE.value:
        return _data_profile_exclusion_reason(state_key, mode_key, context_label)
    if object_key == FirstClassObjectType.ASSUMPTION.value:
        return _assumption_exclusion_reason(state_key, mode_key, context_label)
    if object_key == FirstClassObjectType.TASK.value:
        return _task_exclusion_reason(state_key, mode_key, context_label)
    if object_key == FirstClassObjectType.HYPOTHESIS.value:
        return _hypothesis_exclusion_reason(state_key, mode_key, context_label)
    if object_key == FirstClassObjectType.EVIDENCE.value:
        return _evidence_exclusion_reason(state_key, mode_key, context_label)
    if object_key == FirstClassObjectType.DISCOVERY.value:
        return _discovery_exclusion_reason(state_key, mode_key, context_label)
    if object_key == FirstClassObjectType.SESSION_FRAME.value:
        return _session_frame_exclusion_reason(state_key, mode_key, context_label)

    return f"{object_key} is not allowed in {context_label}."


def _objective_exclusion_reason(
    state_key: str | None,
    mode_key: str,
    context_label: str,
) -> str | None:
    if (
        mode_key in {ContextMode.PLANNING.value, ContextMode.ANSWER.value}
        and state_key == ObjectiveStatus.ACTIVE.value
    ):
        return None
    return _state_not_allowed("Objective", state_key, context_label)


def _data_profile_exclusion_reason(
    state_key: str | None,
    _mode_key: str,
    context_label: str,
) -> str | None:
    if state_key in _ACTIVE_MEMORY_STATES | {DataProfileLifecycleState.ACTIVE.value}:
        return None
    if state_key == DataProfileLifecycleState.SUPERSEDED.value:
        return f"Superseded DataProfile is not current enough for {context_label}."
    return _state_not_allowed("DataProfile", state_key, context_label)


def _assumption_exclusion_reason(
    state_key: str | None,
    mode_key: str,
    context_label: str,
) -> str | None:
    if mode_key == ContextMode.PLANNING.value and state_key == AssumptionStatus.ACTIVE.value:
        return None
    if mode_key in {
        ContextMode.ANSWER.value,
        ContextMode.CONCLUSION.value,
        ContextMode.DISCOVERY_SYNTHESIS.value,
    }:
        return f"Assumption is planning-only and cannot enter {context_label}."
    return _state_not_allowed("Assumption", state_key, context_label)


def _task_exclusion_reason(
    state_key: str | None,
    mode_key: str,
    context_label: str,
) -> str | None:
    if mode_key in {ContextMode.PLANNING.value, ContextMode.ANSWER.value} and state_key in {
        TaskLifecycleState.PROPOSED.value,
        TaskLifecycleState.ACTIVE.value,
        TaskLifecycleState.PAUSED.value,
    }:
        return None
    if state_key == TaskLifecycleState.REJECTED.value:
        return f"Rejected Task is workflow state and cannot enter {context_label}."
    if mode_key in {ContextMode.CONCLUSION.value, ContextMode.DISCOVERY_SYNTHESIS.value}:
        return f"Task is workflow state and cannot enter {context_label}."
    return _state_not_allowed("Task", state_key, context_label)


def _hypothesis_exclusion_reason(
    state_key: str | None,
    mode_key: str,
    context_label: str,
) -> str | None:
    if mode_key in {ContextMode.PLANNING.value, ContextMode.ANSWER.value} and state_key in {
        HypothesisStatus.PROPOSED.value,
        HypothesisStatus.TESTING.value,
    }:
        return None
    if mode_key in {ContextMode.CONCLUSION.value, ContextMode.DISCOVERY_SYNTHESIS.value}:
        if state_key == HypothesisStatus.TESTING.value:
            return None
        if state_key == HypothesisStatus.CONFIRMED.value:
            return f"Completed Hypothesis is excluded by default from {context_label}."
    if state_key == HypothesisStatus.CONFIRMED.value:
        return f"Completed Hypothesis is excluded by default from {context_label}."
    return _state_not_allowed("Hypothesis", state_key, context_label)


def _evidence_exclusion_reason(
    state_key: str | None,
    mode_key: str,
    context_label: str,
) -> str | None:
    if (
        mode_key == ContextMode.PLANNING.value
        and state_key
        in {
            EvidenceLifecycleState.ACTIVE.value,
            EvidenceLifecycleState.HISTORICALLY_SCOPED.value,
        }
        | _ACTIVE_MEMORY_STATES
    ):
        return None
    if state_key in _ACTIVE_MEMORY_STATES | {EvidenceLifecycleState.ACTIVE.value}:
        return None
    if state_key == EvidenceLifecycleState.HISTORICALLY_SCOPED.value:
        return f"Historically scoped Evidence is not normal current Evidence for {context_label}."
    if state_key == EvidenceLifecycleState.SUPERSEDED.value:
        return f"Superseded Evidence is not allowed in {context_label}."
    if state_key == EvidenceLifecycleState.INVALIDATED.value:
        return f"Invalidated Evidence is not allowed in {context_label}."
    return _state_not_allowed("Evidence", state_key, context_label)


def _discovery_exclusion_reason(
    state_key: str | None,
    mode_key: str,
    context_label: str,
) -> str | None:
    if (
        mode_key == ContextMode.PLANNING.value
        and state_key
        in {
            DiscoveryLifecycleState.ACTIVE.value,
            DiscoveryLifecycleState.FLAGGED.value,
        }
        | _ACTIVE_OR_REVIEW_MEMORY_STATES
    ):
        return None
    if mode_key == ContextMode.ANSWER.value and state_key in (
        _ACTIVE_MEMORY_STATES | {DiscoveryLifecycleState.ACTIVE.value}
    ):
        return None
    if mode_key in {ContextMode.CONCLUSION.value, ContextMode.DISCOVERY_SYNTHESIS.value}:
        return (
            f"Existing Discovery is excluded from {context_label}; synthesize from "
            "Hypothesis, current DataProfile, provenance, and valid Evidence."
        )
    if state_key == DiscoveryLifecycleState.FLAGGED.value:
        return f"Flagged Discovery requires review before entering {context_label}."
    if state_key in {
        DiscoveryLifecycleState.INVALIDATED.value,
        DiscoveryLifecycleState.DEPRECATED.value,
    }:
        return f"{state_key} Discovery is not allowed in {context_label}."
    return _state_not_allowed("Discovery", state_key, context_label)


def _session_frame_exclusion_reason(
    state_key: str | None,
    mode_key: str,
    context_label: str,
) -> str | None:
    if mode_key in {ContextMode.PLANNING.value, ContextMode.ANSWER.value} and state_key in {
        SessionFrameStatus.ACTIVE.value,
        SessionFrameStatus.CHECKPOINT.value,
        SessionFrameStatus.HANDOFF.value,
    }:
        return None
    return _state_not_allowed("SessionFrame", state_key, context_label)


def _provenance_reference_exclusion_reason(
    state_key: str | None,
    mode_key: str,
    context_label: str,
) -> str | None:
    if mode_key == ContextMode.PLANNING.value:
        return None
    if mode_key in {
        ContextMode.ANSWER.value,
        ContextMode.CONCLUSION.value,
        ContextMode.DISCOVERY_SYNTHESIS.value,
    } and (state_key is None or state_key in _ACTIVE_MEMORY_STATES):
        return None
    return _state_not_allowed("Provenance reference", state_key, context_label)


def _state_not_allowed(
    object_label: str,
    state_key: str | None,
    context_label: str,
) -> str:
    state_label = state_key if state_key is not None else "<missing>"
    return f"{object_label} state '{state_label}' is not allowed in {context_label}."


def _normalize_state(lifecycle_state: LifecycleState) -> str | None:
    if lifecycle_state is None:
        return None
    return _normalize_token(lifecycle_state)


def _normalize_token(value: RetrievalObjectType | ContextModeInput | LifecycleState) -> str:
    if isinstance(value, StrEnum):
        raw = value.value
    else:
        raw = str(value)
    return raw.strip().lower().replace("-", "_")


# TODO: Add explicit audit/historical context modes before permitting historical
# Evidence outside planning.
# TODO: Replace string adapters for non-FCO provenance/cache markers when those
# records gain dedicated retrieval candidate types.
