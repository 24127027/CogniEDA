
from ..llm import ModelConfig, create_agent
from .types import PlannerPlan

class PlannerModel:
    def __init__(self) -> None:

        self._agent = create_agent(
            worker="planner",
            config=ModelConfig(),
            deps_type=type(None),
            builtin_tools=[],
        )

    async def plan(self, query: str) -> PlannerPlan:
        prompt = (
            "Analyze the user's request and produce a bounded research plan.\n"
            "Do not execute any tools.\n"
            "Do not claim that any analysis has already been performed.\n"
            "Each plan step should describe one coherent unit of work.\n"
            "Use capability='data_exploration' when the step requires dataset analysis.\n\n"
            f"User request:\n{query}"
        )

        result = await self._agent.run(
            prompt,
            output_type=PlannerPlan,
        )

        return PlannerPlan.model_validate(result.output)