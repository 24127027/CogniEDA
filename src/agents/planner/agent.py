"""Planner agent wrapper."""

from tools.builtin_tools import AvailableBuiltinTools

from ..types import RuntimePayload
from .graph import build_graph
from .types import Context, PlannerOutput, State


class Planner:
    """Planner orchestrator. It produces operations, not Evidence or Discovery."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = (AvailableBuiltinTools.GRAPH,)

    def __init__(self) -> None:
        self.graph = build_graph()

    async def run(self, query: str, session_frame: ...) -> RuntimePayload:
        """Run the Planner agent with the given query and session frame."""

        input = State(query=query)
        context = self.prepare_context(session_frame)
        final_state_dict = await self.graph.ainvoke(input, context=context)
        final_state = State(**final_state_dict)

        payload = self.prepare_payload(final_state)
        return payload

    def prepare_payload(self, state: State) -> RuntimePayload:
        """Extract the necessary information from the state
        to prepare the payload returned to the runtime
        """
        return RuntimePayload(
            payload=PlannerOutput(
                planner_operations=state.planner_operations,
                commit_result=state.commit_result,
            )
        )

    def prepare_context(self, session_frame: ...) -> Context:
        """Prepare the context for the Planner agent based on the session frame."""
        return session_frame
