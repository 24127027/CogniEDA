from ..base_agent import BaseAgent
from .graph import build_graph
from .types import PlannerRequest, PlannerResult, PlannerState
class Planner(BaseAgent[PlannerRequest, PlannerResult, PlannerState]):
    def __init__(self, *args, **kwargs):
        super().__init__(
            graph=build_graph()
        )
        # Initialize any additional attributes specific to the Planner here

    async def before_run(self, input: PlannerRequest) -> PlannerState:
        # Implement any preprocessing or setup before the main run method
        raise NotImplementedError("Planner.before_run is not implemented yet.")

    async def after_run(self, output: PlannerState) -> PlannerResult:
        # Implement any postprocessing or conversion of the output to the expected format
        raise NotImplementedError("Planner.after_run is not implemented yet.")