from __future__ import annotations

from cognieda.agents.executor.graph_miner.agent import GraphMiner
from cognieda.agents.executor.hypothesis_analyst.agent import HypothesisAnalyst
from cognieda.tools.builtin import AvailableBuiltinTools


def test_deferred_specialists_import_without_production_registration() -> None:
    assert HypothesisAnalyst.builtin_tools == ()
    assert GraphMiner.builtin_tools == (AvailableBuiltinTools.GRAPH,)
