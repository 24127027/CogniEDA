# planner.py

from __future__ import annotations

from ..types import RuntimePayload
from .graph import build_graph
from .types import Context, PlannerOutput, State
from .model import PlannerModel

class Planner:
    """Planner that currently produces plans only."""

    def __init__(self) -> None:
        self.graph = build_graph()
        self.model = PlannerModel()

    async def run(
        self,
        query: str,
        context: Context,
    ) -> RuntimePayload:
        state = State(query=query)
        context.planner_model = self.model

        result = await self.graph.ainvoke(
            state,
            context=context,
        )

        final_state = State.model_validate(result)

        return RuntimePayload(
            payload=PlannerOutput(
                plan=final_state.plan,
                error=final_state.error,
            )
        )