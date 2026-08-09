from __future__ import annotations

from pydantic_ai.tools import RunContext

from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ExecutorContext,
    ExecutorInput,
)
from cognieda.schemas.artifacts import Task

from ..dependencies.protocols import HasExecutorDispatcher


async def invoke_data_capability(
    ctx: RunContext[HasExecutorDispatcher],
    task: Task,
    capability: Capability = Capability.DATA_ANALYSIS,
) -> ExecutionResult:
    """PydanticAI adapter for a typed Data Explorer capability invocation."""

    if capability not in {
        Capability.DATA_ANALYSIS,
        Capability.DATA_PROFILING,
        Capability.DATA_TRANSFORMATION,
    }:
        raise ValueError("The dataset delegation tool accepts only data capabilities.")

    return await ctx.deps.dispatcher.dispatch(
        ExecutionRequest(
            capability=capability,
            input=ExecutorInput(task=task),
            context=ExecutorContext(),
        )
    )
