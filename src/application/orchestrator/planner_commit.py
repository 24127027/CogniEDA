"""Atomic commit boundary for approved planner operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session, asc, select

from db.models import (
    AssumptionRecord,
    ObjectiveRecord,
    PlannerOperationRecord,
    SessionFrameRecord,
    TaskRecord,
)
from repositories.assumption_repository import ASSUMPTION_JSON_FIELDS, AssumptionUpdate
from repositories.common import apply_update, schema_to_record_payload
from repositories.objective_repository import ObjectiveUpdate
from repositories.session_frame_repository import SESSION_FRAME_JSON_FIELDS
from repositories.task_repository import TASK_JSON_FIELDS, TaskUpdate
from schemas.artifacts import Assumption, SessionFrame, Task
from schemas.enums import (
    AssumptionStatus,
    PlannerOperationApprovalState,
    PlannerOperationType,
)
from schemas.planner_operations import (
    AssumptionStateUpdateOperationPayload,
    ConflictFlagOperationPayload,
    ObjectiveUpdateOperationPayload,
    PlannerCommitResult,
    TaskStateChangeOperationPayload,
    TaskUpdateOperationPayload,
)

_COMMITTABLE_STATES = {
    PlannerOperationApprovalState.APPROVED,
    PlannerOperationApprovalState.NOT_REQUIRED,
}


def commit_planner_operations(
    session: Session,
    *,
    session_id: str | None = None,
    operation_ids: list[UUID] | None = None,
) -> PlannerCommitResult:
    """Apply approved PlannerOperations in one all-or-nothing transaction."""

    records = _load_candidate_operations(
        session,
        session_id=session_id,
        operation_ids=operation_ids,
    )
    skipped_operation_ids = [
        record.operation_id
        for record in records
        if record.approval_state not in _COMMITTABLE_STATES
    ]
    committable_records = [
        record for record in records if record.approval_state in _COMMITTABLE_STATES
    ]
    if not committable_records:
        return PlannerCommitResult(skipped_operation_ids=skipped_operation_ids)

    current_record: PlannerOperationRecord | None = None
    try:
        for record in committable_records:
            current_record = record
            _apply_operation(session, record)

        committed_at = datetime.now(UTC)
        for record in committable_records:
            record.approval_state = PlannerOperationApprovalState.COMMITTED
            record.committed_at = committed_at
            record.error_message = None
            session.add(record)
        session.commit()
        return PlannerCommitResult(
            committed_operation_ids=[
                record.operation_id for record in committable_records
            ],
            skipped_operation_ids=skipped_operation_ids,
        )
    except Exception as exc:
        session.rollback()
        error_message = str(exc)
        failed_operation_ids = []
        error_details: dict[UUID, str] = {}
        if current_record is not None:
            _mark_failed_after_rollback(session, current_record.operation_id, error_message)
            failed_operation_ids.append(current_record.operation_id)
            error_details[current_record.operation_id] = error_message
        return PlannerCommitResult(
            failed_operation_ids=failed_operation_ids,
            skipped_operation_ids=skipped_operation_ids,
            error_details=error_details,
        )


def _load_candidate_operations(
    session: Session,
    *,
    session_id: str | None,
    operation_ids: list[UUID] | None,
) -> list[PlannerOperationRecord]:
    if operation_ids is not None:
        records: list[PlannerOperationRecord] = []
        for operation_id in operation_ids:
            record = session.get(PlannerOperationRecord, operation_id)
            if record is not None:
                records.append(record)
        return records

    statement = (
        select(PlannerOperationRecord)
        .where(
            PlannerOperationRecord.approval_state.in_(
                (
                    PlannerOperationApprovalState.APPROVED,
                    PlannerOperationApprovalState.NOT_REQUIRED,
                )
            )
        )
        .order_by(asc(PlannerOperationRecord.created_at))
    )
    if session_id is not None:
        statement = statement.where(PlannerOperationRecord.session_id == session_id)
    return list(session.exec(statement).all())


def _apply_operation(session: Session, record: PlannerOperationRecord) -> None:
    match record.operation_type:
        case PlannerOperationType.CREATE_TASK:
            _apply_create_task(session, record)
        case PlannerOperationType.UPDATE_TASK:
            _apply_update_task(session, record)
        case PlannerOperationType.CHANGE_TASK_STATE:
            _apply_change_task_state(session, record)
        case PlannerOperationType.CREATE_ASSUMPTION:
            _apply_create_assumption(session, record)
        case PlannerOperationType.UPDATE_ASSUMPTION_STATE:
            _apply_update_assumption_state(session, record)
        case PlannerOperationType.UPDATE_OBJECTIVE:
            _apply_update_objective(session, record)
        case PlannerOperationType.UPDATE_SESSION_FRAME:
            _apply_update_session_frame(session, record)
        case PlannerOperationType.FLAG_OBJECT:
            _apply_flag_object(session, record)
        case _:
            raise ValueError(
                "Unsupported PlannerOperation type for Phase 1 commit: "
                f"{record.operation_type.value}"
            )


def _apply_create_task(session: Session, operation: PlannerOperationRecord) -> None:
    payload = _payload_with_target_id(operation, id_field="task_id")
    task = Task(**payload)
    if session.get(TaskRecord, task.task_id) is not None:
        raise ValueError(f"Task already exists: {task.task_id}")
    record = TaskRecord(**schema_to_record_payload(task, json_fields=TASK_JSON_FIELDS))
    session.add(record)
    operation.target_object_id = task.task_id
    operation.target_object_type = "task"
    session.add(operation)
    session.flush()


def _apply_update_task(session: Session, operation: PlannerOperationRecord) -> None:
    payload = TaskUpdateOperationPayload.model_validate(
        _payload_with_target_id(operation, id_field="task_id")
    )
    _require_payload_target_matches(operation, payload.task_id, "update_task")
    task_record = _require_record(session, TaskRecord, payload.task_id, "Task")
    update = TaskUpdate(
        **payload.model_dump(exclude={"task_id"}, exclude_none=True)
    )
    _require_update_payload(update.model_fields_set, operation.operation_type.value)
    apply_update(task_record, update, json_fields=TASK_JSON_FIELDS)
    session.add(task_record)
    session.flush()


def _apply_change_task_state(session: Session, operation: PlannerOperationRecord) -> None:
    payload = TaskStateChangeOperationPayload.model_validate(
        _payload_with_target_id(operation, id_field="task_id")
    )
    _require_payload_target_matches(operation, payload.task_id, "change_task_state")
    task_record = _require_record(session, TaskRecord, payload.task_id, "Task")
    update = TaskUpdate(lifecycle_state=payload.lifecycle_state)
    apply_update(task_record, update, json_fields=TASK_JSON_FIELDS)
    session.add(task_record)
    session.flush()


def _apply_create_assumption(session: Session, operation: PlannerOperationRecord) -> None:
    payload = _payload_with_target_id(operation, id_field="assumption_id")
    assumption = Assumption(**payload)
    if session.get(AssumptionRecord, assumption.assumption_id) is not None:
        raise ValueError(f"Assumption already exists: {assumption.assumption_id}")
    record = AssumptionRecord(
        **schema_to_record_payload(assumption, json_fields=ASSUMPTION_JSON_FIELDS)
    )
    session.add(record)
    operation.target_object_id = assumption.assumption_id
    operation.target_object_type = "assumption"
    session.add(operation)
    session.flush()


def _apply_update_assumption_state(
    session: Session,
    operation: PlannerOperationRecord,
) -> None:
    payload = AssumptionStateUpdateOperationPayload.model_validate(
        _payload_with_target_id(operation, id_field="assumption_id")
    )
    _require_payload_target_matches(
        operation,
        payload.assumption_id,
        "update_assumption_state",
    )
    assumption_record = _require_record(
        session,
        AssumptionRecord,
        payload.assumption_id,
        "Assumption",
    )
    update = AssumptionUpdate(
        **payload.model_dump(exclude={"assumption_id"}, exclude_none=True)
    )
    _require_update_payload(update.model_fields_set, operation.operation_type.value)
    apply_update(assumption_record, update, json_fields=ASSUMPTION_JSON_FIELDS)
    session.add(assumption_record)
    session.flush()


def _apply_update_objective(session: Session, operation: PlannerOperationRecord) -> None:
    payload = ObjectiveUpdateOperationPayload.model_validate(
        _payload_with_target_id(operation, id_field="objective_id")
    )
    _require_payload_target_matches(operation, payload.objective_id, "update_objective")
    objective_record = _require_record(
        session,
        ObjectiveRecord,
        payload.objective_id,
        "Objective",
    )
    update = ObjectiveUpdate(
        **payload.model_dump(exclude={"objective_id"}, exclude_none=True)
    )
    _require_update_payload(update.model_fields_set, operation.operation_type.value)
    apply_update(objective_record, update)
    session.add(objective_record)
    session.flush()


def _apply_update_session_frame(session: Session, operation: PlannerOperationRecord) -> None:
    payload = _payload_with_target_id(operation, id_field="session_frame_id")
    frame = SessionFrame(**payload)
    if session.get(SessionFrameRecord, frame.session_frame_id) is not None:
        raise ValueError(f"SessionFrame already exists: {frame.session_frame_id}")
    record = SessionFrameRecord(
        **schema_to_record_payload(frame, json_fields=SESSION_FRAME_JSON_FIELDS)
    )
    session.add(record)
    operation.target_object_id = frame.session_frame_id
    operation.target_object_type = "session_frame"
    session.add(operation)
    session.flush()


def _apply_flag_object(session: Session, operation: PlannerOperationRecord) -> None:
    payload = ConflictFlagOperationPayload.model_validate(
        _payload_with_target_id(operation, id_field="assumption_id")
    )
    _require_payload_target_matches(operation, payload.assumption_id, "flag_object")
    if payload.target_object_type != "assumption":
        raise ValueError("Phase 1 flag_object supports target_object_type='assumption' only.")

    assumption_record = _require_record(
        session,
        AssumptionRecord,
        payload.assumption_id,
        "Assumption",
    )
    contradiction_ref = payload.discovery_id or payload.contradicted_by_discovery_id
    if contradiction_ref is not None:
        contradicted_by_discovery_ids = list(assumption_record.contradicted_by_discovery_ids)
        discovery_ref = str(UUID(str(contradiction_ref)))
        if discovery_ref not in contradicted_by_discovery_ids:
            contradicted_by_discovery_ids.append(discovery_ref)
        assumption_record.contradicted_by_discovery_ids = contradicted_by_discovery_ids
    assumption_record.status = AssumptionStatus.FLAGGED
    assumption_record.updated_at = datetime.now(UTC)
    session.add(assumption_record)
    session.flush()


def _payload_with_target_id(
    operation: PlannerOperationRecord,
    *,
    id_field: str,
) -> dict[str, Any]:
    payload = dict(operation.payload)
    if operation.target_object_id is not None and id_field not in payload:
        payload[id_field] = operation.target_object_id
    return payload


def _require_target_object_id(
    operation: PlannerOperationRecord,
    operation_name: str,
) -> UUID:
    if operation.target_object_id is None:
        raise ValueError(f"{operation_name} requires target_object_id.")
    return operation.target_object_id


def _require_payload_target_matches(
    operation: PlannerOperationRecord,
    payload_target_id: UUID,
    operation_name: str,
) -> None:
    if (
        operation.target_object_id is not None
        and operation.target_object_id != payload_target_id
    ):
        raise ValueError(
            f"{operation_name} payload target does not match target_object_id."
        )


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


def _mark_failed_after_rollback(
    session: Session,
    operation_id: UUID,
    error_message: str,
) -> None:
    record = session.get(PlannerOperationRecord, operation_id)
    if record is None:
        return
    record.approval_state = PlannerOperationApprovalState.FAILED
    record.error_message = error_message
    session.add(record)
    session.commit()
