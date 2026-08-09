# nodes.py

from __future__ import annotations

from langgraph.runtime import Runtime

from .types import State
from .context import Context

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
        result = await model.plan( #type: ignore
            state.query,
            message_history=runtime.context.planning_context.
            conversation_history
            .model_messages()
        )

        state.plan = result.plan
        state.new_messages = result.new_messages

    except Exception as exc:
        state.error = f"Planner failed: {exc}"

    return state