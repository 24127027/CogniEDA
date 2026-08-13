"""Application-owned governed DATA interaction exposed to Planner."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from pydantic_ai.tools import RunContext

from cognieda.agents.data_explorer import DataExplorerInput, DataExplorerResult
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContext,
    PlannerWorkOutcome,
    normalize_for_planner,
)


def _blocked_outcome(task_id: UUID, message: str) -> PlannerWorkOutcome:
    payload = json.dumps(
        {"task_id": str(task_id), "message": message},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return PlannerWorkOutcome(
        source_role="application",
        task_id=task_id,
        work_id=f"blocked:data_work:{task_id}",
        status=ExecutionStatus.BLOCKED,
        semantic_summary="The governed Data Explorer interaction could not run.",
        blockers=[message],
        permitted_next_actions=["hold", "replan"],
        result_digest=hashlib.sha256(payload).hexdigest(),
    )


async def run_data_work(
    ctx: RunContext[PlannerDeps],
    requested_work: str,
) -> PlannerWorkOutcome:
    """Request semantic bounded data work without exposing execution routing."""

    deps = ctx.deps
    task = deps.active_task
    data_profile = deps.data_profile
    dataset_path = deps.execution_context.dataset_path
    if (
        task is None
        or data_profile is None
        or dataset_path is None
        or deps.dataset_digest is None
    ):
        raise ValueError("Data work requires application-supplied authoritative execution state.")

    request = ExecutionRequest(
        capability=Capability.DATA_ANALYSIS,
        input=DataExplorerInput(
            task=task,
            data_profile=data_profile,
            requested_work=requested_work,
        ),
        context=ExecutorContext(
            dataset_path=dataset_path,
            data_profile_id=data_profile.data_profile_id,
        ),
    )
    try:
        dispatched = await deps.dispatcher.dispatch(request)
    except Exception as exc:
        return _blocked_outcome(task.task_id, str(exc))

    if not isinstance(dispatched, DataExplorerResult):
        raise ValueError("Data work requires a role-native DataExplorerResult.")
    if dispatched.task_id != task.task_id or dispatched.source_role != "data_explorer":
        raise ValueError("Data Explorer result identity does not match the eligible Task.")
    provenance = dispatched.provenance
    if dispatched.status is ExecutionStatus.SUCCEEDED and (
        provenance is None
        or provenance.data_profile_id != data_profile.data_profile_id
        or provenance.dataset_reference != dataset_path
        or provenance.dataset_digest != deps.dataset_digest
    ):
        raise ValueError("Data Explorer result provenance does not match authoritative state.")

    deps.data_results.append(dispatched)
    outcome = normalize_for_planner(dispatched)
    if dispatched.observations:
        outcome = outcome.model_copy(
            update={
                "semantic_summary": " ".join(
                    f"{observation.summary} Result: "
                    f"{json.dumps(observation.payload, sort_keys=True)}"
                    for observation in dispatched.observations
                )
            }
        )
    return outcome


__all__ = ("run_data_work",)
