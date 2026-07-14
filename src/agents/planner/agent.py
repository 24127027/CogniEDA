"""Planner agent wrapper."""

from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver

from tools.builtin_tools import AvailableBuiltinTools

from ..types import RuntimePayload
from .graph import build_graph
from .types import Context, PlannerDecision, PlannerOutput, State


class Planner:
    """Planner orchestrator. It produces operations, not Evidence or Discovery."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = (AvailableBuiltinTools.GRAPH,)

    builtin_tools: tuple[AvailableBuiltinTools, ...] = (AvailableBuiltinTools.GRAPH,)

    def __init__(
        self,
        *,
        database_url: str | None = None,
        checkpointer=None,
    ) -> None:
        self.checkpointer = checkpointer or MemorySaver()
        self.graph = build_graph(checkpointer=self.checkpointer)
        self._database_url = database_url

    async def run(
        self,
        query: str,
        session_frame: Context | None = None,
        decision: PlannerDecision | None = None,
    ) -> RuntimePayload:
        """Run the Planner agent with the given query and session frame."""

        context = self.prepare_context(session_frame)
        if context.database_url:
            from application.orchestrator.reconciler import reconcile_execution_attempts
            from db.session import get_session

            session = get_session(context.database_url)
            try:
                reconcile_execution_attempts(session)
            finally:
                session.close()

        resume_approval_id: UUID | None = None
        if decision is not None and decision.proposal_id is not None:
            try:
                resume_approval_id = UUID(decision.proposal_id)
            except ValueError:
                resume_approval_id = None
        input = State(
            query=query,
            planner_decision=decision,
            resume_approval_id=resume_approval_id,
            session_id=context.session_id or "default",
        )
        config = {"configurable": {"thread_id": context.session_id or "default"}}
        final_state_dict = await self.graph.ainvoke(input, config=config, context=context)
        final_state = State(**final_state_dict)

        payload = self.prepare_payload(final_state)
        return payload

    def prepare_payload(self, state: State) -> RuntimePayload:
        """Extract the necessary information from the state
        to prepare the payload returned to the runtime
        """
        return RuntimePayload(
            payload=PlannerOutput(
                response_text=state.response_text,
                session_frame_id=state.active_session_frame_id,
                requested_capability=state.requested_capability,
                pending_interaction=state.pending_interaction,
                controlled_error=state.controlled_error,
                controlled_placeholder=state.controlled_placeholder,
                committed_operation_ids=state.operation_ids_to_commit or [],
                planner_operations=state.planner_operations,
                executor_dispatch_ref=(
                    state.resolve_object_reference(state.execution_admission.execution_run_ref)
                    if state.execution_admission is not None
                    and state.execution_admission.execution_run_ref is not None
                    else None
                ),
                commit_result=state.commit_result,
            )
        )

    def prepare_context(self, session_frame: Context | None = None) -> Context:
        """Prepare transient dependencies; SessionFrame refresh remains a future stage."""

        base_context = session_frame or Context()
        return base_context.model_copy(
            update={
                "database_url": self._database_url or base_context.database_url,
            }
        )
