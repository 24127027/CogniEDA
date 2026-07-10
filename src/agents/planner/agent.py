"""Planner agent wrapper."""

from ..types import RuntimePayload
from .graph import build_graph
from .types import AnalyticalExecutor, Context, PlannerOutput, State


class Planner:
    """Planner orchestrator. It produces operations, not Evidence or Discovery."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        analytical_executor: AnalyticalExecutor | None = None,
    ) -> None:
        self.graph = build_graph()
        self._database_url = database_url
        self._analytical_executor = analytical_executor

    async def run(
        self,
        query: str,
        session_frame: Context | None = None,
    ) -> RuntimePayload:
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

    def prepare_context(self, session_frame: Context | None = None) -> Context:
        """Prepare transient dependencies; SessionFrame refresh remains a future stage."""

        base_context = session_frame or Context()
        return base_context.model_copy(
            update={
                "database_url": self._database_url or base_context.database_url,
                "analytical_executor": (
                    self._analytical_executor or base_context.analytical_executor
                ),
            }
        )
