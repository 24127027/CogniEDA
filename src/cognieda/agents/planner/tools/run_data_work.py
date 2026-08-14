from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic_ai import ModelRetry, RunContext, Tool
from pydantic_ai.tools import ToolDefinition

from cognieda.agents.data_explorer.contracts import DataExplorerInput
from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutorInput,
    PlannerWorkOutcome,
    normalize_for_planner,
)
from cognieda.schemas.artifacts import Task
from cognieda.schemas.enums import TaskKind

from ..dependencies import PlannerDeps

DataWork = Literal["analyze_dataset", "profile_dataset"]


def _authorized_task(deps: PlannerDeps, task_id: UUID) -> Task:
    if not deps.executor_tools_enabled:
        raise ModelRetry("Executor tools are unavailable before Human approval.")
    if deps.approved_plan is None:
        raise ModelRetry("No approved Plan is available for executor work.")
    if task_id not in deps.approved_plan.task_ids:
        raise ModelRetry("The requested Task is outside the approved Plan.")
    if task_id not in deps.eligible_task_ids:
        raise ModelRetry("The requested Task is not currently eligible in the approved DAG.")

    tasks = {task.task_id: task for task in deps.approved_tasks}
    task = tasks.get(task_id)
    if task is None:
        raise ModelRetry("The requested Task is absent from the approved Task bundle.")
    if task.kind is not TaskKind.DATA:
        raise ModelRetry("run_data_work accepts only an approved DATA Task.")
    return task


async def run_data_work(
    ctx: RunContext[PlannerDeps],
    task_id: UUID,
    work: DataWork,
) -> PlannerWorkOutcome:
    """Run semantic dataset work for one eligible Task in the approved Plan."""

    task = _authorized_task(ctx.deps, task_id)
    execution_context = ctx.deps.execution_context

    if work == "analyze_dataset":
        data_profile = ctx.deps.data_profile
        if data_profile is None:
            raise ModelRetry("Dataset analysis requires an active DataProfile.")
        executor_input: ExecutorInput = DataExplorerInput(
            task=task,
            data_profile=data_profile,
        )
        capability = Capability.DATA_ANALYSIS
    else:
        executor_input = ExecutorInput(task=task)
        capability = Capability.DATA_PROFILING

    try:
        result = await ctx.deps.dispatcher.dispatch(
            ExecutionRequest(
                capability=capability,
                input=executor_input,
                context=execution_context,
            )
        )
    except Exception as exc:
        raise ModelRetry(f"Data Explorer dispatch failed: {exc}") from exc
    return normalize_for_planner(result)


def _prepare_executor_tool(
    ctx: RunContext[PlannerDeps],
    tool_definition: ToolDefinition,
) -> ToolDefinition | None:
    if not ctx.deps.executor_tools_enabled or ctx.deps.approved_plan is None:
        return None
    return tool_definition


RUN_DATA_WORK_TOOL = Tool[PlannerDeps](
    run_data_work,
    takes_ctx=True,
    name="run_data_work",
    prepare=_prepare_executor_tool,
)


__all__ = ("RUN_DATA_WORK_TOOL", "run_data_work")
