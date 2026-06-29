from ..base_agent import BaseAgent
from .graph import build_graph
from .types import PlannerRequest, PlannerResult
class Planner(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(
            graph=build_graph()
        )
        # Initialize any additional attributes specific to the Planner here

    async def before_run(self, input: PlannerRequest):
        # Implement any preprocessing or setup before the main run method
        pass

    async def after_run(self, output: PlannerResult):
        # Implement any postprocessing or conversion of the output to the expected format
        return output  # Modify this as needed to convert to the expected ResT