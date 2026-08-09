from __future__ import annotations

from cognieda.application.ports import AgentFactoryPort, ModelConfig

from .dependencies import PlannerDeps
from .graph import build_graph
from .model import PlannerModel
from .tools import invoke_data_capability
from .types import PlannerOutput, State
from .context import Context, PlanningContext

class Planner:
    """Planner responsible for producing the next research plan."""

    builtin_tools = ()

    def __init__(
        self,
        deps: PlannerDeps,
        *,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig,
    ) -> None:
        self.graph = build_graph()
        self.model = PlannerModel(
            deps=deps,
            agent_factory=agent_factory,
            model_config=model_config,
            builtin_tools=self.builtin_tools,
        )

    async def run(
        self,
        query: str,
        *,
        planning_context: PlanningContext | None = None,
    ) -> PlannerOutput:
        planning_context = planning_context or PlanningContext()

        context = Context(
            planner_model=self.model,
            planning_context=planning_context,
        )

        result = await self.graph.ainvoke(
            State(query=query),
            context=context,
        )

        final_state = State.model_validate(result)

        return PlannerOutput(
            plan=final_state.plan,
            new_messages=final_state.new_messages,
            error=final_state.error,
        )