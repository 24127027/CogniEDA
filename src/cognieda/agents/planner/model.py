from collections.abc import Sequence

from cognieda.application.ports import AgentFactoryPort, AgentTool, ModelConfig

from .dependencies import PlannerDeps
from .types import PlannerPlan


class PlannerModel:
    def __init__(
        self,
        deps: PlannerDeps,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig,
        builtin_tools: Sequence[AgentTool],
    ) -> None:
        self.deps = deps
        self._agent = agent_factory.create_agent(
            worker="planner",
            config=model_config,
            deps_type=PlannerDeps,
            builtin_tools=builtin_tools,
        )

    async def plan(self, query: str) -> PlannerPlan:
        prompt = (
            "Analyze the user's request and produce a bounded research plan.\n"
            "Do not claim that any analysis has already been performed.\n"
            "Each plan step should describe one coherent unit of work.\n"
            f"User request:\n{query}"
        )

        result = await self._agent.run(
            prompt,
            output_type=PlannerPlan,
            deps=self.deps,
        )

        return PlannerPlan.model_validate(result.output)
