from ..base_agent import BaseAgent
from .graph import build_graph
from .types import HypothesisAnalystRequest, HypothesisAnalystResult, HypothesisAnalystState

class HypothesisAnalyst(BaseAgent[HypothesisAnalystRequest, HypothesisAnalystResult, HypothesisAnalystState]):
    def __init__(self, *args, **kwargs):
        super().__init__(
            graph=build_graph()
        )
        # Initialize any additional attributes specific to the HypothesisAnalyst here

    async def before_run(self, input: HypothesisAnalystRequest) -> HypothesisAnalystState:
        # Implement any preprocessing or setup before the main run method
        raise NotImplementedError("HypothesisAnalyst.before_run is not implemented yet.")

    async def after_run(self, output: HypothesisAnalystState) -> HypothesisAnalystResult:
        # Implement any postprocessing or conversion of the output to the expected format
        raise NotImplementedError("HypothesisAnalyst.after_run is not implemented yet.")