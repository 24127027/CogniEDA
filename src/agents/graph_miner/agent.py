from ..base_agent import BaseAgent
from .graph import build_graph
from .types import GraphMinerRequest, GraphMinerResult, GraphMinerState


class GraphMiner(BaseAgent[GraphMinerRequest, GraphMinerResult, GraphMinerState]):
    def __init__(self) -> None:
        super().__init__(graph=build_graph())

    async def before_run(self, input: GraphMinerRequest) -> GraphMinerState:
        raise NotImplementedError("GraphMiner.before_run is not implemented yet.")

    async def after_run(self, output: GraphMinerState) -> GraphMinerResult:
        raise NotImplementedError("GraphMiner.after_run is not implemented yet.")