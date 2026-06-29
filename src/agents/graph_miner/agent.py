from ..base_agent import BaseAgent
from ..types import BaseState
from .graph import build_graph
from .types import GraphMinerRequest, GraphMinerResult


class GraphMiner(BaseAgent[GraphMinerRequest, GraphMinerResult, BaseState]):
    def __init__(self) -> None:
        super().__init__(graph=build_graph())

    async def before_run(self, input: GraphMinerRequest) -> BaseState:
        raise NotImplementedError("GraphMiner.before_run is not implemented yet.")

    async def after_run(self, output: BaseState) -> GraphMinerResult:
        raise NotImplementedError("GraphMiner.after_run is not implemented yet.")