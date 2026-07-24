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


class ExecutionRunStatus(StrEnum):
    """Lifecycle states for an ExecutionRun."""

    PENDING_APPROVAL = "pending_approval"
    ADMITTED = "admitted"
    DISPATCH_CLAIMED = "dispatch_claimed"
    RUNNING = "running"
    RESULT_RECEIVED = "result_received"
    EVIDENCE_ADMITTING = "evidence_admitting"
    EVIDENCE_ADMITTED = "evidence_admitted"
    DISPATCH_FAILED = "dispatch_failed"
    EXECUTION_FAILED = "execution_failed"
    EXPIRED = "expired"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    RESULT_CONFLICT = "result_conflict"


class EvaluationControlState(StrEnum):
    """Operational states for durable non-FCO evaluation control."""

    PENDING = "pending"
    CLAIMED = "claimed"
    PROPOSAL_READY = "proposal_ready"
    RETRYABLE_FAILED = "retryable_failed"
    NON_RETRYABLE_FAILED = "non_retryable_failed"
    INVALIDATED = "invalidated"
    CANCELLED = "cancelled"
    CONFLICT = "conflict"
    COMMITTED = "committed"


class ExecutionApprovalStatus(StrEnum):
    """Durable lifecycle for one user-approved execution contract."""

    PENDING = "pending"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    STALE = "stale"
    CONSUMED = "consumed"
    FAILED = "failed"


class AnalysisIntent(StrEnum):
    """Epistemic intent for an analytical claim or contract."""

    EXPLORATORY = "exploratory"
    CONFIRMATORY = "confirmatory"
    REPLICATION = "replication"


class ConflictRelationship(StrEnum):
    """Typed review relationships for conflict detection."""

    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    NARROWS = "narrows"
    EXTENDS = "extends"
    REPLICATES = "replicates"
    FAILS_TO_REPLICATE = "fails_to_replicate"
    SUPERSEDES = "supersedes"
    INCOMPARABLE_SCOPE = "incomparable_scope"


class AnswerabilityState(StrEnum):
    """Gate status indicating whether a question can be validly answered."""

    ANSWERABLE_FROM_DISCOVERY = "answerable_from_discovery"
    ANSWERABLE_WITH_LIMITATIONS = "answerable_with_limitations"
    ONLY_EVIDENCE = "only_evidence"
    SCOPE_MISMATCH = "scope_mismatch"
    FLAGGED_DISCOVERY = "flagged_discovery"
    INSUFFICIENT_KNOWLEDGE = "insufficient_knowledge"
    NEW_TASK_REQUIRED = "new_task_required"


class TaskDependencyType(StrEnum):
    """Dependency semantics between tasks."""

    PREREQUISITE = "prerequisite"
    OPTIONAL = "optional"
    BLOCKED = "blocked"
    ALTERNATIVE = "alternative"


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


class DiscoveryLifecycleState(StrEnum):
    """Lifecycle states for Discovery review metadata."""

    ACTIVE = "active"
    FLAGGED = "flagged"
    INVALIDATED = "invalidated"
    DEPRECATED = "deprecated"


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
    OBJECTIVE_MANAGEMENT = "objective_management"


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
    CREATE_OBJECTIVE = "create_objective"
    UPDATE_OBJECTIVE = "update_objective"
    CREATE_ASSUMPTION = "create_assumption"
    UPDATE_ASSUMPTION_STATE = "update_assumption_state"
    CREATE_HYPOTHESIS = "create_hypothesis"
    CHANGE_HYPOTHESIS_STATE = "change_hypothesis_state"
    CREATE_ANALYSIS_FRAME = "create_analysis_frame"
    CREATE_EXECUTION_RUN = "create_execution_run"
    UPDATE_EXECUTION_RUN = "update_execution_run"
    CREATE_EXECUTION_OUTBOX = "create_execution_outbox"
    CREATE_EXECUTION_INBOX = "create_execution_inbox"
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
    VALIDATE_EVIDENCE = "validate_evidence"
    EVALUATE_HYPOTHESIS = "evaluate_hypothesis"
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


class PlannerCapability(StrEnum):
    """Capabilities available for planner resolution."""

    MANAGE_TASKS = "manage_tasks"
    MANAGE_ASSUMPTIONS = "manage_assumptions"
    EXECUTE_ANALYTICS = "execute_analytics"
    ANSWER_QUESTION = "answer_question"
    SUGGEST = "suggest"
    REGISTER_DATASET = "register_dataset"
    CLOSE_PROJECT = "close_project"
    PROFILE_DATASET = "profile_dataset"
    REVIEW_PROFILE = "review_profile"
    CLEAN_DATASET = "clean_dataset"
    ACCEPT_PROFILE = "accept_profile"
    REVIEW_RESULT = "review_result"
    REVIEW_CONFLICT = "review_conflict"


class AuthorizationClass(StrEnum):
    """Authorization category for proposed mutations."""

    USER_GOVERNED = "user_governed"
    TRUSTED_INTERNAL = "trusted_internal"
    UNAUTHORIZED = "unauthorized"


class GovernanceDecisionOutcome(StrEnum):
    """Outcome for a durable proposal governance decision."""

    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class DiscoveryAdmissionReplayDisposition(StrEnum):
    """Content-equivalence result for a DiscoveryAdmissionPlan attempt."""

    NEW = "new"
    IDEMPOTENT = "idempotent"
    CONFLICT = "conflict"


class DiscoveryAdmissionClaimState(StrEnum):
    """Active operational states for Discovery admission claims."""

    PENDING = "pending"
    CLAIMED = "claimed"
    COMMITTED = "committed"
    CONFLICT = "conflict"
    CANCELLED = "cancelled"
    INVALIDATED = "invalidated"



class ValiditySourceType(StrEnum):
    """Source object types for validity events."""

    EVIDENCE = "evidence"
    DATA_PROFILE = "data_profile"
    ANALYSIS_FRAME = "analysis_frame"
    EXECUTION_RUN = "execution_run"


class ValiditySourceState(StrEnum):
    """Validity state for mutable provenance metadata on non-FCO sources."""

    ACTIVE = "active"
    INVALIDATED = "invalidated"
    CONFLICT = "conflict"
    UNVERIFIED = "unverified"


class ValidityEventType(StrEnum):
    """Supported source validity events."""

    EVIDENCE_INVALIDATION = "evidence_invalidation"
    EVIDENCE_SUPERSESSION = "evidence_supersession"
    EVIDENCE_CONFLICT = "evidence_conflict"
    DATA_PROFILE_INVALIDATION = "data_profile_invalidation"
    DATA_PROFILE_SUPERSESSION = "data_profile_supersession"
    ANALYSIS_FRAME_INVALIDITY = "analysis_frame_invalidity"
    EXECUTION_RUN_CONFLICT = "execution_run_conflict"
    PROVENANCE_CORRUPTION = "provenance_corruption"
