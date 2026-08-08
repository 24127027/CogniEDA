from __future__ import annotations


from ..types import RuntimePayload
from .dependencies import PlannerDeps
from .graph import build_graph
from .types import Context, PlannerOutput, State
from .model import PlannerModel
from ...tools.builtin import AvailableBuiltinTools


class Planner:
    """Planner responsible for producing the next research plan."""
    builtin_tools: list = [AvailableBuiltinTools.TERMINAL]

    def __init__(self, deps: PlannerDeps) -> None:
        self.graph = build_graph()
        self.model = PlannerModel(deps=deps, builtin_tools=self.builtin_tools)

    async def run(
        self,
        query: str,
        *,
        context: Context | None = None,
    ) -> RuntimePayload:
        if context is None:
            context = Context()

        context.planner_model = self.model

        state = State(query=query)

        result = await self.graph.ainvoke(
            state,
            context=context,
        )

        final_state = State.model_validate(result)

        planner_output = PlannerOutput(
            plan=final_state.plan,
            error=final_state.error,
        )

        return RuntimePayload(payload=planner_output)