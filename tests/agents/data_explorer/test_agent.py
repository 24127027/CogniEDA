from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pandas as pd
import pytest

from cognieda.agents.data_explorer_patch.agent import DataExplorer
from cognieda.agents.data_explorer_patch.dependencies import DataExplorerDeps
from cognieda.delegation.contracts import ExecutionStatus, ExecutorContext, ExecutorRequest
from cognieda.schemas.artifacts import DataProfile


def test_builtin_tools_is_flat_sequence():
    """Verify builtin_tools is a flat sequence of callables, not nested tuples."""
    assert isinstance(DataExplorer.builtin_tools, tuple)
    assert len(DataExplorer.builtin_tools) > 0
    for tool in DataExplorer.builtin_tools:
        assert callable(tool)
        assert not isinstance(tool, tuple)


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
        context=ExecutorContext(content=()),
    )


@pytest.mark.anyio
async def test_agent_run_success(agent, req):
    agent.graph.ainvoke.return_value = {
        "artifacts": [],
        "iterations": 1,
        "feedback": "YES, it works",
    }

    res = await agent.run(req)
    assert res.status == ExecutionStatus.SUCCEEDED
    assert len(res.emitted_artifacts) == 0
    agent.graph.ainvoke.assert_called_once()


@pytest.mark.anyio
async def test_agent_run_resolves_data_profile_from_context(agent):
    profile = DataProfile(data_profile_id=uuid4(), row_count=2, column_count=0, columns=())
    req = ExecutorRequest(
        capability=agent.CAPABILITIES[0],
        input="test",
        context=ExecutorContext(content=(profile,)),
    )
    agent.graph.ainvoke.return_value = {
        "artifacts": [profile],
        "iterations": 1,
        "feedback": "YES",
    }

    res = await agent.run(req)
    assert res.status == ExecutionStatus.SUCCEEDED
    assert len(res.emitted_artifacts) == 1

    # Verify the context passed into graph had the resolved data_profile_id
    call_kwargs = agent.graph.ainvoke.call_args[1]
    invoked_context = call_kwargs["context"]
    assert invoked_context.deps.data_profile_id == profile.data_profile_id


@pytest.mark.anyio
async def test_agent_run_failure_loop_limit(agent, req):
    agent.graph.ainvoke.return_value = {
        "artifacts": [],
        "iterations": 3,
        "feedback": "NO: reason",
    }

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
