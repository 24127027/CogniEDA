from __future__ import annotations

from uuid import UUID

from pydantic_ai import ModelRetry, RunContext, Tool
from pydantic_ai.tools import ToolDefinition

from cognieda.schemas.artifacts import Evidence

from ..dependencies import PlannerDeps, PlannerExecutionSessionPort


def _execution_session(deps: PlannerDeps) -> PlannerExecutionSessionPort:
    if not deps.executor_tools_enabled:
        raise ModelRetry("Executor tools are unavailable before Human approval.")
    if deps.execution_session is None:
        raise ModelRetry("No authorized execution session is available.")
    return deps.execution_session


async def run_data_work(
    ctx: RunContext[PlannerDeps],
    task_id: UUID,
    requested_work: str,
) -> Evidence:
    """Run semantic dataset work for one eligible Task in the approved Plan."""

    if not requested_work.strip():
        raise ModelRetry("requested_work must describe non-empty semantic data work.")
    try:
        return await _execution_session(ctx.deps).run_data_work(
            ctx.deps.dispatcher,
            task_id=task_id,
            requested_work=requested_work,
        )
    except Exception as exc:
        raise ModelRetry(f"Data Explorer dispatch failed: {exc}") from exc


def _prepare_executor_tool(
    ctx: RunContext[PlannerDeps],
    tool_definition: ToolDefinition,
) -> ToolDefinition | None:
    if not ctx.deps.executor_tools_enabled or ctx.deps.execution_session is None:
        return None
    return tool_definition


RUN_DATA_WORK_TOOL = Tool[PlannerDeps](
    run_data_work,
    takes_ctx=True,
    name="run_data_work",
    prepare=_prepare_executor_tool,
)


__all__ = ("RUN_DATA_WORK_TOOL", "run_data_work")
