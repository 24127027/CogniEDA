# nodes.py

from __future__ import annotations

from langgraph.runtime import Runtime

from ..utilities.nodes_registry import NodeRegistry
from .types import Context, State

registry = NodeRegistry[State, Context]()
R = registry.R


@registry.register()
async def create_plan(
    state: State,
    runtime: Runtime[Context],
) -> State:
    """Produce a typed plan for the latest user request."""

    model = runtime.context.planner_model

    if model is None:
        state.error = "Planner model is not configured."
        return state

    try:
        state.plan = await model.plan(state.query)  # type: ignore
    except Exception as exc:
        state.error = f"Planner failed: {exc}"

    return state
