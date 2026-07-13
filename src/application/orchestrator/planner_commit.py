"""Skeleton commit boundary for planner-produced operations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, asc, select

from db.models import (
    AnalysisFrameRecord,
    AssumptionRecord,
    ExecutionRunRecord,
    HypothesisRecord,
    ObjectiveRecord,
    ObjectiveRevisionRecord,
    PlannerOperationRecord,
    SessionFrameRecord,
    TaskRecord,
)
from repositories.analysis_frame_repository import AnalysisFrameRepository
from repositories.assumption_repository import ASSUMPTION_JSON_FIELDS, AssumptionUpdate
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from repositories.discovery_repository import DiscoveryRepository
from repositories.evidence_repository import EvidenceRepository
from repositories.execution_run_repository import ExecutionRunRepository
from repositories.hypothesis_repository import HypothesisRepository, HypothesisUpdate
from repositories.objective_repository import ObjectiveUpdate, build_objective_revision
from repositories.objective_revision_repository import OBJECTIVE_REVISION_JSON_FIELDS
from repositories.session_frame_repository import SESSION_FRAME_JSON_FIELDS
from repositories.task_repository import TASK_JSON_FIELDS, TaskUpdate
from schemas.artifacts import (
    Assumption,
    Discovery,
    Evidence,
    Hypothesis,
    Objective,
    SessionFrame,
    Task,
)
from schemas.enums import (
    AssumptionStatus,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerCommitResult, PlannerOperation
from schemas.provenance import AnalysisFrame, ExecutionRun

_COMMITTABLE_STATES = {
    PlannerOperationApprovalState.APPROVED,
    PlannerOperationApprovalState.NOT_REQUIRED,
}
_EXECUTION_OPERATION_TYPES = {
    PlannerOperationType.CREATE_HYPOTHESIS,
    PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
    PlannerOperationType.CREATE_ANALYSIS_FRAME,
    PlannerOperationType.CREATE_EXECUTION_RUN,
    PlannerOperationType.CREATE_EVIDENCE,
    PlannerOperationType.CREATE_DISCOVERY,
}


def commit_planner_operations(
    session: Session,
    operations: list[PlannerOperation] | None = None,
    *,
    session_id: str | None = None,
    operation_ids: list[UUID] | None = None,
) -> PlannerCommitResult:
    """Dispatch approved PlannerOperations through the commit boundary.

    The current implementation is intentionally skeleton-first. It shows that
    planner nodes produce operations and that commit is the only place where
    approved operations are applied. Future work should add explicit
    transaction scope, rollback provenance, and the user-approval workflow here.
    """

    candidate_operations = operations
    if candidate_operations is None:
        candidate_operations = _load_candidate_operations(
            session,
            session_id=session_id,
            operation_ids=operation_ids,
        )

    if _is_execution_bundle(candidate_operations):
        return _commit_execution_bundle(session, candidate_operations)

    result = PlannerCommitResult()
    committed_at = datetime.now(UTC)
    for operation in candidate_operations:
        if operation.approval_state not in _COMMITTABLE_STATES:
            result.skipped_operation_ids.append(operation.operation_id)
            continue

        try:
            _apply_operation(session, operation)
        except Exception as exc:
            result.failed_operation_ids.append(operation.operation_id)
            result.errors[operation.operation_id] = str(exc)
            continue

        operation.approval_state = PlannerOperationApprovalState.COMMITTED
        operation.committed_at = committed_at
        _mark_persisted_operation_committed(
            session,
            operation.operation_id,
            committed_at=committed_at,
        )
        result.committed_operation_ids.append(operation.operation_id)

    # This single flush is only the skeleton boundary. Production commit should
    # make transaction, rollback, and approval semantics explicit in this layer.
    session.commit()
    result.message = _result_message(result)
    return result


def _load_candidate_operations(
    session: Session,
    *,
    session_id: str | None,
    operation_ids: list[UUID] | None,
) -> list[PlannerOperation]:
    if operation_ids is not None:
        operations: list[PlannerOperation] = []
        for operation_id in operation_ids:
            record = session.get(PlannerOperationRecord, operation_id)
            if record is not None:
                operations.append(record_to_schema(PlannerOperation, record))
        return operations

    statement = select(PlannerOperationRecord).order_by(asc(PlannerOperationRecord.created_at))
    if session_id is not None:
        statement = statement.where(PlannerOperationRecord.session_id == session_id)
    records = session.exec(statement).all()
    return [record_to_schema(PlannerOperation, record) for record in records]


def _is_execution_bundle(operations: list[PlannerOperation]) -> bool:
    """Identify the Stage 2 ordered analytical mutation bundle."""

    return any(operation.operation_type in _EXECUTION_OPERATION_TYPES for operation in operations)


def _commit_execution_bundle(
    session: Session,
    operations: list[PlannerOperation],
) -> PlannerCommitResult:
    """Apply an analytical bundle in one session commit or roll back all target changes."""

    result = PlannerCommitResult()
    committable = [
        operation for operation in operations if operation.approval_state in _COMMITTABLE_STATES
    ]
    result.skipped_operation_ids.extend(
        operation.operation_id
        for operation in operations
        if operation.approval_state not in _COMMITTABLE_STATES
    )
    committed_at = datetime.now(UTC)
    current_operation: PlannerOperation | None = None
    try:
        for current_operation in committable:
            _apply_operation(session, current_operation)
            # Surface FK/uniqueness errors before marking any operation successful.
            session.flush()
        for operation in committable:
            operation.approval_state = PlannerOperationApprovalState.COMMITTED
            operation.committed_at = committed_at
            _mark_persisted_operation_committed(
                session,
                operation.operation_id,
                committed_at=committed_at,
            )
        session.commit()
    except Exception as exc:
        session.rollback()
        if current_operation is not None:
            result.failed_operation_ids.append(current_operation.operation_id)
            result.errors[current_operation.operation_id] = str(exc)
        result.message = _result_message(result)
        return result

    result.committed_operation_ids.extend(operation.operation_id for operation in committable)
    result.message = _result_message(result)
    return result


def _apply_operation(session: Session, operation: PlannerOperation) -> None:
    match operation.operation_type:
        case PlannerOperationType.CREATE_TASK:
            _apply_create_task(session, operation)
        case PlannerOperationType.UPDATE_TASK:
            _apply_update_task(session, operation)
        case PlannerOperationType.CHANGE_TASK_STATE:
            _apply_change_task_state(session, operation)
        case PlannerOperationType.CREATE_ASSUMPTION:
            _apply_create_assumption(session, operation)
        case PlannerOperationType.UPDATE_ASSUMPTION_STATE:
            _apply_update_assumption_state(session, operation)
        case PlannerOperationType.CREATE_HYPOTHESIS:
            _apply_create_hypothesis(session, operation)
        case PlannerOperationType.CHANGE_HYPOTHESIS_STATE:
            _apply_change_hypothesis_state(session, operation)
        case PlannerOperationType.CREATE_ANALYSIS_FRAME:
            _apply_create_analysis_frame(session, operation)
        case PlannerOperationType.CREATE_EXECUTION_RUN:
            _apply_create_execution_run(session, operation)
        case PlannerOperationType.UPDATE_EXECUTION_RUN:
            _apply_update_execution_run(session, operation)
        case PlannerOperationType.CREATE_EVIDENCE:
            _apply_create_evidence(session, operation)
        case PlannerOperationType.CREATE_DISCOVERY:
            _apply_create_discovery(session, operation)
        case PlannerOperationType.UPDATE_OBJECTIVE:
            _apply_update_objective(session, operation)
        case PlannerOperationType.UPDATE_SESSION_FRAME:
            _apply_update_session_frame(session, operation)
        case PlannerOperationType.FLAG_OBJECT:
            _apply_flag_object(session, operation)
        case _:
            raise ValueError(
                "Unsupported PlannerOperation type for skeleton commit: "
                f"{operation.operation_type.value}"
            )


def _apply_create_task(session: Session, operation: PlannerOperation) -> None:
    task = Task(**operation.payload)
    if session.get(TaskRecord, task.task_id) is not None:
        raise ValueError(f"Task already exists: {task.task_id}")
    session.add(TaskRecord(**schema_to_record_payload(task, json_fields=TASK_JSON_FIELDS)))


def _apply_update_task(session: Session, operation: PlannerOperation) -> None:
    task_id = _require_payload_uuid(operation, "task_id")
    task_record = _require_record(session, TaskRecord, task_id, "Task")
    payload = dict(operation.payload)
    payload.pop("task_id", None)
    update = TaskUpdate(**payload)
    _require_update_payload(update.model_fields_set, operation.operation_type.value)
    apply_update(task_record, update, json_fields=TASK_JSON_FIELDS)
    session.add(task_record)


def _apply_change_task_state(session: Session, operation: PlannerOperation) -> None:
    task_id = _require_payload_uuid(operation, "task_id")
    task_record = _require_record(session, TaskRecord, task_id, "Task")
    if "lifecycle_state" not in operation.payload:
        raise ValueError("change_task_state requires lifecycle_state in payload.")
    apply_update(
        task_record,
        TaskUpdate(lifecycle_state=TaskLifecycleState(operation.payload["lifecycle_state"])),
        json_fields=TASK_JSON_FIELDS,
    )
    session.add(task_record)


def _apply_create_assumption(session: Session, operation: PlannerOperation) -> None:
    assumption = Assumption(**operation.payload)
    if session.get(AssumptionRecord, assumption.assumption_id) is not None:
        raise ValueError(f"Assumption already exists: {assumption.assumption_id}")
    session.add(
        AssumptionRecord(**schema_to_record_payload(assumption, json_fields=ASSUMPTION_JSON_FIELDS))
    )


def _apply_create_hypothesis(session: Session, operation: PlannerOperation) -> None:
    hypothesis = Hypothesis(**operation.payload)
    if session.get(HypothesisRecord, hypothesis.hypothesis_id) is not None:
        raise ValueError(f"Hypothesis already exists: {hypothesis.hypothesis_id}")
    HypothesisRepository(session).stage_create(hypothesis)


def _apply_change_hypothesis_state(session: Session, operation: PlannerOperation) -> None:
    hypothesis_id = _require_payload_uuid(operation, "hypothesis_id")
    record = _require_record(session, HypothesisRecord, hypothesis_id, "Hypothesis")
    if "status" not in operation.payload:
        raise ValueError("change_hypothesis_state requires status in payload.")
    apply_update(record, HypothesisUpdate(status=operation.payload["status"]))
    session.add(record)


def _apply_create_analysis_frame(session: Session, operation: PlannerOperation) -> None:
    analysis_frame = AnalysisFrame(**operation.payload)
    if session.get(AnalysisFrameRecord, analysis_frame.analysis_frame_id) is not None:
        raise ValueError(f"AnalysisFrame already exists: {analysis_frame.analysis_frame_id}")
    AnalysisFrameRepository(session).stage_create(analysis_frame)


def _apply_create_execution_run(session: Session, operation: PlannerOperation) -> None:
    execution_run = ExecutionRun(**operation.payload)
    if session.get(ExecutionRunRecord, execution_run.execution_run_id) is not None:
        raise ValueError(f"ExecutionRun already exists: {execution_run.execution_run_id}")
    ExecutionRunRepository(session).stage_create(execution_run)


def _apply_update_execution_run(session: Session, operation: PlannerOperation) -> None:
    execution_run_id = _require_payload_uuid(operation, "execution_run_id")
    record = _require_record(session, ExecutionRunRecord, execution_run_id, "ExecutionRun")
    if "status" in operation.payload:
        record.status = operation.payload["status"]
    session.add(record)


def _apply_create_evidence(session: Session, operation: PlannerOperation) -> None:
    evidence = Evidence(**operation.payload)
    EvidenceRepository(session, strict_provenance_validation=True).stage_create(evidence)


def _apply_create_discovery(session: Session, operation: PlannerOperation) -> None:
    discovery = Discovery(**operation.payload)
    DiscoveryRepository(session).stage_create(discovery)


def _apply_update_assumption_state(session: Session, operation: PlannerOperation) -> None:
    assumption_id = _require_payload_uuid(operation, "assumption_id")
    assumption_record = _require_record(session, AssumptionRecord, assumption_id, "Assumption")
    payload = dict(operation.payload)
    payload.pop("assumption_id", None)
    update = AssumptionUpdate(**payload)
    _require_update_payload(update.model_fields_set, operation.operation_type.value)
    apply_update(assumption_record, update, json_fields=ASSUMPTION_JSON_FIELDS)
    session.add(assumption_record)


def _apply_update_objective(session: Session, operation: PlannerOperation) -> None:
    objective_id = _require_payload_uuid(operation, "objective_id")
    objective_record = _require_record(session, ObjectiveRecord, objective_id, "Objective")
    payload = dict(operation.payload)
    payload.pop("objective_id", None)
    revision_reason = payload.pop("revision_reason", None)
    user_decision_id = payload.pop("user_decision_id", None)
    created_by = payload.pop("created_by", None)
    update = ObjectiveUpdate(**payload)
    _require_update_payload(update.model_fields_set, operation.operation_type.value)
    previous_objective = record_to_schema(Objective, objective_record)
    apply_update(objective_record, update)
    updated_objective = record_to_schema(Objective, objective_record)
    revision = build_objective_revision(
        previous_objective,
        updated_objective,
        revision_reason=revision_reason,
        planner_operation_id=operation.operation_id,
        user_decision_id=user_decision_id,
        created_by=created_by,
    )
    # TODO: Wire richer approval/user-decision provenance when approval UX exists.
    if revision is not None:
        session.add(
            ObjectiveRevisionRecord(
                **schema_to_record_payload(
                    revision,
                    json_fields=OBJECTIVE_REVISION_JSON_FIELDS,
                )
            )
        )
    session.add(objective_record)


def _apply_update_session_frame(session: Session, operation: PlannerOperation) -> None:
    # Skeleton behavior: create a new frame snapshot from the supplied payload.
    # Later work can decide whether this operation means append, replace, or
    # user-governed frame mutation.
    frame = SessionFrame(**operation.payload)
    if session.get(SessionFrameRecord, frame.session_frame_id) is not None:
        raise ValueError(f"SessionFrame already exists: {frame.session_frame_id}")
    session.add(
        SessionFrameRecord(**schema_to_record_payload(frame, json_fields=SESSION_FRAME_JSON_FIELDS))
    )


def _apply_flag_object(session: Session, operation: PlannerOperation) -> None:
    target_type = operation.payload.get("target_object_type", "assumption")
    if target_type != "assumption":
        raise ValueError("flag_object skeleton supports target_object_type='assumption' only.")

    assumption_id = _require_payload_uuid(operation, "assumption_id")
    assumption_record = _require_record(session, AssumptionRecord, assumption_id, "Assumption")
    contradiction_ref = operation.payload.get("discovery_id") or operation.payload.get(
        "contradicted_by_discovery_id"
    )
    if contradiction_ref is not None:
        contradicted_by_discovery_ids = list(assumption_record.contradicted_by_discovery_ids)
        discovery_ref = str(UUID(str(contradiction_ref)))
        if discovery_ref not in contradicted_by_discovery_ids:
            contradicted_by_discovery_ids.append(discovery_ref)
        assumption_record.contradicted_by_discovery_ids = contradicted_by_discovery_ids
    assumption_record.status = AssumptionStatus.FLAGGED
    assumption_record.updated_at = datetime.now(UTC)
    session.add(assumption_record)


def _require_payload_uuid(operation: PlannerOperation, field_name: str) -> UUID:
    value = operation.payload.get(field_name)
    if value is None:
        raise ValueError(f"{operation.operation_type.value} requires {field_name} in payload.")
    return UUID(str(value))


def _require_record[RecordT](
    session: Session,
    record_type: type[RecordT],
    record_id: UUID,
    record_name: str,
) -> RecordT:
    record = session.get(record_type, record_id)
    if record is None:
        raise ValueError(f"{record_name} not found: {record_id}")
    return record


def _require_update_payload(field_names: set[str], operation_type: str) -> None:
    if not field_names:
        raise ValueError(f"{operation_type} requires at least one update field.")


def _mark_persisted_operation_committed(
    session: Session,
    operation_id: UUID,
    *,
    committed_at: datetime,
) -> None:
    record = session.get(PlannerOperationRecord, operation_id)
    if record is None:
        return
    record.approval_state = PlannerOperationApprovalState.COMMITTED
    record.committed_at = committed_at
    session.add(record)


def _result_message(result: PlannerCommitResult) -> str:
    return (
        f"Committed {len(result.committed_operation_ids)} operation(s), "
        f"skipped {len(result.skipped_operation_ids)}, "
        f"failed {len(result.failed_operation_ids)}."
    )
