from ..base_agent import BaseAgent
from .graph import build_graph

class HypothesisAnalyst(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(
            graph=build_graph()
        )
        # Initialize any additional attributes specific to the HypothesisAnalyst here

    async def before_run(self, input):
        # Implement any preprocessing or setup before the main run method
        pass

    async def after_run(self, output: dict):
        # Implement any postprocessing or conversion of the output to the expected format
        return output  # Modify this as needed to convert to the expected ResT