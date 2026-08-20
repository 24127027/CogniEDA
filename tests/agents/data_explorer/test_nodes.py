import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from cognieda.agents.data_explorer_patch.nodes import (
    planning, execute, check_result, _route_after_check_result
)
from cognieda.agents.data_explorer_patch.state import State
from cognieda.agents.data_explorer_patch.context import Context
from cognieda.schemas.artifacts import DataProfile
from pydantic_ai.messages import ToolReturnPart, ModelResponse

def create_mock_runtime():
    runtime = MagicMock()
    runtime.context = MagicMock(spec=Context)
    runtime.context.deps = MagicMock()
    runtime.context.deps.data_profile_id = None
    runtime.context.agent = MagicMock()
    # the run method returns an object with all_messages(), new_messages(), and data
    run_result = MagicMock()
    run_result.all_messages.return_value = ["message1", "message2"]
    run_result.new_messages.return_value = []
    run_result.data = ""
    # We must use AsyncMock for the run function, but it needs to return the synchronous result
    runtime.context.agent.run = AsyncMock(return_value=run_result)
    return runtime

@pytest.mark.anyio
async def test_planning_node():
    state: State = {
        "input": "test task",
        "external_context": "{}",
        "artifacts": ["old_artifact"],
        "iterations": 1,
        "messages": [],
        "feedback": "Needs work"
    }
    runtime = create_mock_runtime()
    
    new_state = await planning(state, runtime)
    
    # artifacts should be cleared on planning loop
    assert new_state["artifacts"] == []
    # iterations should be incremented
    assert new_state["iterations"] == 2
    # Should update messages
    assert new_state["messages"] == ["message1", "message2"]
    runtime.context.agent.run.assert_called_once()
    
    # Verify feedback was included in the prompt
    prompt = runtime.context.agent.run.call_args[0][0]
    assert "Needs work" in prompt

@pytest.mark.anyio
async def test_execute_node_with_data_profile(monkeypatch):
    state: State = {
        "input": "test task",
        "external_context": "{}",
        "messages": []
    }
    runtime = create_mock_runtime()
    run_result = runtime.context.agent.run.return_value
    
    # Mock a ToolReturn containing a DataProfile
    profile = DataProfile(data_profile_id=uuid4(), row_count=10, column_count=0, columns=())
    tool_ret = ToolReturnPart(tool_name="test", content=profile, tool_call_id="1")
    run_result.new_messages.return_value = [tool_ret]
    
    # Mock the Agent inside execute to avoid actual LLM calls for descriptions
    mock_desc_agent = MagicMock()
    mock_desc_agent_run = AsyncMock()
    mock_desc_result = MagicMock()
    mock_desc_result.data.descriptions = {}
    mock_desc_agent_run.return_value = mock_desc_result
    mock_desc_agent.return_value.run = mock_desc_agent_run
    
    monkeypatch.setattr("pydantic_ai.Agent", mock_desc_agent)
    
    new_state = await execute(state, runtime)
    
    assert len(new_state.get("artifacts", [])) == 1
    assert isinstance(new_state["artifacts"][0], DataProfile)
    mock_desc_agent.return_value.run.assert_called_once()

@pytest.mark.anyio
async def test_execute_node_with_tool_responses(monkeypatch):
    state: State = {
        "input": "test task",
        "external_context": "{}",
        "messages": []
    }
    runtime = create_mock_runtime()
    run_result = runtime.context.agent.run.return_value
    
    # Mock a generic tool response
    tool_ret = ToolReturnPart(tool_name="test_tool", content={"result": 42}, tool_call_id="1")
    run_result.new_messages.return_value = [tool_ret]
    
    # Mock the Agent inside execute for Evidence synthesis
    mock_ev_agent = MagicMock()
    mock_ev_agent_run = AsyncMock()
    mock_ev_result = MagicMock()
    mock_ev_result.data.content = {"synthesized": True}
    mock_ev_result.data.artifact_refs = ["test_ref"]
    mock_ev_agent_run.return_value = mock_ev_result
    mock_ev_agent.return_value.run = mock_ev_agent_run
    
    monkeypatch.setattr("pydantic_ai.Agent", mock_ev_agent)
    
    new_state = await execute(state, runtime)
    
    assert len(new_state.get("artifacts", [])) == 1
    # Check Evidence synthesis
    ev = new_state["artifacts"][0]
    assert ev.content == {"synthesized": True}
    assert ev.artifact_refs == ("test_ref",)
    mock_ev_agent.return_value.run.assert_called_once()

@pytest.mark.anyio
async def test_check_result_node():
    state: State = {}
    runtime = create_mock_runtime()
    runtime.context.agent.run.return_value.data = "YES"
    
    new_state = await check_result(state, runtime)
    assert new_state["feedback"] == "YES"

def test_route_after_check_result_success():
    state: State = {"feedback": "YES, it works"}
    assert _route_after_check_result(state) == "__end__"

def test_route_after_check_result_needs_revision():
    state: State = {"feedback": "NO: broken", "iterations": 1}
    assert _route_after_check_result(state) == "planning"

def test_route_after_check_result_exhausted_loops():
    state: State = {"feedback": "NO: broken", "iterations": 3}
    assert _route_after_check_result(state) == "__end__"
