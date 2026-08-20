from pydantic_ai import RunContext

from cognieda.delegation.contracts import ExecutorResult, ExecutorRequest, ExecutorContext
from cognieda.delegation.capabilities import Capability
from cognieda.schemas.artifacts import DataProfile

from ..dependencies import PlannerDeps


async def _dispatch(
    ctx: RunContext[PlannerDeps],
    *,
    capability: Capability,
    task: str,
    include_data_profile: bool = False,
) -> ExecutorResult:
    content: tuple[DataProfile, ...] = ()

    if include_data_profile:
        profile = ctx.deps.planner_context.data_profile
        if profile is not None:
            content = (profile,)

    request = ExecutorRequest(
        capability=capability,
        input=task,
        context=ExecutorContext(content=content),
    )

    return await ctx.deps.dispatcher.dispatch(request)


async def data_analysis(
    ctx: RunContext[PlannerDeps],
    *,
    task: str,
    include_data_profile: bool = False,
) -> ExecutorResult:
    """Perform analytical work on the active dataset."""
    return await _dispatch(
        ctx,
        capability=Capability.DATA_ANALYSIS,
        task=task,
        include_data_profile=include_data_profile,
    )


async def data_profiling(
    ctx: RunContext[PlannerDeps],
    *,
    task: str,
) -> ExecutorResult:
    """Create or inspect the structural profile of the active dataset."""
    return await _dispatch(
        ctx,
        capability=Capability.DATA_PROFILING,
        task=task,
    )


async def data_transformation(
    ctx: RunContext[PlannerDeps],
    *,
    task: str,
    include_data_profile: bool = False,
) -> ExecutorResult:
    """Perform a requested transformation of the active dataset."""
    return await _dispatch(
        ctx,
        capability=Capability.DATA_TRANSFORMATION,
        task=task,
        include_data_profile=include_data_profile,
    )