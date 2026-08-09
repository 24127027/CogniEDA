from __future__ import annotations

from collections.abc import Sequence

from pydantic_ai.messages import ModelMessage

from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.execution import ExecutorContext
from cognieda.schemas.artifacts import SessionFrame

from .context import BuildPlanningContext, PlanningContextResolutionError
from .dependencies import PlannerDeps
from .graph import build_graph
from .model import PlannerDecisionModel, PlannerModel
from .types import (
    Context,
    PlannerControlledError,
    PlannerErrorCode,
    PlannerOutput,
    State,
)


class Planner:
    """Human-facing coordinator over typed MVP research state."""

    builtin_tools: tuple[()] = ()

    def __init__(
        self,
        deps: PlannerDeps,
        *,
        planner_model: PlannerDecisionModel | None = None,
        agent_factory: AgentFactoryPort | None = None,
        model_config: ModelConfig | None = None,
    ) -> None:
        if planner_model is not None:
            if agent_factory is not None or model_config is not None:
                raise ValueError(
                    "Provide either planner_model or agent_factory plus model_config, not both."
                )
            self.model = planner_model
        else:
            if agent_factory is None or model_config is None:
                raise ValueError(
                    "Planner requires a typed planner_model or agent_factory plus model_config."
                )
            self.model = PlannerModel(
                deps=deps,
                agent_factory=agent_factory,
                model_config=model_config,
            )

        self.deps = deps
        self.context_builder = BuildPlanningContext(deps.research_state)
        self.graph = build_graph()

    async def run(
        self,
        query: str,
        *,
        session_frame: SessionFrame | None = None,
        message_history: Sequence[ModelMessage] = (),
        execution_context: ExecutorContext | None = None,
    ) -> PlannerOutput:
        """Run one request against explicit typed state and return its validated successor."""

        frame = session_frame or SessionFrame()
        if not query.strip():
            error = PlannerControlledError(
                code=PlannerErrorCode.INVALID_COMMAND,
                message="Planner requests cannot be empty.",
            )
            return PlannerOutput(response=error.message, session_frame=frame, error=error)

        try:
            planning_context = self.context_builder.build(
                latest_request=query,
                frame=frame,
                message_history=message_history,
            )
        except PlanningContextResolutionError as exc:
            error = PlannerControlledError(
                code=PlannerErrorCode.CONTEXT_RESOLUTION_FAILED,
                message=f"Planner context resolution failed closed: {exc}",
            )
            return PlannerOutput(response=error.message, session_frame=frame, error=error)

        state = State(
            query=query,
            session_frame=frame,
            planning_context=planning_context,
            execution_context=execution_context or ExecutorContext(),
        )
        context = Context(
            planner_model=self.model,
            dispatcher=self.deps.dispatcher,
            research_state=self.deps.research_state,
            context_builder=self.context_builder,
        )
        result = await self.graph.ainvoke(state, context=context)
        final_state = State.model_validate(result)

        if final_state.response is None:
            error = PlannerControlledError(
                code=PlannerErrorCode.RESPONSE_FAILED,
                message="Planner graph completed without a human-facing response.",
            )
            final_state.error = error
            final_state.response = error.message

        return PlannerOutput(
            response=final_state.response,
            session_frame=final_state.session_frame,
            decision=final_state.decision,
            created_task_ids=(
                (final_state.created_task_id,) if final_state.created_task_id is not None else ()
            ),
            selected_capability=final_state.selected_capability,
            work_outcome=final_state.work_outcome,
            error=final_state.error,
            new_messages=final_state.new_messages,
        )
