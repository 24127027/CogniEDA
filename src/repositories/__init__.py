"""Research-state and provenance persistence repositories."""

from repositories.discovery import DiscoveryRepository
from repositories.evaluation import EvaluationControlRepository
from repositories.evidence import AnalysisFrameRepository, EvidenceRepository
from repositories.execution import (
    ExecutionApprovalRepository,
    ExecutionInboxRepository,
    ExecutionOutboxRepository,
    ExecutionRunRepository,
)
from repositories.governance import (
    ProposalDecisionRepository,
    UserDecisionRepository,
    UserDecisionUpdate,
)
from repositories.planner_operation_repository import PlannerOperationRepository
from repositories.research import (
    AssumptionRepository,
    AssumptionUpdate,
    DataProfileRepository,
    HypothesisRepository,
    HypothesisUpdate,
    MultipleActiveObjectivesError,
    ObjectiveMutationContext,
    ObjectiveRepository,
    ObjectiveRevisionRepository,
    ObjectiveUpdate,
    SessionFrameRepository,
    TaskRepository,
    TaskUpdate,
)
from repositories.validity import ValidityEventRepository

__all__ = [
    "AnalysisFrameRepository",
    "AssumptionRepository",
    "AssumptionUpdate",
    "DataProfileRepository",
    "DiscoveryRepository",
    "EvaluationControlRepository",
    "EvidenceRepository",
    "ExecutionApprovalRepository",
    "ExecutionInboxRepository",
    "ExecutionOutboxRepository",
    "ExecutionRunRepository",
    "HypothesisRepository",
    "HypothesisUpdate",
    "MultipleActiveObjectivesError",
    "ObjectiveMutationContext",
    "ObjectiveRepository",
    "ObjectiveRevisionRepository",
    "ObjectiveUpdate",
    "PlannerOperationRepository",
    "ProposalDecisionRepository",
    "SessionFrameRepository",
    "TaskRepository",
    "TaskUpdate",
    "UserDecisionRepository",
    "UserDecisionUpdate",
    "ValidityEventRepository",
]
