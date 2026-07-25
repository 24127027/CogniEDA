"""Lifecycle enums for research-owned canonical objects."""

from enum import StrEnum


class ObjectiveStatus(StrEnum):
    """Lifecycle states for an Objective."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DataProfileLifecycleState(StrEnum):
    """Lifecycle states for immutable DataProfile snapshots."""

    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"


class DatasetSourceType(StrEnum):
    """Origin type for a profiled dataset source."""

    FILE = "file"
    DATABASE = "database"
    API = "api"
    QUERY = "query"
    MANUAL = "manual"
    GENERATED = "generated"


class LineageOperationType(StrEnum):
    """Explicit transformation steps recorded in profile lineage."""

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
    """Profiling strategies used to summarize a dataset version."""

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
    """Lifecycle states for an Assumption."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    FLAGGED = "flagged"
    RETAINED = "retained"
    REPLACED = "replaced"
    ARCHIVED = "archived"


class AssumptionSource(StrEnum):
    """Source categories for planning-only assumptions."""

    USER = "user"
    DOMAIN_EXPERTISE = "domain_expertise"
    LITERATURE = "literature"
    PREVIOUS_PROJECT = "previous_project"
    SYSTEM_SUGGESTED = "system_suggested"


class AssumptionTestability(StrEnum):
    """Admission categories for claims proposed as assumptions."""

    UNTESTABLE_IN_PROJECT = "untestable_in_project"
    TESTABLE_CLAIM_REJECTED_AS_ASSUMPTION = "testable_claim_rejected_as_assumption"


class TaskLifecycleState(StrEnum):
    """Durable Task lifecycle states."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TaskKind(StrEnum):
    """Task categories used to guard hypothesis creation."""

    ANALYTICAL = "analytical"
    ORGANIZING = "organizing"
    REVIEW = "review"


class TaskDependencyType(StrEnum):
    """Dependency semantics between tasks."""

    PREREQUISITE = "prerequisite"
    OPTIONAL = "optional"
    BLOCKED = "blocked"
    ALTERNATIVE = "alternative"


class HypothesisStatus(StrEnum):
    """Lifecycle states for a Hypothesis test contract."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    TESTING = "testing"
    AWAITING_ADDITIONAL_EVIDENCE = "awaiting_additional_evidence"
    READY_FOR_EVALUATION = "ready_for_evaluation"
    EVALUATED = "evaluated"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class HypothesisEvidenceOutcome(StrEnum):
    """Typed outcome of one evidence record against one hypothesis."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class SessionFrameStatus(StrEnum):
    """Operational states for a persisted context frame snapshot."""

    ACTIVE = "active"
    CHECKPOINT = "checkpoint"
    HANDOFF = "handoff"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class AnalysisIntent(StrEnum):
    """Epistemic intent for an analytical claim or contract."""

    EXPLORATORY = "exploratory"
    CONFIRMATORY = "confirmatory"
    REPLICATION = "replication"
