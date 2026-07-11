"""Enumerations for CogniEDA research-state objects and provenance records."""

from enum import StrEnum


class FirstClassObjectType(StrEnum):
    """The target CogniEDA first-class object set."""

    OBJECTIVE = "objective"
    DATA_PROFILE = "data_profile"
    ASSUMPTION = "assumption"
    TASK = "task"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    DISCOVERY = "discovery"
    SESSION_FRAME = "session_frame"


class MemoryStatus(StrEnum):
    """Lifecycle states for items selected into an active context frame."""

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
    DISCOVERY_SYNTHESIS = "discovery_synthesis"
    ANSWER = "answer"


class MemorySourceType(StrEnum):
    """Provenance sources for context-frame items."""

    USER_CONFIRMATION = "user_confirmation"
    TOOL_RESULT = "tool_result"
    DATA_PROFILE = "data_profile"
    STATISTICAL_TEST = "statistical_test"
    EXECUTION_RUN = "execution_run"
    ANALYSIS_FRAME = "analysis_frame"
    EXTERNAL_DOCUMENTATION = "external_documentation"
    CODE_INSPECTION = "code_inspection"
    PREVIOUS_FRAME = "previous_frame"
    VALIDATION_RESULT = "validation_result"


class InvalidationTrigger(StrEnum):
    """Events that make cached, summarized, or evidence-bound context stale."""

    DATA_PROFILE_SUPERSEDED = "data_profile_superseded"
    DATASET_VERSION_CHANGE = "dataset_version_change"
    SOURCE_HASH_CHANGE = "source_hash_change"
    SCHEMA_CHANGE = "schema_change"
    METRIC_DEFINITION_CHANGE = "metric_definition_change"
    METHOD_VERSION_CHANGE = "method_version_change"
    PARAMETER_CHANGE = "parameter_change"
    CODE_VERSION_CHANGE = "code_version_change"
    ENVIRONMENT_CHANGE = "environment_change"
    SEED_CHANGE = "seed_change"
    USER_OVERRULE = "user_overrule"
    TTL_EXPIRED = "ttl_expired"
    MANUAL_REVIEW = "manual_review"


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


class HypothesisStatus(StrEnum):
    """Lifecycle states for a Hypothesis test contract."""

    PROPOSED = "proposed"
    TESTING = "testing"
    COMPLETED = "completed"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"


class HypothesisEvidenceOutcome(StrEnum):
    """Typed outcome of one evidence record against one hypothesis."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


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
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


class DiscoveryEpistemicStatus(StrEnum):
    """Epistemic status of an evidence-bound Discovery claim."""

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class UserDecisionType(StrEnum):
    """Typed provenance categories for user decisions."""

    DATA_SELECTION = "data_selection"
    PREPROCESSING = "preprocessing"
    TASK_MANAGEMENT = "task_management"
    HYPOTHESIS_MANAGEMENT = "hypothesis_management"
    VALIDATION_STRATEGY = "validation_strategy"
    INTERPRETATION_REVIEW = "interpretation_review"
    REPORTING = "reporting"


class UserDecisionStatus(StrEnum):
    """Lifecycle states for user-decision provenance records."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class PlannerOperationType(StrEnum):
    """Typed pending mutations produced by planner nodes."""

    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    DELETE_TASK = "delete_task"
    CHANGE_TASK_STATE = "change_task_state"
    CREATE_OBJECTIVE_REVISION = "create_objective_revision"
    UPDATE_OBJECTIVE = "update_objective"
    CREATE_ASSUMPTION = "create_assumption"
    UPDATE_ASSUMPTION_STATE = "update_assumption_state"
    CREATE_HYPOTHESIS = "create_hypothesis"
    CREATE_EVIDENCE = "create_evidence"
    CREATE_DISCOVERY = "create_discovery"
    UPDATE_SESSION_FRAME = "update_session_frame"
    FLAG_OBJECT = "flag_object"


class PlannerNodeName(StrEnum):
    """Planner nodes allowed to produce pending state-transition operations."""

    PROPOSE_QUESTIONS = "propose_questions"
    EXPAND_PLAN = "expand_plan"
    MANAGE_TASKS = "manage_tasks"
    PREPARE_EXECUTION = "prepare_execution"
    REVIEW_EXECUTION = "review_execution"
    REVIEW_CONFLICTS = "review_conflicts"
    MANAGE_OBJECTIVE = "manage_objective"
    MANAGE_ASSUMPTIONS = "manage_assumptions"
    PROCESS_DECISION = "process_decision"


class PlannerOperationApprovalState(StrEnum):
    """Approval and commit lifecycle for PlannerOperation records."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMMITTED = "committed"
    FAILED = "failed"


class SessionFrameStatus(StrEnum):
    """Operational states for a persisted context frame snapshot."""

    ACTIVE = "active"
    CHECKPOINT = "checkpoint"
    HANDOFF = "handoff"
    SUPERSEDED = "superseded"
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
