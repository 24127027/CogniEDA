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

    builtin_tools = (invoke_data_capability,)

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
        planning_context: PlanningContext 
    ) -> PlannerOutput:
        
        context = Context(
            planning_context=planning_context,
            planner_model=self.model,
        )

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

        return planner_output
