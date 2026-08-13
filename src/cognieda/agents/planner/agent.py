from __future__ import annotations

from cognieda.application.planner_data_work import run_data_work
from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.execution import ExecutorContext
from cognieda.schemas.artifacts import DataProfile, Task

from .context import Context, PlanningContext
from .dependencies import PlannerDeps
from .graph import build_graph
from .model import PlannerDecisionModel, PlannerModel
from .types import (
    PlannerControlledError,
    PlannerErrorCode,
    PlannerOutput,
    PlannerTaskExecutionInput,
    PlannerTaskExecutionOutput,
    State,
)


class Planner:
    """Human-facing coordinator over typed MVP research state."""

    builtin_tools = (run_data_work,)

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

    async def reload_model(self) -> None:
        """Reload the underlying model from the agent factory and model config."""

        #TODO: Temporarily allow reloading of the model
        if not isinstance(self.model, PlannerModel):
            raise RuntimeError(
                "Cannot reload model because it was provided directly and is not a PlannerModel."
            )
        self.model.reload_model()

    async def execute_task(
        self,
        *,
        task: Task,
        data_profile: DataProfile,
        execution_context: ExecutorContext,
        dataset_digest: str,
    ) -> PlannerTaskExecutionOutput:
        """Reason over governed tools for one application-selected Task goal."""

        execution_deps = PlannerDeps(
            dispatcher=self.deps.dispatcher,
            active_task=task,
            data_profile=data_profile,
            execution_context=execution_context,
            dataset_digest=dataset_digest,
        )
        result = await self.model.execute_task(
            PlannerTaskExecutionInput(task=task, data_profile=data_profile),
            deps=execution_deps,
        )
        return PlannerTaskExecutionOutput(
            response=result.output.response,
            blocker=result.output.blocker,
            data_results=tuple(execution_deps.data_results),
            new_messages=result.new_messages,
        )

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
            proposed_objective=final_state.proposed_objective,
            proposed_tasks=final_state.proposed_tasks,
            proposed_plan_revision=final_state.proposed_plan_revision,
            new_messages=final_state.new_messages,
            error=final_state.error,
        )
