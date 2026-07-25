"""Lifecycle enums for Evidence-owned canonical objects."""

from enum import StrEnum


class EvidenceType(StrEnum):
    """Evidence categories for directly observed analytical results."""

    PROFILE = "profile"
    SUMMARY_STATISTIC = "summary_statistic"
    STATISTICAL_TEST = "statistical_test"
    DATA_QUALITY_CHECK = "data_quality_check"
    VISUALIZATION = "visualization"
    MANUAL_REVIEW = "manual_review"
    EXPERIMENT_RESULT = "experiment_result"


class EvidenceLifecycleState(StrEnum):
    """Allowed lifecycle states for immutable Evidence records."""

    ACTIVE = "active"
    HISTORICALLY_SCOPED = "historically_scoped"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"
