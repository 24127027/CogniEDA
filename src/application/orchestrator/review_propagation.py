"""Propagation of Discovery review flags to exact motivated tasks."""

from uuid import UUID

from sqlmodel import Session

from db.models import DiscoveryRecord, TaskRecord
from repositories.common import apply_update
from repositories.task_repository import TASK_JSON_FIELDS, TaskRepository, TaskUpdate
from schemas.enums import DiscoveryLifecycleState


def propagate_discovery_review(session: Session, discovery_id: UUID) -> None:
    """Flag all Tasks explicitly motivated by a reviewed/invalidated Discovery.
    
    This enforces strict exact mappings (T1, T3) rather than invalidating downstream
    hypotheses or changing the Task scientific truth state to 'failed'.
    """
    
    discovery = session.get(DiscoveryRecord, discovery_id)
    if discovery is None:
        raise ValueError(f"Discovery {discovery_id} not found.")
        
    if discovery.lifecycle_state not in {
        DiscoveryLifecycleState.FLAGGED,
        DiscoveryLifecycleState.INVALIDATED,
        DiscoveryLifecycleState.DEPRECATED,
    }:
        return

    task_repo = TaskRepository(session)
    motivated_tasks = task_repo.list_motivated_by_discovery(discovery_id)
    
    reason_note = (
        f"Motivating Discovery {discovery_id} entered review state "
        f"({discovery.lifecycle_state.value})."
    )
    
    for task in motivated_tasks:
        if reason_note not in task.review_reasons:
            reasons = list(task.review_reasons)
            reasons.append(reason_note)
            update = TaskUpdate(review_reasons=reasons)
            record = session.get(TaskRecord, task.task_id)
            if record is None:
                raise ValueError(f"Task disappeared during review propagation: {task.task_id}")
            apply_update(record, update, json_fields=TASK_JSON_FIELDS)
            session.add(record)
