from __future__ import annotations

from cognieda.agents.graph_miner import GraphMiner
from cognieda.agents.hypothesis_analyst import HypothesisAnalyst
from cognieda.tools.builtin import AvailableBuiltinTools


def test_deferred_specialists_import_without_production_registration() -> None:
    assert HypothesisAnalyst.builtin_tools == ()
    assert GraphMiner.builtin_tools == (AvailableBuiltinTools.GRAPH,)
