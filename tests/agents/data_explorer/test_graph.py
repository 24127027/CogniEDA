from unittest.mock import AsyncMock, MagicMock

import pytest

from cognieda.agents.data_explorer_patch.context import Context
from cognieda.agents.data_explorer_patch.graph import build_graph
from cognieda.agents.data_explorer_patch.nodes import _route_after_check_result
from cognieda.agents.data_explorer_patch.state import State


def test_build_graph_compiles_successfully():
    graph = build_graph()
    assert graph is not None


@pytest.mark.anyio
async def test_graph_happy_path(monkeypatch):
    # We will mock the nodes so we don't need real pydantic_ai agents
    mock_planning = AsyncMock(return_value={"iterations": 1, "messages": ["plan msg"]})
    mock_execute = AsyncMock(return_value={"artifacts": ["evidence"], "messages": ["exec msg"]})
    mock_check_result = AsyncMock(return_value={"feedback": "YES", "messages": ["check msg"]})

    monkeypatch.setattr("cognieda.agents.data_explorer_patch.graph.planning", mock_planning)
    monkeypatch.setattr("cognieda.agents.data_explorer_patch.graph.execute", mock_execute)
    monkeypatch.setattr(
        "cognieda.agents.data_explorer_patch.graph.check_result", mock_check_result
    )

    # Rebuild graph to pick up patched nodes
    graph = build_graph()

    state: State = {"input": "test", "external_context": "{}"}
    context = MagicMock(spec=Context)

    result = await graph.ainvoke(state, context=context)

    # It should pass through planning -> execute -> check_result -> END
    assert result["feedback"] == "YES"
    assert "evidence" in result["artifacts"]


@pytest.mark.anyio
async def test_graph_replanning_path():
    # Verify the router function loops back when feedback is NO and iterations < 3
    assert _route_after_check_result({"feedback": "NO", "iterations": 1}) == "planning"
    assert _route_after_check_result({"feedback": "NO", "iterations": 3}) == "__end__"
