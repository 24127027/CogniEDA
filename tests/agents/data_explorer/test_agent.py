import pytest
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
from cognieda.agents.data_explorer_patch.agent import DataExplorer
from cognieda.agents.data_explorer_patch.dependencies import DataExplorerDeps
from cognieda.delegation.contracts import ExecutorRequest, ExecutionStatus, ExecutorContext

@pytest.fixture
def agent():
    df = pd.DataFrame({"A": [1, 2]})
    deps = DataExplorerDeps(dataframe=df)
    config = MagicMock()
    factory = MagicMock()
    factory.create_agent.return_value = MagicMock()
    
    agent = DataExplorer(deps=deps, config=config, agent_factory=factory)
    agent.graph = AsyncMock()
    return agent

@pytest.fixture
def req(agent):
    return ExecutorRequest(
        capability=agent.CAPABILITIES[0],
        input="test",
        context=ExecutorContext(content=())
    )

@pytest.mark.anyio
async def test_agent_run_success(agent, req):
    agent.graph.ainvoke.return_value = {"artifacts": [], "iterations": 1, "feedback": "YES, it works"}
    
    res = await agent.run(req)
    assert res.status == ExecutionStatus.SUCCEEDED
    assert len(res.emitted_artifacts) == 0
    agent.graph.ainvoke.assert_called_once()

@pytest.mark.anyio
async def test_agent_run_failure_loop_limit(agent, req):
    agent.graph.ainvoke.return_value = {"artifacts": [], "iterations": 3, "feedback": "NO: reason"}
    
    res = await agent.run(req)
    assert res.status == ExecutionStatus.FAILED
    assert res.failure == "NO: reason"
    agent.graph.ainvoke.assert_called_once()

@pytest.mark.anyio
async def test_agent_run_exception(agent, req):
    agent.graph.ainvoke.side_effect = Exception("Graph crashed")
    
    res = await agent.run(req)
    assert res.status == ExecutionStatus.FAILED
    assert "Graph crashed" in res.failure
    agent.graph.ainvoke.assert_called_once()
