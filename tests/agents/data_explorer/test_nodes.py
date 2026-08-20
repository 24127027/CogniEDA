from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart

from cognieda.agents.data_explorer_patch.context import Context
from cognieda.agents.data_explorer_patch.nodes import (
    _route_after_check_result,
    check_result,
    execute,
    planning,
)
from cognieda.agents.data_explorer_patch.state import State
from cognieda.schemas.artifacts import DataProfile, Evidence
from cognieda.schemas.common import ColumnProfile
from cognieda.schemas.enums import VariableType


def create_mock_runtime(data_profile_id=None):
    runtime = MagicMock()
    runtime.context = MagicMock(spec=Context)
    runtime.context.deps = MagicMock()
    runtime.context.deps.data_profile_id = data_profile_id
    runtime.context.context = MagicMock()
    runtime.context.context.model_dump_json.return_value = '{"test": "context"}'
    runtime.context.agent = MagicMock()

    run_result = MagicMock()
    run_result.all_messages.return_value = ["message1", "message2"]
    run_result.new_messages.return_value = []
    run_result.output = ""
    run_result.data = ""
    runtime.context.agent.run = AsyncMock(return_value=run_result)
    return runtime


@pytest.mark.anyio
async def test_planning_node_initial():
    state: State = {
        "input": "investigate seasonality",
        "artifacts": [],
        "iterations": 0,
        "messages": [],
    }
    runtime = create_mock_runtime()

    new_state = await planning(state, runtime)

    assert new_state["iterations"] == 1
    assert new_state["artifacts"] == []
    assert new_state["messages"] == ["message1", "message2"]
    runtime.context.agent.run.assert_called_once()

    prompt = runtime.context.agent.run.call_args[0][0]
    assert "investigate seasonality" in prompt
    assert "DATA OPERATIONS" in prompt

    # Check instructions passed to agent.run
    call_kwargs = runtime.context.agent.run.call_args[1]
    instructions = call_kwargs.get("instructions", "")
    assert "DATA_EXPLORER" in instructions or "Data Explorer" in instructions


@pytest.mark.anyio
async def test_planning_node_revision_preserves_artifacts():
    existing_profile = DataProfile(
        data_profile_id=uuid4(),
        row_count=100,
        column_count=1,
        columns=(
            ColumnProfile(
                name="sales",
                dtype="float64",
                variable_type=VariableType.CONTINUOUS,
                distinct_count=50,
                missing_count=0,
            ),
        ),
    )
    state: State = {
        "input": "compute autocorrelation",
        "artifacts": [existing_profile],
        "iterations": 1,
        "messages": [],
        "feedback": "NO: lag 12 was not computed",
    }
    runtime = create_mock_runtime()

    new_state = await planning(state, runtime)

    # Artifacts MUST be preserved, not wiped!
    assert len(new_state["artifacts"]) == 1
    assert new_state["artifacts"][0] == existing_profile
    assert new_state["iterations"] == 2

    prompt = runtime.context.agent.run.call_args[0][0]
    assert "Previous execution did not fully fulfill the request" in prompt
    assert "lag 12 was not computed" in prompt
    assert "DataProfile" in prompt


@pytest.mark.anyio
async def test_execute_node_with_data_profile():
    state: State = {
        "input": "profile dataset",
        "artifacts": [],
        "messages": [],
    }
    runtime = create_mock_runtime()
    run_result = runtime.context.agent.run.return_value

    profile = DataProfile(data_profile_id=uuid4(), row_count=10, column_count=0, columns=())
    tool_call = ToolCallPart(tool_name="profiling", args={}, tool_call_id="call_1")
    tool_ret = ToolReturnPart(tool_name="profiling", content=profile, tool_call_id="call_1")

    # Simulate PydanticAI response containing tool call and return
    req = ModelRequest(parts=[tool_ret])
    resp = ModelResponse(parts=[tool_call])
    run_result.new_messages.return_value = [resp, req]

    new_state = await execute(state, runtime)

    assert len(new_state["artifacts"]) == 1
    assert isinstance(new_state["artifacts"][0], DataProfile)
    assert new_state["artifacts"][0] == profile


@pytest.mark.anyio
async def test_execute_node_with_deterministic_evidence():
    profile_id = uuid4()
    state: State = {
        "input": "check sales summary",
        "artifacts": [],
        "messages": [],
    }
    runtime = create_mock_runtime(data_profile_id=profile_id)
    run_result = runtime.context.agent.run.return_value

    tool_output = {
        "column": "sales",
        "dtype": "float64",
        "row_count": 50,
        "missing_count": 0,
        "distinct_count": 45,
    }
    tool_call = ToolCallPart(
        tool_name="column_summary",
        args={"column": "sales"},
        tool_call_id="call_2",
    )
    tool_ret = ToolReturnPart(
        tool_name="column_summary",
        content=tool_output,
        tool_call_id="call_2",
    )

    resp = ModelResponse(parts=[tool_call])
    req = ModelRequest(parts=[tool_ret])
    run_result.new_messages.return_value = [resp, req]

    new_state = await execute(state, runtime)

    assert len(new_state["artifacts"]) == 1
    evidence = new_state["artifacts"][0]
    assert isinstance(evidence, Evidence)
    assert evidence.data_profile_id == profile_id
    assert evidence.content == tool_output
    assert evidence.artifact_refs == ("sales",)
    assert evidence.provenance.tool_reference == "column_summary"
    assert evidence.provenance.data_profile_id == profile_id


@pytest.mark.anyio
async def test_execute_node_without_data_profile_id_fails_closed():
    # When no data_profile_id exists in deps, context, or generated artifacts,
    # it must NOT fabricate a random UUID.
    state: State = {
        "input": "check summary",
        "artifacts": [],
        "messages": [],
    }
    runtime = create_mock_runtime(data_profile_id=None)
    run_result = runtime.context.agent.run.return_value

    tool_call = ToolCallPart(
        tool_name="column_summary",
        args={"column": "sales"},
        tool_call_id="call_3",
    )
    tool_ret = ToolReturnPart(
        tool_name="column_summary",
        content={"column": "sales", "row_count": 10},
        tool_call_id="call_3",
    )

    resp = ModelResponse(parts=[tool_call])
    req = ModelRequest(parts=[tool_ret])
    run_result.new_messages.return_value = [resp, req]

    new_state = await execute(state, runtime)

    # Should fail closed and not emit Evidence with a fake UUID
    assert len(new_state["artifacts"]) == 0


@pytest.mark.anyio
async def test_check_result_node():
    state: State = {}
    runtime = create_mock_runtime()
    runtime.context.agent.run.return_value.output = "YES"

    new_state = await check_result(state, runtime)
    assert new_state["feedback"] == "YES"

    prompt = runtime.context.agent.run.call_args[0][0]
    assert "requested DATA RESULT" in prompt
    assert "Do NOT judge whether a hypothesis is supported" in prompt


def test_route_after_check_result_success():
    state: State = {"feedback": "YES"}
    assert _route_after_check_result(state) == "__end__"


def test_route_after_check_result_needs_revision():
    state: State = {"feedback": "NO: broken", "iterations": 1}
    assert _route_after_check_result(state) == "planning"


def test_route_after_check_result_exhausted_loops():
    state: State = {"feedback": "NO: broken", "iterations": 3}
    assert _route_after_check_result(state) == "__end__"
