"""Enumerations for CogniEDA analytical artifacts."""

from enum import StrEnum


class ProjectStatus(StrEnum):
    """Lifecycle states for a project."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class MemoryStatus(StrEnum):
    """Lifecycle states for memory items inside an active context frame."""

    ACTIVE = "active"
    PINNED = "pinned"
    TENTATIVE = "tentative"
    VALIDATED = "validated"
    REJECTED = "rejected"
    STALE = "stale"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    DEAD_END = "dead_end"
    OVERRULED = "overruled"
    NEEDS_REVIEW = "needs_review"
    UNRESOLVED = "unresolved"


class ContextMode(StrEnum):
    """Typed context views used to protect epistemic-role boundaries."""

    PLANNING = "planning"
    CONCLUSION = "conclusion"


class MemorySourceType(StrEnum):
    """Provenance sources for durable analytical memory items."""

    USER_CONFIRMATION = "user_confirmation"
    TOOL_RESULT = "tool_result"
    DATA_PROFILE = "data_profile"
    STATISTICAL_TEST = "statistical_test"
    AGENT_INFERENCE = "agent_inference"
    EXTERNAL_DOCUMENTATION = "external_documentation"
    CODE_INSPECTION = "code_inspection"
    PREVIOUS_FRAME = "previous_frame"
    VALIDATION_RESULT = "validation_result"


class InvalidationTrigger(StrEnum):
    """Events that make cached or summarized context stale."""

    DATASET_VERSION_CHANGE = "dataset_version_change"
    SOURCE_HASH_CHANGE = "source_hash_change"
    SCHEMA_CHANGE = "schema_change"
    METRIC_DEFINITION_CHANGE = "metric_definition_change"
    ASSUMPTION_REJECTED = "assumption_rejected"
    USER_OVERRULE = "user_overrule"
    TTL_EXPIRED = "ttl_expired"
    COMMIT_SHA_CHANGE = "commit_sha_change"
    MANUAL_REVIEW = "manual_review"


class SessionFrameStatus(StrEnum):
    """Operational states for a persisted context frame snapshot."""

    ACTIVE = "active"
    CHECKPOINT = "checkpoint"
    HANDOFF = "handoff"
    SUPERSEDED = "superseded"
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


class LineageOperationType(StrEnum):
    """Explicit transformation steps recorded in dataset lineage."""

    FILTER = "filter"
    ROW_DROP = "row_drop"
    COLUMN_DROP = "column_drop"
    IMPUTATION = "imputation"
    JOIN = "join"
    AGGREGATION = "aggregation"
    FEATURE_ENGINEERING = "feature_engineering"
    SAMPLING = "sampling"
    RENAME = "rename"
    CUSTOM = "custom"


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


class HypothesisEvidenceOutcome(StrEnum):
    """Typed outcome of one evidence record against one hypothesis."""

    SUPPORTS = "supports"
    REFUTES = "refutes"
    INCONCLUSIVE = "inconclusive"


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


class LogicalDtype(StrEnum):
    """Semantic column categories inferred during profiling."""

    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    CATEGORICAL = "categorical"
