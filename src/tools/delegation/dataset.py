from pydantic_ai.tools import RunContext

from src.agents.executor.capabilities import Capability
from src.agents.executor.types import ExecutionRequest

from ..dependencies.protocols import HasExecutorDispatcher


async def analyze_dataset(
    ctx: RunContext[HasExecutorDispatcher],
    task: ...,
):
    return await ctx.deps.dispatcher.dispatch(
        ExecutionRequest(
            capability=Capability.DATA_ANALYSIS,
            input=...,
            context=...,
        )
    )