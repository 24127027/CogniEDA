"""SQLModel table definitions for persisted CogniEDA research state.

This module acts as the canonical persistence model facade.
Importing this package registers all table models in SQLModel.metadata.
"""

from __future__ import annotations

from db.models.common import TimestampedRecord, utc_now
from db.models.discovery import DiscoveryAdmissionClaimRecord, DiscoveryRecord
from db.models.evaluation import EvaluationControlRecord
from db.models.evidence import AnalysisFrameRecord, EvidenceRecord
from db.models.execution import (
    ExecutionApprovalRecord,
    ExecutionInboxRecord,
    ExecutionOutboxRecord,
    ExecutionRunRecord,
)
from db.models.governance import (
    GovernanceAuthorityRecord,
    ProposalDecisionRecord,
    UserDecisionRecord,
)
from db.models.research import (
    AssumptionRecord,
    DataProfileRecord,
    HypothesisRecord,
    ObjectiveRecord,
    ObjectiveRevisionRecord,
    SessionFrameRecord,
    TaskRecord,
)
from db.models.validity import ValidityEventRecord
from db.models.workflow import PlannerOperationRecord

__all__ = [
    "AnalysisFrameRecord",
    "AssumptionRecord",
    "DataProfileRecord",
    "DiscoveryAdmissionClaimRecord",
    "DiscoveryRecord",
    "EvaluationControlRecord",
    "EvidenceRecord",
    "ExecutionApprovalRecord",
    "ExecutionInboxRecord",
    "ExecutionOutboxRecord",
    "ExecutionRunRecord",
    "GovernanceAuthorityRecord",
    "HypothesisRecord",
    "ObjectiveRecord",
    "ObjectiveRevisionRecord",
    "PlannerOperationRecord",
    "ProposalDecisionRecord",
    "SessionFrameRecord",
    "TaskRecord",
    "TimestampedRecord",
    "UserDecisionRecord",
    "ValidityEventRecord",
    "utc_now",
]
