from __future__ import annotations

from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.execution import ExecutorContext

from .context import Context, PlanningContext
from .dependencies import PlannerDeps
from .graph import build_graph
from .model import PlannerDecisionModel, PlannerModel
from .types import PlannerControlledError, PlannerErrorCode, PlannerOutput, State


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
        self.graph = build_graph()

    async def reload_model(self):
        """Reload the underlying model from the agent factory and model config."""

        #TODO: Temporarily allow reloading of the model
        if not isinstance(self.model, PlannerModel):
            raise RuntimeError(
                "Cannot reload model because it was provided directly and is not a PlannerModel."
            )
        self.model.reload_model()

    async def run(
        self,
        query: str,
        *,
        planning_context: PlanningContext,
        execution_context: ExecutorContext | None = None,
    ) -> PlannerOutput:
        """Run one request against explicit read-only context and return typed results."""

        if not query.strip():
            error = PlannerControlledError(
                code=PlannerErrorCode.INVALID_COMMAND,
                message="Planner requests cannot be empty.",
            )
            return PlannerOutput(response=error.message, error=error)

        state = State(
            query=query,
            execution_context=execution_context or ExecutorContext(),
        )
        context = Context(
            planner_model=self.model,
            dispatcher=self.deps.dispatcher,
            planning_context=planning_context,
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
            decision=final_state.decision,
            created_objective=final_state.created_objective,
            created_assumption=final_state.created_assumption,
            plan_draft=final_state.plan_draft,
            new_messages=final_state.new_messages,
            error=final_state.error,
        )
