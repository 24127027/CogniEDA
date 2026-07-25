"""Typed research-state schemas exposed without eager cross-boundary imports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    **dict.fromkeys(
        (
            "Assumption",
            "DataProfile",
            "Hypothesis",
            "Objective",
            "ObjectiveRevision",
            "SessionFrame",
            "Task",
        ),
        "schemas.research",
    ),
    **dict.fromkeys(
        (
            "AnalysisFrame",
            "Evidence",
        ),
        "schemas.evidence",
    ),
    **dict.fromkeys(
        (
            "ExecutionApproval",
            "ExecutionInbox",
            "ExecutionOutbox",
            "ExecutionRun",
        ),
        "schemas.execution",
    ),
    **dict.fromkeys(
        ("Discovery",),
        "schemas.discovery",
    ),
    **dict.fromkeys(
        ("UserDecision",),
        "schemas.governance",
    ),
    **dict.fromkeys(
        (
            "AssumptionContextSummary",
            "BaselineSummary",
            "CategoricalColumnSummary",
            "ColumnSchemaSummary",
            "ContextProvenance",
            "DataProfileContextSummary",
            "DeadEndSummary",
            "DiscoveryClaim",
            "DiscoveryContextSummary",
            "EvidenceContextSummary",
            "EvidenceProvenance",
            "EvidenceResultSummary",
            "HypothesisContextSummary",
            "InvalidationRule",
            "LineageStep",
            "MethodParameter",
            "NumericColumnSummary",
            "QualityFlag",
            "SchemaSummary",
            "StaleContextMarker",
            "TaskContextSummary",
            "ToolResultCacheSummary",
            "TopValueSummary",
            "UserDecisionContextSummary",
            "ValidityBasis",
        ),
        "schemas.common",
    ),
    **dict.fromkeys(
        (
            "DataExplorerFailureReason",
            "DataExplorerFailureResult",
            "DataExplorerResult",
            "DataExplorerSuccessResult",
            "ExecutionDetails",
            "TechnicalDiagnostic",
            "TechnicalRetryDisposition",
        ),
        "schemas.execution.data_explorer",
    ),
    **dict.fromkeys(
        (
            "ExecutionReceiptEnvelope",
            "ExecutionSpecification",
            "HypothesisDraft",
            "PreparedExecution",
        ),
        "schemas.execution.contracts",
    ),
    **dict.fromkeys(
        (
            "AssumptionSource",
            "AssumptionStatus",
            "AssumptionTestability",
            "AuthorizationClass",
            "ConfidenceLevel",
            "ContextMode",
            "DataProfileLifecycleState",
            "DataProfileMethod",
            "DatasetSourceType",
            "DiscoveryAdmissionReplayDisposition",
            "DiscoveryEpistemicStatus",
            "EvaluationControlState",
            "EvidenceLifecycleState",
            "EvidenceType",
            "FirstClassObjectType",
            "GovernanceDecisionOutcome",
            "HypothesisEvidenceOutcome",
            "HypothesisStatus",
            "InvalidationTrigger",
            "LineageOperationType",
            "LogicalDtype",
            "MemorySourceType",
            "MemoryStatus",
            "ObjectiveStatus",
            "PlannerNodeName",
            "PlannerOperationApprovalState",
            "PlannerOperationType",
            "QualityFlagSeverity",
            "SessionFrameStatus",
            "TaskKind",
            "TaskLifecycleState",
            "UserDecisionStatus",
            "UserDecisionType",
            "ValidityEventType",
            "ValiditySourceType",
            "ValiditySourceState",
        ),
        "schemas.enums",
    ),
    **dict.fromkeys(
        (
            "AtomicDiscoveryAdmissionResult",
            "DiscoveryAdmissionLease",
            "DiscoveryAdmissionPlan",
            "DiscoveryClaimSnapshot",
            "FutureAtomicWriteSet",
            "ValidityBasisSnapshot",
        ),
        "schemas.discovery",
    ),
    **dict.fromkeys(
        (
            "ValidityPropagationCommand",
            "ValidityPropagationPlan",
            "ValidityPropagationResult",
            "ValidityTargetTransition",
        ),
        "schemas.validity",
    ),
    **dict.fromkeys(
        ("AnalysisFrameObservation", "EvidenceObservation"),
        "schemas.execution.observations",
    ),
    **dict.fromkeys(
        ("PlannerCommitResult", "PlannerOperation"),
        "schemas.planner_operations",
    ),
    **dict.fromkeys(
        (
            "AnalysisFrameEvaluationSnapshot",
            "DataProfileEvaluationSnapshot",
            "DiscoveryProposal",
            "DiscoverySynthesisBundle",
            "EvaluationFailure",
            "EvaluationFailureReason",
            "HypothesisAnalystResult",
            "HypothesisEvaluationSnapshot",
            "compute_proposal_digest",
            "validate_proposal_against_bundle",
        ),
        "schemas.evaluation",
    ),
}

__all__ = sorted(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    """Lazily preserve package-level exports without crossing authority boundaries."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted((*globals(), *__all__))
