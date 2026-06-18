"""Enumerations for CogniEDA analytical artifacts."""

from enum import StrEnum


class ProjectStatus(StrEnum):
    """Lifecycle states for a project."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class DatasetKind(StrEnum):
    """High-level lineage role for a dataset asset."""

    RAW = "raw"
    DERIVED = "derived"


class DatasetRole(StrEnum):
    """Analytical role a dataset plays within a project."""

    PRIMARY = "primary"
    REFERENCE = "reference"
    INTERMEDIATE = "intermediate"
    VALIDATION = "validation"


class DatasetSourceType(StrEnum):
    """Origin type for a dataset asset."""

    FILE = "file"
    DATABASE = "database"
    API = "api"
    QUERY = "query"
    MANUAL = "manual"
    GENERATED = "generated"


class DataProfileMethod(StrEnum):
    """Profiling strategies used to summarize a dataset."""

    INFERRED_SCHEMA = "inferred_schema"
    BASELINE_SUMMARY = "baseline_summary"
    DATA_QUALITY_SCAN = "data_quality_scan"
    CUSTOM = "custom"


class ConfidenceLevel(StrEnum):
    """Confidence levels for provisional analytical artifacts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AssumptionStatus(StrEnum):
    """Lifecycle states for an assumption."""

    ACTIVE = "active"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class HypothesisStatus(StrEnum):
    """Lifecycle states for a hypothesis."""

    PROPOSED = "proposed"
    PLANNED = "planned"
    VALIDATING = "validating"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"
    ARCHIVED = "archived"


class EvidenceType(StrEnum):
    """Evidence categories for analytical results."""

    PROFILE = "profile"
    SUMMARY_STATISTIC = "summary_statistic"
    STATISTICAL_TEST = "statistical_test"
    DATA_QUALITY_CHECK = "data_quality_check"
    VISUALIZATION = "visualization"
    MANUAL_REVIEW = "manual_review"
    EXPERIMENT_RESULT = "experiment_result"


class DecisionType(StrEnum):
    """Decision categories captured in the analytical decision log."""

    DATA_SELECTION = "data_selection"
    PREPROCESSING = "preprocessing"
    HYPOTHESIS_MANAGEMENT = "hypothesis_management"
    VALIDATION_STRATEGY = "validation_strategy"
    INTERPRETATION = "interpretation"
    REPORTING = "reporting"


class DecisionStatus(StrEnum):
    """Lifecycle states for a decision record."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class QualityFlagSeverity(StrEnum):
    """Severity levels for profile quality flags."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
