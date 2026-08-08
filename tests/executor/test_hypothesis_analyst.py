from __future__ import annotations

from agents.executor.graph_miner.agent import GraphMiner
from agents.executor.hypothesis_analyst.agent import HypothesisAnalyst
from tools.builtin import AvailableBuiltinTools


def test_deferred_specialists_import_without_production_registration() -> None:
    assert HypothesisAnalyst.builtin_tools == ()
    assert GraphMiner.builtin_tools == (AvailableBuiltinTools.GRAPH,)
