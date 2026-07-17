"""Planner agent wrapper."""

from uuid import UUID

from tools.builtin_tools import AvailableBuiltinTools

from ..types import RuntimePayload
from .graph import build_graph
from .types import Context, PlannerDecision, PlannerOutput, State


class Planner:
    """Planner orchestrator. It produces operations, not Evidence or Discovery."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = (AvailableBuiltinTools.GRAPH,)

    def __init__(self, *, database_url: str | None = None) -> None:
        self.graph = build_graph()
        self._database_url = database_url

    async def run(
        self,
        query: str,
        session_frame: Context | None = None,
        decision: PlannerDecision | None = None,
    ) -> RuntimePayload:
        """Run the Planner agent with the given query and session frame."""

        context = self.prepare_context(session_frame)
        resume_operation_ids: list[UUID] = []
        if decision is not None:
            try:
                resume_operation_ids = [
                    UUID(operation_id) for operation_id in decision.selected_ids
                ]
            except ValueError:
                resume_operation_ids = []
        input = State(
            query=query,
            session_id=context.session_id or "default",
            planner_decision=decision,
            resume_requested=decision is not None,
            resume_operation_ids=resume_operation_ids,
        )
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
                pending_interaction=state.pending_interaction,
                controlled_error=state.controlled_error,
                committed_operation_ids=(
                    state.commit_result.committed_operation_ids
                    if state.commit_result is not None
                    else []
                ),
                planner_operations=state.planner_operations,
                commit_result=state.commit_result,
            )
        )

    def prepare_context(self, session_frame: Context | None = None) -> Context:
        """Prepare the context for the Planner agent based on the session frame."""

        context = session_frame or Context()
        return context.model_copy(
            update={"database_url": self._database_url or context.database_url}
        )
